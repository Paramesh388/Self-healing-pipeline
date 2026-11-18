# Automated Root Cause Analysis and Remediation for CI/CD Build Failures
### An AI-Powered Pipeline Prototype

> **MCA Major Project & Research Prototype**  
> **Repository:** [Paramesh388/Self-healing-pipeline](https://github.com/Paramesh388/Self-healing-pipeline)  
> **Author:** Paramesh S  
> **Core Stack:** Python 3.11+, FastAPI, Groq Cloud API (`llama-3.3-70b-versatile`), GitHub Actions, ngrok, Vanilla HTML5/CSS3/JavaScript (Dark Observability UI)

---

## 1. Quick Control: How to Shutdown & Restart

### 🛑 How to Shutdown Every Background Process
If you want to completely stop the FastAPI backend and ngrok tunnel, run this single command in **PowerShell**:

```powershell
Get-Process -Name python*,ngrok*,uvicorn* -ErrorAction SilentlyContinue | Stop-Process -Force
```

*(Alternatively, in Command Prompt: `taskkill /F /IM python.exe /T` and `taskkill /F /IM ngrok.exe /T`)*

---

### 🚀 How to Run the Entire Project From Scratch (Start to Finish)

Follow these exact steps whenever you boot up your computer or prepare for a live demonstration:

#### Step 1: Open Terminal 1 (Start FastAPI Backend)
Open PowerShell, navigate to the project directory, and launch the server:
```powershell
cd "C:\Users\PARAMESH S\OneDrive\Desktop\PRO"
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```
- Server will run at: `http://127.0.0.1:8000`

#### Step 2: Open Terminal 2 (Start ngrok Tunnel)
Open a second PowerShell window and launch the tunnel:
```powershell
ngrok http 8000
```
- ngrok will output an active public URL, for example:  
  `Forwarding https://xxxx-xxxx.ngrok-free.dev -> http://localhost:8000`

#### Step 3: Link GitHub Webhook
1. Go to your GitHub repository:  
   👉 **`https://github.com/Paramesh388/Self-healing-pipeline/settings/hooks`**
2. Click **Edit** on your existing webhook (or **Add webhook**):
   - **Payload URL:** `https://<your-ngrok-subdomain>.ngrok-free.dev/api/webhook`
   - **Content type:** `application/json`
   - **Events:** Select **Let me select individual events** → Check **Workflow runs** (`workflow_run`).
3. Click **Update webhook** / **Add webhook** (ensure the green checkmark appears).

#### Step 4: Open the Observability Dashboard
In your browser (Chrome/Edge), open:
👉 **`http://127.0.0.1:8000/`** (or open `index.html` directly)
- Confirm the status badge says: **`● Listening for GitHub Webhooks...`**
- Confirm the API indicator says: **`API Online (127.0.0.1:8000)`**

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

## 3. Two Live Demo Failure & Fix Instances

You have **two distinct real-world test cases** to demonstrate automated failure capture and self-healing. Choose either one or demonstrate both during your review.

---

### 🧪 Instance 1: Python Syntax Error in `main.py`
This scenario demonstrates what happens when a developer accidentally commits incomplete code or an unclosed parenthesis/function signature.

#### Step A: Introduce the Error
Open `main.py` in VS Code, scroll to the bottom, and add this broken line:
```python
def broken_demo(
```

#### Step B: Commit & Push to GitHub
```powershell
git add main.py
git commit -m "Test: introduce syntax error in main.py"
git push origin main
```

#### Step C: What Happens on Screen (Red Failure State)
1. GitHub Actions runs `.github/workflows/build.yml` (`python -m py_compile main.py diagnose.py`).
2. Compilation halts with `SyntaxError: '(' was never closed` and exits with code `1`.
3. GitHub sends a webhook to FastAPI.
4. Within **3 seconds**, your dashboard at `http://127.0.0.1:8000/` automatically turns **RED**:
   - Badge updates to: **`⚠️ Build Failure Detected`**
   - Telemetry displays the repository, branch, and failed run number.
   - **Groq AI RCA** outputs: *"Root Cause: An unclosed function header in main.py prevented compilation"* and provides the exact line fix.

#### Step D: Apply the Fix & Heal the Pipeline
In `main.py`, remove the line `def broken_demo(` and save the file. Then push:
```powershell
git add main.py
git commit -m "Fix: remove broken function header to heal pipeline"
git push origin main
```
- GitHub Actions compiles cleanly with exit code `0`.
- The dashboard automatically flips to **EMERALD GREEN**: **`✅ Pipeline Healed & Passing`**.

---

### 🧪 Instance 2: Indentation / Syntax Defect in `diagnose.py`
This scenario demonstrates what happens when a developer introduces an improper indentation or malformed block in a utility module.

#### Step A: Introduce the Error
Open `diagnose.py` in VS Code, scroll to the bottom, and add these misaligned lines:
```python
  def misaligned_sanitizer():
  pass
```
*(Notice the leading 2 spaces before `def`, which is invalid Python at the module level).*

#### Step B: Commit & Push to GitHub
```powershell
git add diagnose.py
git commit -m "Test: introduce indentation error in diagnose.py"
git push origin main
```

#### Step C: What Happens on Screen (Red Failure State)
1. GitHub Actions runs `python -m py_compile main.py diagnose.py`.
2. Compilation fails with:  
   `IndentationError: unexpected indent (diagnose.py)` and exits with code `1`.
3. GitHub sends a webhook to FastAPI.
4. The dashboard automatically turns **RED**:
   - Sanitized logs display the exact `IndentationError` line.
   - **Groq AI RCA** outputs: *"Root Cause: An unexpected indent at module level in diagnose.py"* with step-by-step indentation correction guidance.

#### Step D: Apply the Fix & Heal the Pipeline
In `diagnose.py`, delete the misaligned lines and save the file. Then push:
```powershell
git add diagnose.py
git commit -m "Fix: remove misaligned indentation to heal pipeline"
git push origin main
```
- GitHub Actions passes with exit code `0`.
- The dashboard automatically flips to **EMERALD GREEN**: **`✅ Pipeline Healed & Passing`**.

---

### 💡 Bonus Instant Demo: Manual Build Log Analyzer
If you want to showcase the AI diagnosis instantly **without running git push**:
1. Click the **"Manual Build Log Analyzer"** tab on `http://127.0.0.1:8000/`.
2. Click the preset button:
   - **"Python SyntaxError"** (Simulates py_compile syntax breaks)
   - **"Missing Dependency"** (Simulates `ModuleNotFoundError: No module named 'fastapi'`)
   - **"TypeScript Compile"** (Simulates Angular/React `tsc` compile errors)
3. Click **"Analyze Log with Groq AI"**.
4. In under **2 seconds**, show the evaluators:
   - **Sanitized Error Lines:** Regex filter isolates error lines, stripping 80%+ noise.
   - **Structured AI RCA:** Groq Llama-3.3-70B gives root cause + copy-pasteable terminal commands.
   - Click the **"Copy Fix"** button.

---

## 4. Quick Command Cheat-Sheet

| Action | Commands | Expected UI State |
| :--- | :--- | :--- |
| **Shutdown Everything** | `Get-Process -Name python*,ngrok*,uvicorn* -ErrorAction SilentlyContinue \| Stop-Process -Force` | All processes terminate |
| **Start Backend** | `python -m uvicorn main:app --host 127.0.0.1 --port 8000` | Port 8000 active |
| **Start Tunnel** | `ngrok http 8000` | Port 4040 active |
| **Instance 1: Break** | Add `def broken_demo(` to `main.py`<br>`git add main.py; git commit -m "break main"; git push origin main` | Turns **RED** (SyntaxError) |
| **Instance 1: Heal** | Delete `def broken_demo(` from `main.py`<br>`git add main.py; git commit -m "heal main"; git push origin main` | Turns **GREEN** (Healed) |
| **Instance 2: Break** | Add indented `  def bad(): pass` to `diagnose.py`<br>`git add diagnose.py; git commit -m "break diagnose"; git push origin main` | Turns **RED** (IndentationError) |
| **Instance 2: Heal** | Delete `  def bad(): pass` from `diagnose.py`<br>`git add diagnose.py; git commit -m "heal diagnose"; git push origin main` | Turns **GREEN** (Healed) |

---

## 5. Viva / Evaluator Technical Defense Q&A

### Q1: Why use regular expression filtering before passing logs to the LLM?
> **Answer:**  
> Real-world CI logs often exceed 5,000–20,000 lines with routine environmental logs. Passing raw logs wastes API tokens, increases latency, and increases LLM hallucination risk. Our regex filter isolates critical failure signatures (`ERROR`, `FATAL`, `FAIL`, `Exception`), reducing prompt token volume by >80% while retaining full diagnostic fidelity.

### Q2: Why did you choose Groq and Llama-3.3-70B?
> **Answer:**  
> Groq’s LPU (Language Processing Unit) architecture delivers generation speeds of ~250–300 tokens/sec. For developer experience in CI/CD, getting an actionable diagnosis in under 2 seconds is critical. Furthermore, our code implements automatic fallback models in case the requested model is unavailable.

### Q3: How does the backend receive build updates in real-time?
> **Answer:**  
> We leverage GitHub Actions' native webhook architecture via the `workflow_run` event. When a workflow concludes, GitHub dispatches an event payload to our FastAPI endpoint exposed via ngrok, triggering asynchronous log processing, regex sanitization, and AI diagnosis.

### Q4: How is security handled in this prototype?
> **Answer:**  
> - API keys are stored exclusively in `.env` and loaded at runtime via `python-dotenv`.
> - `.env` and bytecode directories (`__pycache__/`, `*.pyc`) are explicitly ignored by `.gitignore`.
> - All repository files were audited to guarantee zero hardcoded credentials exist in source code.

---

## 6. License & Acknowledgements
- Developed for academic research and evaluation in Advanced Software Engineering & DevOps Automation.
- Built using open-source tools: [FastAPI](https://fastapi.tiangolo.com/), [Groq Cloud](https://console.groq.com/), and [GitHub Actions](https://github.com/features/actions).
