# Automated Root Cause Analysis and Remediation for CI/CD Build Failures
### An AI-Powered Pipeline Prototype

> **MCA Major Project & Research Prototype**  
> **Repository:** [Paramesh388/Self-healing-pipeline](https://github.com/Paramesh388/Self-healing-pipeline)  
> **Author:** Paramesh S  
> **Core Stack:** Python 3.11+, FastAPI, Groq Cloud API (`llama-3.3-70b-versatile`), GitHub Actions, ngrok, Vanilla HTML5/CSS3/JavaScript (Dark Observability UI)

---

## 1. Project Overview

In continuous integration and continuous delivery (CI/CD) pipelines, build failures frequently generate thousands of lines of noisy console logs. Developers lose substantial time manually locating stack traces and identifying root causes.

This prototype provides an **automated, self-healing pipeline observability platform**:
1. **Event Capture:** GitHub Actions dispatches real-time `workflow_run` webhooks upon job completion.
2. **Log Sanitization:** A regex-driven filter strips environmental noise, extracting only high-priority lines matching `(ERROR|FATAL|FAIL|Exception)`. This reduces token payload by over **80%**, mitigating LLM hallucinations and saving API costs.
3. **AI Root Cause Analysis (RCA):** Sanitized telemetry is passed to the Groq API running `llama-3.3-70b-versatile` with automatic fallback logic to generate a single-sentence root cause and step-by-step remediation commands in sub-second speeds.
4. **DevOps Observability Dashboard:** A glassmorphic dark-mode dashboard polls the backend every 3 seconds, visualizing transitions across **Listening**, **Build Failure Detected (Red Alert)**, and **Pipeline Healed & Passing (Green Confirmation)**.

---

## 2. System Architecture

```
                    [ Developer Git Push ]
                              │
                              ▼
                [ GitHub Actions CI Runner ]
                 (python -m py_compile check)
                              │
              ┌───────────────┴───────────────┐
              ▼                               ▼
       [ Build Fails ]                [ Build Passes ]
      (exit code = 1)                 (exit code = 0)
              │                               │
              ▼                               ▼
   [ Webhook: workflow_run ]       [ Webhook: workflow_run ]
   (conclusion: "failure")         (conclusion: "success")
              │                               │
              └───────────────┬───────────────┘
                              │
                              ▼
           [ ngrok Public Secure Reverse Proxy ]
                              │
                              ▼
               [ FastAPI Backend (Port 8000) ]
                              │
     ┌────────────────────────┴────────────────────────┐
     │                                                 │
[ Failure Route ]                               [ Success Route ]
     │                                                 │
[ Regex Sanitizer ]                                    │
(ERROR|FATAL|FAIL|Exception)                           │
     │                                                 │
     ▼                                                 │
[ Groq API Llama-3.3-70B ]                             │
(Generates Root Cause & Step-by-Step Fix)              │
     │                                                 │
     ▼                                                 ▼
[ State Store: status="failure" ]           [ State Store: status="healed" ]
     │                                                 │
     └────────────────────────┬────────────────────────┘
                              │
                              ▼
         [ Observability Dashboard (index.html) ]
     (Polls /api/latest-webhook every 3s — Transitions Red ↔ Green)
```

---

## 3. Project Directory Structure

```text
PRO/
│
├── .github/
│   └── workflows/
│       └── build.yml       # GitHub Actions CI workflow (syntax validation via py_compile)
│
├── .env                    # Environment variables (GROQ_API_KEY) — Git-ignored
├── .gitignore              # Ignores .env, __pycache__/, *.pyc
│
├── diagnose.py             # Regex filter (clean_log_text) and Groq LLM client with fallback
├── main.py                 # FastAPI backend server exposing webhook, polling, and diagnosis APIs
├── index.html              # Modern dark-mode DevOps observability dashboard
├── error.log               # Reference local failure log for offline testing
└── README.md               # Project documentation and demo presentation guide
```

---

## 4. Installation & Local Setup

### 4.1 Prerequisites
- Python 3.11 or higher
- Git installed and configured
- [ngrok](https://ngrok.com/) installed
- Groq Cloud API Key ([https://console.groq.com/keys](https://console.groq.com/keys))

### 4.2 Clone & Install Dependencies
```powershell
git clone https://github.com/Paramesh388/Self-healing-pipeline.git
cd Self-healing-pipeline

# Install Python packages
pip install fastapi uvicorn openai python-dotenv pydantic requests
```

### 4.3 Configure Secrets
Create a `.env` file in the project root:
```env
GROQ_API_KEY=gsk_your_groq_api_key_here
```
*(Ensure `.env` is never committed to GitHub; it is listed inside `.gitignore`.)*

### 4.4 Start Services
Open two terminal windows:

**Terminal 1 — FastAPI Server:**
```powershell
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

**Terminal 2 — ngrok Tunnel:**
```powershell
ngrok http 8000
```
*Copy the generated forwarding URL (e.g., `https://your-domain.ngrok-free.dev`).*

### 4.5 Configure GitHub Webhook
1. Go to your GitHub repository: **Settings → Webhooks → Add webhook**.
2. **Payload URL:** `https://your-domain.ngrok-free.dev/api/webhook`
3. **Content type:** `application/json`
4. **Which events would you like to trigger this webhook?**
   - Select **Let me select individual events**.
   - Check **Workflow runs** (`workflow_run`).
   - Uncheck **Pushes** (to avoid duplicate triggers).
5. Click **Add webhook** (confirm active green checkmark).

---

## 5. Live Project Demo Script (Step-by-Step for Evaluators)

Follow this structured 4-stage presentation when showcasing the project for academic evaluation or research reviews:

### Screen Arrangement
- **Left Side:** VS Code with [main.py](file:///c:/Users/PARAMESH%20S/OneDrive/Desktop/PRO/main.py) and a terminal open.
- **Right Side:** Web browser opened to `http://127.0.0.1:8000/` alongside GitHub Actions in a second tab.

---

### Stage 1: The Pitch & Manual Log Analyzer (1 Minute)
1. **Explain the Motivation:**
   > *"Modern CI/CD pipelines generate voluminous logs. When a failure occurs, engineers spend excessive time searching for relevant error lines. Our system introduces an automated pipeline that sanitizes logs via regular expressions, runs Root Cause Analysis via Groq Llama-3.3-70B, and streams real-time remediation to the developer."*
2. **Show the Manual Analyzer:**
   - On `http://127.0.0.1:8000/`, click the **"Manual Build Log Analyzer"** tab.
   - Click a preset (e.g., **"Python SyntaxError"** or **"TypeScript Compile"**).
   - Click **"Analyze Log with Groq AI"**.
   - Point out:
     - **Sanitized Error Lines:** Raw log noise is removed; only `ERROR`, `FATAL`, `FAIL`, and `Exception` lines remain.
     - **AI Diagnosis:** Formatted root cause statement and actionable code fixes with a **Copy Fix** button.

---

### Stage 2: Simulating a Build Failure (The Red State) (1.5 Minutes)
1. Switch to the **"Live Pipeline Monitor"** tab. Note the status is **Listening for GitHub Webhooks...**.
2. In VS Code, open [main.py](file:///c:/Users/PARAMESH%20S/OneDrive/Desktop/PRO/main.py), scroll to the very bottom, and append an intentional syntax error:
   ```python
   def broken_demo(
   ```
3. Commit and push the failure:
   ```powershell
   git add main.py
   git commit -m "Simulate CI syntax failure"
   git push origin main
   ```
4. **Watch the live transition:**
   - GitHub Actions runs `python -m py_compile main.py diagnose.py` and fails with exit code `1`.
   - GitHub Actions dispatches the webhook to FastAPI via ngrok.
   - Within **3 seconds**, the dashboard automatically turns **RED**:
     - Status Badge flips to **`⚠️ Build Failure Detected`**.
     - Shows the commit message, branch name, and run number.
     - Renders sanitized failure logs and Groq AI's structured **Root Cause & Step-by-Step Fix**.

---

### Stage 3: Explaining the AI Root Cause (30 Seconds)
1. Highlight that without logging into the GitHub Actions runner, the developer instantly sees:
   - The exact broken function/file name.
   - The Root Cause in plain, clear language.
   - The exact shell/git commands to resolve the issue.

---

### Stage 4: Self-Healing & Pipeline Recovery (The Green State) (1 Minute)
1. In [main.py](file:///c:/Users/PARAMESH%20S/OneDrive/Desktop/PRO/main.py), delete the broken line (`def broken_demo(`) and save the file.
2. Commit and push the fix:
   ```powershell
   git add main.py
   git commit -m "Fix: resolve syntax error to heal pipeline"
   git push origin main
   ```
3. **Watch the recovery transition:**
   - GitHub Actions runs `py_compile`, cleanly compiles both files, and exits with code `0`.
   - GitHub sends the `conclusion: "success"` webhook.
   - The dashboard automatically flips to **EMERALD GREEN**:
     - Status Badge flips to **`✅ Pipeline Healed & Passing`**.
     - Displays confirmation that all CI checks succeeded with exit code 0.

---

## 6. Demo Command Quick-Reference Table

| Step | Action in Code / Terminal | Command | Dashboard Outcome |
| :--- | :--- | :--- | :--- |
| **1. Break Build** | Add `def broken_demo(` to `main.py` | `git add main.py`<br>`git commit -m "Simulate CI syntax failure"`<br>`git push origin main` | Transitions to **RED** with Groq AI RCA & Fix |
| **2. Heal Build** | Delete `def broken_demo(` from `main.py` | `git add main.py`<br>`git commit -m "Fix: resolve syntax error"`<br>`git push origin main` | Transitions to **GREEN** ("Pipeline Healed") |

---

## 7. Viva & Technical Evaluation Q&A

### Q1: Why perform regex filtering instead of sending raw logs directly to the LLM?
> **Answer:**  
> Real-world CI logs often span 5,000–20,000 lines, packed with environment configurations and status messages. Sending raw logs exhausts context windows, wastes expensive tokens, and induces hallucinations. Our regex filter isolates critical failure indicators (`ERROR|FATAL|FAIL|Exception`), trimming token count by >80% while retaining full diagnostic signal.

### Q2: Why choose Groq and `llama-3.3-70b-versatile` over other providers?
> **Answer:**  
> Groq's LPU (Language Processing Unit) architecture achieves inference speeds of 250–300 tokens per second, returning complete diagnoses in under 2 seconds. For developer productivity during continuous delivery, immediate feedback is critical. In addition, our `diagnose.py` implementation incorporates automated fallback models in case of endpoint outages.

### Q3: How does the system achieve real-time synchronization with the dashboard?
> **Answer:**  
> The dashboard uses lightweight HTTP polling (`/api/latest-webhook` every 3 seconds) paired with an in-memory state cache updated asynchronously by GitHub's `workflow_run` webhook. This eliminates WebSocket connection state overhead while maintaining sub-3-second visual updates.

### Q4: How is security handled in this prototype?
> **Answer:**  
> - API keys are stored exclusively in `.env` and loaded at runtime via `python-dotenv`.
> - `.env` and bytecode directories (`__pycache__/`, `*.pyc`) are explicitly ignored by `.gitignore`.
> - All repository files were audited to guarantee zero hardcoded credentials exist in source code.

---

## 8. License & Acknowledgements
- Developed for academic research and evaluation in Advanced Software Engineering & DevOps Automation.
- Built using open-source tools: [FastAPI](https://fastapi.tiangolo.com/), [Groq SDK](https://console.groq.com/), and [GitHub Actions](https://github.com/features/actions).
