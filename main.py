from fastapi import FastAPI, HTTPException
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
    
@app.post("/api/webhook")
async def handle_github_webhook(request: Request):
    payload = await request.json()
    
    # Check if the payload contains workflow run details
    if "workflow_run" in payload:
        run_status = payload["workflow_run"]["status"]
        conclusion = payload["workflow_run"]["conclusion"]
        
        print(f"GitHub Action Status: {run_status} | Conclusion: {conclusion}")
        
        # If the build failed, we trigger the self-healing AI
        if conclusion == "failure":
            print("Build failed! Triggering Groq AI for root cause analysis...")
            # We will add the call to your diagnose.py here next
            
    return {"status": "success", "message": "Webhook processed"}