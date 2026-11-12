from fastapi import FastAPI, HTTPException
from diagnose import diagnose_error, clean_log
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import re
import os
from groq import Groq
from fastapi import Request

# Initialize the FastAPI app and Groq client
app = FastAPI(title="Self-Healing CI/CD API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = Groq(
    api_key="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")

# --- Data Models ---
class LogPayload(BaseModel):
    raw_log: str

class DiagnosisResponse(BaseModel):
    sanitized_log: str
    diagnosis: str

# --- Core Engine Functions ---
def clean_log_text(raw_text: str) -> str:
    """Filters string payload for critical errors."""
    pattern = re.compile(r"(ERROR|FATAL|FAIL|Exception)")
    matching_lines = [line for line in raw_text.splitlines() if pattern.search(line)]
    return "\n".join(matching_lines)

def get_groq_diagnosis(sanitized_log: str) -> str:
    """Calls Groq API with the cleaned log."""
    if not sanitized_log.strip():
        return "No errors detected in the provided log."
    
    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert DevOps engineer. Analyze the following CI/CD log, identify the root cause of the failure, and provide a step-by-step fix."
                },
                {
                    "role": "user",
                    "content": sanitized_log,
                }
            ],
            model="openai/gpt-oss-120b",
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        return f"AI Diagnosis Failed: {str(e)}"

# --- API Endpoint ---
@app.post("/api/diagnose", response_model=DiagnosisResponse)
async def diagnose_build(payload: LogPayload):
    if not payload.raw_log.strip():
        raise HTTPException(status_code=400, detail="Log cannot be empty.")
    
    cleaned = clean_log_text(payload.raw_log)
    diagnosis = get_groq_diagnosis(cleaned)
    
    return DiagnosisResponse(
        sanitized_log=cleaned,
        diagnosis=diagnosis
    )
    
# Store the latest GitHub failure in memory for the frontend dashboard
latest_incident = {
    "has_incident": False,
    "repo": "",
    "branch": "",
    "commit_msg": "",
    "error_log": "",
    "diagnosis": "",
    "timestamp": ""
}

@app.get("/api/latest-webhook")
async def get_latest_webhook():
    """Endpoint for index.html to fetch the latest automated GitHub diagnosis."""
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
        
        if conclusion == "failure":
            print("Build failed! Triggering Groq AI for root cause analysis...")
            
            # Extract real details from the GitHub webhook payload
            repo_name = payload.get("repository", {}).get("full_name", "Paramesh388/Self-healing-pipeline")
            branch_name = wf.get("head_branch", "main")
            commit_msg = wf.get("head_commit", {}).get("message", "Update pipeline")
            workflow_name = wf.get("name", "CI Pipeline")
            run_number = wf.get("run_number", 1)
            updated_at = wf.get("updated_at", "Just now")
            
            # Build a realistic error context from the GitHub payload
            error_context = (
                f"FATAL: GitHub Actions Workflow '{workflow_name}' (Run #{run_number}) failed.\n"
                f"Repository: {repo_name} | Branch: {branch_name}\n"
                f"Triggering Commit: '{commit_msg}'\n"
                f"ERROR: Process completed with exit code 1 during build step execution."
            )
            
            # Get diagnosis from Groq AI
            diagnosis = diagnose_error(error_context)
            
            print("\n--- GROQ AI DIAGNOSIS ---")
            print(diagnosis)
            print("-------------------------\n")
            
            # Save the result so index.html can display it automatically!
            latest_incident = {
                "has_incident": True,
                "repo": repo_name,
                "branch": branch_name,
                "commit_msg": commit_msg,
                "error_log": error_context,
                "diagnosis": diagnosis,
                "timestamp": updated_at
            }
            
    return {"status": "success", "message": "Webhook processed"}