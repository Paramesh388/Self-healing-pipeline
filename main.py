"""
main.py - FastAPI Backend with Real-Time WebSockets, SQLite Persistence, and GitHub Integration
"""

import os
import hmac
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from diagnose import clean_log_text, diagnose_structured
from db import save_incident, get_latest_incident, get_recent_incidents, get_analytics_summary
import github_client

load_dotenv()

app = FastAPI(
    title="Self-Healing CI/CD Pipeline API",
    description="Real-Time Automated Root Cause Analysis & Autonomous Remediation Platform",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- WebSocket Connection Manager ---
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: Dict[str, Any]):
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception:
                self.disconnect(connection)


ws_manager = ConnectionManager()


# --- Pydantic Data Models ---
class LogPayload(BaseModel):
    raw_log: str


class CIReportPayload(BaseModel):
    run_id: str
    run_number: int
    repo: str
    branch: str
    commit_msg: str = ""
    commit_sha: str = ""
    raw_log: str


class DiagnosisResponse(BaseModel):
    sanitized_log: str
    diagnosis: str
    failure_type: str = "GeneralFailure"
    defect_file: str = ""
    defect_line: str = ""
    token_reduction_pct: float = 0.0
    inference_latency_ms: float = 0.0


ci_failure_reports = {}


# --- Core Web Routes ---
@app.get("/")
async def serve_dashboard():
    """Serves the dashboard UI."""
    index_path = Path(__file__).resolve().parent / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="Dashboard index.html not found.")
    return FileResponse(index_path)


@app.websocket("/ws/telemetry")
async def websocket_telemetry_endpoint(websocket: WebSocket):
    """Real-time WebSocket telemetry stream for instant dashboard status updates."""
    await ws_manager.connect(websocket)
    # Immediately send the latest state upon connection
    try:
        latest = get_latest_incident()
        await websocket.send_json({"type": "INIT_STATE", "data": latest})
        while True:
            # Keep connection open, handle client ping/pong
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception:
        ws_manager.disconnect(websocket)


# --- REST API Endpoints ---
@app.get("/api/latest-webhook")
async def get_latest_status():
    """Returns the latest automated pipeline state from SQLite."""
    return get_latest_incident()


@app.get("/api/analytics")
async def get_analytics():
    """Returns empirical research metrics, token reduction averages, and failure distributions."""
    return get_analytics_summary()


@app.get("/api/incidents")
async def get_incidents():
    """Returns the most recent 10 build incident records."""
    return get_recent_incidents(10)


@app.post("/api/diagnose", response_model=DiagnosisResponse)
async def diagnose_build(payload: LogPayload):
    """On-demand manual log diagnosis with token and latency metrics."""
    if not payload.raw_log.strip():
        raise HTTPException(status_code=400, detail="Log cannot be empty.")

    cleaned = clean_log_text(payload.raw_log)
    structured = diagnose_structured(cleaned or payload.raw_log, payload.raw_log)

    return DiagnosisResponse(
        sanitized_log=cleaned,
        diagnosis=structured["diagnosis"],
        failure_type=structured.get("failure_type", "GeneralFailure"),
        defect_file=structured.get("defect_file", ""),
        defect_line=structured.get("defect_line", ""),
        token_reduction_pct=structured.get("token_reduction_pct", 0.0),
        inference_latency_ms=structured.get("inference_latency_ms", 0.0),
    )


@app.post("/api/diagnose-file")
async def diagnose_uploaded_file(request: Request):
    """Upload a raw .log or .txt file directly for instant diagnosis."""
    content = await request.body()
    raw_log = content.decode("utf-8", errors="replace")
    if not raw_log.strip():
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    cleaned = clean_log_text(raw_log)
    structured = diagnose_structured(cleaned or raw_log, raw_log)

    return {
        "file_name": request.headers.get("X-File-Name", "uploaded.log"),
        "sanitized_log": cleaned,
        "diagnosis": structured["diagnosis"],
        "failure_type": structured.get("failure_type", "GeneralFailure"),
        "defect_file": structured.get("defect_file", ""),
        "defect_line": structured.get("defect_line", ""),
        "token_reduction_pct": structured.get("token_reduction_pct", 0.0),
        "inference_latency_ms": structured.get("inference_latency_ms", 0.0),
    }


@app.post("/api/rerun/{run_id}")
async def rerun_transient_workflow(run_id: str, repo: str = "Paramesh388/Self-healing-pipeline"):
    """Triggers an automated workflow re-run via GitHub Actions API for transient errors."""
    success = github_client.trigger_workflow_rerun(repo, run_id)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to trigger re-run. Verify GITHUB_TOKEN has actions write permissions.")
    return {"status": "rerun_triggered", "run_id": run_id}


@app.post("/api/ci-result")
async def receive_ci_result(payload: CIReportPayload, request: Request):
    """Receives direct compiler/test output from the GitHub Actions runner step."""
    expected_token = os.getenv("CI_REPORT_TOKEN", "")
    supplied_token = request.headers.get("X-CI-Report-Token", "")
    if expected_token and not hmac.compare_digest(supplied_token, expected_token):
        raise HTTPException(status_code=401, detail="Invalid CI report token.")

    raw_log = payload.raw_log[:100_000]
    cleaned = clean_log_text(raw_log)
    structured = diagnose_structured(cleaned or raw_log, raw_log)

    incident_data = {
        "status": "failure",
        "repo": payload.repo,
        "branch": payload.branch,
        "commit_msg": payload.commit_msg,
        "commit_sha": payload.commit_sha,
        "workflow_name": "CI Pipeline",
        "run_number": payload.run_number,
        "run_id": payload.run_id,
        "failure_type": structured["failure_type"],
        "defect_file": structured["defect_file"],
        "defect_line": structured["defect_line"],
        "raw_log_size": structured["raw_log_size"],
        "sanitized_log_size": structured["sanitized_log_size"],
        "token_reduction_pct": structured["token_reduction_pct"],
        "inference_latency_ms": structured["inference_latency_ms"],
        "error_log": cleaned or raw_log,
        "diagnosis": structured["diagnosis"],
        "suggested_patch": structured["suggested_patch"],
        "is_transient": structured["is_transient"]
    }

    ci_failure_reports[payload.run_id] = incident_data
    save_incident(incident_data)
    await ws_manager.broadcast({"type": "STATUS_UPDATE", "data": incident_data})

    return {"status": "received", "run_id": payload.run_id}


@app.post("/api/webhook")
async def handle_github_webhook(request: Request):
    """Processes GitHub Actions workflow_run webhook deliveries."""
    payload = await request.json()

    if "workflow_run" not in payload:
        return {"status": "ignored", "message": "No workflow_run event present."}

    wf = payload["workflow_run"]
    conclusion = wf.get("conclusion")
    run_id = str(wf.get("id", ""))
    repo_name = payload.get("repository", {}).get("full_name", "Paramesh388/Self-healing-pipeline")
    branch_name = wf.get("head_branch", "main")
    commit_msg = wf.get("head_commit", {}).get("message", "Update pipeline")
    commit_sha = wf.get("head_commit", {}).get("id", "")
    workflow_name = wf.get("name", "CI Pipeline")
    run_number = wf.get("run_number", 1)
    updated_at = wf.get("updated_at")

    # 1. BUILD FAILED -> FETCH LOGS, DIAGNOSE & REMEDIATE
    if conclusion == "failure":
        print(f"[CI Webhook] Build Failed: Run #{run_number} ({run_id})")

        # Step A: Check if a direct CI report arrived, else fetch via GitHub REST API
        report = ci_failure_reports.get(run_id)
        raw_error_text = ""

        if report:
            raw_error_text = report["error_log"]
        else:
            # Attempt to fetch real runner logs via GitHub API
            log_success, fetched_logs = github_client.fetch_run_logs(repo_name, run_id)
            if log_success:
                raw_error_text = fetched_logs
            else:
                raw_error_text = (
                    f"FATAL: GitHub Actions Workflow '{workflow_name}' (Run #{run_number}) failed.\n"
                    f"Repository: {repo_name} | Branch: {branch_name}\n"
                    f"Triggering Commit: '{commit_msg}'\n"
                    f"ERROR: Process completed with exit code 1 during build step execution."
                )

        # Step B: Sanitize and Diagnose
        cleaned_logs = clean_log_text(raw_error_text)
        diagnosis_record = diagnose_structured(cleaned_logs or raw_error_text, raw_error_text)

        pr_url = ""
        comment_url = ""

        # Step C: Closed-Loop Auto-PR & Commit Comment (if GITHUB_TOKEN is available)
        if not diagnosis_record["is_transient"]:
            # Post comment to commit
            comment_body = (
                f"### 🤖 AI Pipeline Root Cause Analysis & Remediation\n\n"
                f"**Workflow:** `{workflow_name}` (Run #{run_number}) | **Category:** `{diagnosis_record['failure_type']}`\n\n"
                f"{diagnosis_record['diagnosis']}"
            )
            comment_url = github_client.post_commit_comment(repo_name, commit_sha, comment_body) or ""

            # Attempt automated PR if file and patch are isolated
            if diagnosis_record["defect_file"] and diagnosis_record["suggested_patch"]:
                pr_title = f"fix(ci): autonomous repair for {diagnosis_record['failure_type']} in Run #{run_number}"
                pr_body = (
                    f"## 🤖 Autonomous Self-Healing Pull Request\n\n"
                    f"This PR was generated automatically by the AI-Powered Pipeline Prototype.\n\n"
                    f"### Root Cause\n{diagnosis_record['diagnosis']}\n\n"
                    f"**Target Defect:** `{diagnosis_record['defect_file']}` (Line: {diagnosis_record['defect_line'] or 'N/A'})\n"
                )
                pr_url = github_client.create_automated_fix_pr(
                    repo=repo_name,
                    base_branch=branch_name,
                    target_file=diagnosis_record["defect_file"],
                    corrected_content=diagnosis_record["suggested_patch"],
                    commit_msg=f"Fix: autonomous repair for {diagnosis_record['defect_file']}",
                    pr_title=pr_title,
                    pr_body=pr_body
                ) or ""

        incident_data = {
            "status": "failure",
            "repo": repo_name,
            "branch": branch_name,
            "commit_msg": commit_msg,
            "commit_sha": commit_sha,
            "workflow_name": workflow_name,
            "run_number": run_number,
            "run_id": run_id,
            "failure_type": diagnosis_record["failure_type"],
            "defect_file": diagnosis_record["defect_file"],
            "defect_line": diagnosis_record["defect_line"],
            "raw_log_size": diagnosis_record["raw_log_size"],
            "sanitized_log_size": diagnosis_record["sanitized_log_size"],
            "token_reduction_pct": diagnosis_record["token_reduction_pct"],
            "inference_latency_ms": diagnosis_record["inference_latency_ms"],
            "error_log": cleaned_logs or raw_error_text,
            "diagnosis": diagnosis_record["diagnosis"],
            "suggested_patch": diagnosis_record["suggested_patch"],
            "pr_url": pr_url,
            "comment_url": comment_url,
            "is_transient": diagnosis_record["is_transient"],
            "timestamp": updated_at
        }

        save_incident(incident_data)
        await ws_manager.broadcast({"type": "STATUS_UPDATE", "data": incident_data})

    # 2. BUILD SUCCEEDED -> MARK HEALED
    elif conclusion == "success":
        print(f"[CI Webhook] Build Succeeded: Run #{run_number} ({run_id})")

        healed_data = {
            "status": "healed",
            "repo": repo_name,
            "branch": branch_name,
            "commit_msg": commit_msg,
            "commit_sha": commit_sha,
            "workflow_name": workflow_name,
            "run_number": run_number,
            "run_id": run_id,
            "failure_type": "SuccessExit0",
            "defect_file": "",
            "defect_line": "",
            "raw_log_size": 0,
            "sanitized_log_size": 0,
            "token_reduction_pct": 0.0,
            "inference_latency_ms": 0.0,
            "error_log": f"SUCCESS: Workflow '{workflow_name}' (Run #{run_number}) completed with exit code 0.",
            "diagnosis": "No errors detected. The pipeline has successfully healed and all CI verification checks passed!",
            "suggested_patch": "",
            "pr_url": "",
            "comment_url": "",
            "is_transient": False,
            "timestamp": updated_at
        }

        save_incident(healed_data)
        await ws_manager.broadcast({"type": "STATUS_UPDATE", "data": healed_data})

    return {"status": "success", "message": "Webhook processed successfully."}
