"""
github_client.py - GitHub REST API Client for Real Log Ingestion and Auto-Remediation
"""

import os
import io
import zipfile
import requests
from typing import Optional, Dict, Any, Tuple

DEFAULT_HEADERS = {
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
    "User-Agent": "Self-Healing-CI-Pipeline-Agent"
}


def get_token() -> Optional[str]:
    return os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")


def fetch_run_logs(repo: str, run_id: str, token: Optional[str] = None) -> Tuple[bool, str]:
    """
    Downloads and extracts the actual console runner logs from a GitHub Actions workflow run.
    Uses: GET https://api.github.com/repos/{owner}/{repo}/actions/runs/{run_id}/logs
    Returns: (success: bool, extracted_log_text: str)
    """
    auth_token = token or get_token()
    headers = dict(DEFAULT_HEADERS)
    if auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"

    url = f"https://api.github.com/repos/{repo}/actions/runs/{run_id}/logs"

    try:
        response = requests.get(url, headers=headers, allow_redirects=True, timeout=20)
        if response.status_code != 200:
            return False, f"GitHub API responded with HTTP {response.status_code}: {response.text[:200]}"

        # The response is a ZIP archive containing log files for all jobs and steps
        with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
            log_entries = []
            for file_name in archive.namelist():
                # Focus on text log files from the runner steps
                if file_name.endswith(".txt") and not file_name.startswith("__"):
                    try:
                        content = archive.read(file_name).decode("utf-8", errors="replace")
                        # Look for files containing error signatures
                        if any(k in content for k in ("ERROR", "FATAL", "FAIL", "Exception", "SyntaxError", "IndentationError", "error TS")):
                            log_entries.append(f"=== Step Log: {file_name} ===\n{content}")
                    except Exception:
                        continue

            if log_entries:
                return True, "\n\n".join(log_entries)
            
            # If no specific error-marked step file found, concatenate the last few log files
            all_text = []
            for file_name in sorted(archive.namelist()):
                if file_name.endswith(".txt"):
                    try:
                        all_text.append(archive.read(file_name).decode("utf-8", errors="replace"))
                    except Exception:
                        pass
            return True, "\n".join(all_text[-3:]) if all_text else "No textual logs extracted from ZIP."

    except Exception as exc:
        return False, f"Log fetch failed: {str(exc)}"


def post_commit_comment(repo: str, commit_sha: str, comment_markdown: str, token: Optional[str] = None) -> Optional[str]:
    """
    Posts a formatted markdown comment directly onto the failed commit on GitHub.
    Uses: POST https://api.github.com/repos/{owner}/{repo}/commits/{commit_sha}/comments
    """
    auth_token = token or get_token()
    if not auth_token or not commit_sha:
        return None

    headers = dict(DEFAULT_HEADERS)
    headers["Authorization"] = f"Bearer {auth_token}"
    url = f"https://api.github.com/repos/{repo}/commits/{commit_sha}/comments"

    try:
        resp = requests.post(url, headers=headers, json={"body": comment_markdown}, timeout=10)
        if resp.status_code in (200, 201):
            return resp.json().get("html_url")
        print(f"[Warning] Failed to post commit comment: HTTP {resp.status_code} - {resp.text[:150]}")
    except Exception as exc:
        print(f"[Warning] Exception posting commit comment: {exc}")
    return None


def create_automated_fix_pr(
    repo: str,
    base_branch: str,
    target_file: str,
    corrected_content: str,
    commit_msg: str,
    pr_title: str,
    pr_body: str,
    token: Optional[str] = None
) -> Optional[str]:
    """
    Creates an automated fix branch and opens a Pull Request on GitHub.
    Returns: PR html_url if successful, else None.
    """
    auth_token = token or get_token()
    if not auth_token or not target_file or not corrected_content:
        return None

    headers = dict(DEFAULT_HEADERS)
    headers["Authorization"] = f"Bearer {auth_token}"

    try:
        # 1. Get base branch latest commit SHA
        ref_url = f"https://api.github.com/repos/{repo}/git/ref/heads/{base_branch}"
        ref_resp = requests.get(ref_url, headers=headers, timeout=10)
        if ref_resp.status_code != 200:
            return None
        base_sha = ref_resp.json()["object"]["sha"]

        # 2. Create new fix branch
        branch_name = f"auto-heal/fix-{base_sha[:7]}"
        create_ref_url = f"https://api.github.com/repos/{repo}/git/refs"
        branch_payload = {"ref": f"refs/heads/{branch_name}", "sha": base_sha}
        requests.post(create_ref_url, headers=headers, json=branch_payload, timeout=10)

        # 3. Get existing file SHA (needed for PUT /contents)
        file_url = f"https://api.github.com/repos/{repo}/contents/{target_file}?ref={branch_name}"
        file_resp = requests.get(file_url, headers=headers, timeout=10)
        file_sha = file_resp.json().get("sha") if file_resp.status_code == 200 else None

        # 4. Commit updated file to new branch
        import base64
        content_b64 = base64.b64encode(corrected_content.encode("utf-8")).decode("utf-8")
        put_payload = {
            "message": commit_msg or "Fix: autonomous remediation by Self-Healing Pipeline",
            "content": content_b64,
            "branch": branch_name
        }
        if file_sha:
            put_payload["sha"] = file_sha

        put_resp = requests.put(file_url, headers=headers, json=put_payload, timeout=10)
        if put_resp.status_code not in (200, 201):
            return None

        # 5. Open Pull Request
        pr_url = f"https://api.github.com/repos/{repo}/pulls"
        pr_payload = {
            "title": pr_title or "🤖 Autonomous Fix for CI/CD Pipeline Failure",
            "head": branch_name,
            "base": base_branch,
            "body": pr_body or "Automated Pull Request generated by AI Pipeline Agent."
        }
        pr_resp = requests.post(pr_url, headers=headers, json=pr_payload, timeout=10)
        if pr_resp.status_code in (200, 201):
            return pr_resp.json().get("html_url")

    except Exception as exc:
        print(f"[Warning] Failed to create automated PR: {exc}")
    return None


def trigger_workflow_rerun(repo: str, run_id: str, token: Optional[str] = None) -> bool:
    """
    Reruns a failed workflow using GitHub REST API when error is transient.
    Uses: POST https://api.github.com/repos/{owner}/{repo}/actions/runs/{run_id}/rerun
    """
    auth_token = token or get_token()
    if not auth_token or not run_id:
        return False

    headers = dict(DEFAULT_HEADERS)
    headers["Authorization"] = f"Bearer {auth_token}"
    url = f"https://api.github.com/repos/{repo}/actions/runs/{run_id}/rerun"

    try:
        resp = requests.post(url, headers=headers, timeout=10)
        return resp.status_code in (200, 201)
    except Exception:
        return False
