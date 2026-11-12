import os
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from diagnose import clean_log_text, diagnose_error

load_dotenv()

# Initialize the FastAPI app
app = FastAPI(title="Self-Healing CI/CD API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Data Models ---
class LogPayload(BaseModel):
    raw_log: str


class DiagnosisResponse(BaseModel):
    sanitized_log: str
    diagnosis: str


def run_ai_diagnosis(sanitized_log: str) -> str:
    """Runs Groq RCA with automatic model fallback on sanitized log lines."""
    if not sanitized_log.strip():
        return "No critical error lines (ERROR, FATAL, FAIL, Exception) detected in the provided log."
    try:
        return diagnose_error(sanitized_log)
    except Exception as exc:
        return f"AI Diagnosis Failed: {exc}"


# Store the latest GitHub status in memory for the frontend dashboard
latest_incident = {
    "status": "waiting",  # Can be "waiting", "failure", or "healed"
    "repo": "",
    "branch": "",
    "commit_msg": "",
    "workflow_name": "",
    "run_number": None,
    "error_log": "",
    "diagnosis": "",
    "timestamp": "",
}


@app.get("/")
async def serve_dashboard():
    """Serves the dashboard UI when accessed directly from the backend root."""
    index_path = Path(__file__).resolve().parent / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="Dashboard index.html not found.")
    return FileResponse(index_path)


# --- API Endpoints ---
@app.post("/api/diagnose", response_model=DiagnosisResponse)
async def diagnose_build(payload: LogPayload):
    if not payload.raw_log.strip():
        raise HTTPException(status_code=400, detail="Log cannot be empty.")

    cleaned = clean_log_text(payload.raw_log)
    diagnosis = run_ai_diagnosis(cleaned)

    return DiagnosisResponse(
        sanitized_log=cleaned,
        diagnosis=diagnosis,
    )


@app.get("/api/latest-webhook")
async def get_latest_webhook():
    """Endpoint for index.html to fetch the latest automated GitHub status."""
    return latest_incident


@app.post("/api/webhook")
async def handle_github_webhook(request: Request):
    global latest_incident
    payload = await request.json()

    if "workflow_run" in payload:
        wf = payload["workflow_run"]
        run_status = wf.get("status")
        conclusion = wf.get("conclusion")

        print(f"GitHub Action Status: {run_status} | Conclusion: {conclusion}")

        repo_name = payload.get("repository", {}).get("full_name", "Paramesh388/Self-healing-pipeline")
        branch_name = wf.get("head_branch", "main")
        commit_msg = wf.get("head_commit", {}).get("message", "Update pipeline")
        workflow_name = wf.get("name", "CI Pipeline")
        run_number = wf.get("run_number", 1)
        updated_at = wf.get("updated_at", "Just now")

        # 1. IF THE BUILD FAILED -> TURN DASHBOARD RED & CALL GROQ AI
        if conclusion == "failure":
            print("Build failed! Triggering Groq AI for root cause analysis...")

            error_context = (
                f"FATAL: GitHub Actions Workflow '{workflow_name}' (Run #{run_number}) failed.\n"
                f"Repository: {repo_name} | Branch: {branch_name}\n"
                f"Triggering Commit: '{commit_msg}'\n"
                f"ERROR: Process completed with exit code 1 during build step execution."
            )

            diagnosis = run_ai_diagnosis(error_context)

            latest_incident = {
                "status": "failure",
                "repo": repo_name,
                "branch": branch_name,
                "commit_msg": commit_msg,
                "workflow_name": workflow_name,
                "run_number": run_number,
                "error_log": error_context,
                "diagnosis": diagnosis,
                "timestamp": updated_at,
            }

        # 2. IF THE BUILD SUCCEEDED -> TURN DASHBOARD GREEN (HEALED!)
        elif conclusion == "success":
            print("Build succeeded! Pipeline is healed and passing.")

            latest_incident = {
                "status": "healed",
                "repo": repo_name,
                "branch": branch_name,
                "commit_msg": commit_msg,
                "workflow_name": workflow_name,
                "run_number": run_number,
                "error_log": f"SUCCESS: Workflow '{workflow_name}' (Run #{run_number}) completed with exit code 0.",
                "diagnosis": "No errors detected. The previous failure has been resolved and all CI checks passed!",
                "timestamp": updated_at,
            }

    return {"status": "success", "message": "Webhook processed"}

