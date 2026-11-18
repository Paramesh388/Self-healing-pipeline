# Automated Root Cause Analysis and Remediation for CI/CD Build Failures
### An AI-Powered Pipeline Prototype

> **MCA Major Project & Research Prototype**  
> **Repository:** [Paramesh388/Self-healing-pipeline](https://github.com/Paramesh388/Self-healing-pipeline)  
> **Author:** Paramesh S  
> **Core Stack:** Python 3.11+, FastAPI, Groq Cloud API (`llama-3.3-70b-versatile`), WebSockets, SQLite, GitHub Actions, Docker, Vanilla HTML5/CSS3/JavaScript (Dark Observability UI)

---

## 1. Quick Control: How to Shutdown & Restart

### 🛑 How to Shutdown Every Background Process
To completely stop the FastAPI server and ngrok tunnel, run this single command in **PowerShell**:

```powershell
Get-Process -Name python*,ngrok*,uvicorn* -ErrorAction SilentlyContinue | Stop-Process -Force
```

---

### 🚀 How to Run the Entire Project From Scratch (Start to Finish)

Follow these exact steps whenever you boot up your computer or prepare for a live demonstration:

#### Step 1: Open Terminal 1 (Start FastAPI Backend)
Open PowerShell, navigate to the project directory, and launch the server:
```powershell
cd "C:\Users\PARAMESH S\OneDrive\Desktop\PRO"
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```
- Server will run at: `http://127.0.0.1:8000` (WebSockets stream active at `/ws/telemetry`)

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

*(Optional for Real Runner Logs & Auto-PRs: Add `GITHUB_TOKEN=ghp_...` with repo permissions to `.env` to allow autonomous GitHub PR creation and commit comments!)*

#### Step 4: Open the Observability Dashboard
In your browser (Chrome/Edge), open:
👉 **`http://127.0.0.1:8000/`**
- Confirm the connection indicator says: **`● WebSocket Live (0ms delay)`** (instant real-time push!).

---

## 2. Advanced Platform Architecture

```
                    [ Developer Git Push in VS Code ]
                                   │
                                   ▼
                     [ GitHub Actions CI Runner ]
                (python -m py_compile syntax verification)
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
             [ FastAPI Backend (Port 8000 & WebSockets) ]
                                   │
          ┌────────────────────────┴────────────────────────┐
          │                                                 │
     [ Failure Route ]                               [ Success Route ]
          │                                                 │
[ 1. GitHub API Runner Log Fetch ]                          │
(GET /actions/runs/{id}/logs)                               │
          │                                                 │
[ 2. Regex Noise Sanitizer ]                                │
(85-95% Token Reduction)                                    │
          │                                                 │
[ 3. Deterministic vs Transient Classifier ]                │
          │                                                 │
[ 4. Groq API Llama-3.3-70B RCA ]                           │
(Root Cause, Defect Line & Code Fix)                        │
          │                                                 │
[ 5. Autonomous Auto-PR / Commit Comment ]                  │
(GitHub REST API via GITHUB_TOKEN)                          │
          │                                                 │
          ▼                                                 ▼
[ 6. SQLite Persistent Storage ]              [ 6. SQLite Persistent Storage ]
(incidents.db - MTTD/MTTR/Metrics)            (Records Healed Status & Run #)
          │                                                 │
          └────────────────────────┬────────────────────────┘
                                   │
                                   ▼
                 [ Real-Time WebSocket Telemetry ]
                 (/ws/telemetry — Zero Polling Delay)
                                   │
                                   ▼
              [ Observability Dashboard (index.html) ]
     (3 Tabs: Live Pipeline Monitor, Drag-and-Drop Ingestion, Research Metrics)
```

---

## 3. Two Live Demo Failure & Fix Instances

You have **two distinct real-world test cases** to demonstrate failure detection, exact defect isolation, and automatic self-healing.

---

### 🧪 Instance 1: Python Syntax Error in `main.py`
*Simulates a developer committing unclosed syntax or an incomplete function.*

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
1. GitHub Actions runs `.github/workflows/build.yml` (`py_compile` check).
2. Compilation halts with `SyntaxError: '(' was never closed` and exits with code `1`.
3. GitHub dispatches the webhook to FastAPI.
4. **Instantly via WebSockets**, your dashboard at `http://127.0.0.1:8000/` turns **RED**:
   - Status Badge updates to: **`⚠️ Build Failure Detected`**
   - **Defect Location Ribbon:** Displays `Defect Location: main.py:line 152` | `Category: SyntaxError` | `Token Reduction: >90%`.
   - **Groq AI RCA:** Formats the Root Cause, Defect Location, Step-by-Step Fix, and Suggested Code Fix.
   - If `GITHUB_TOKEN` is set, a **`🔗 View Autonomous PR`** button appears directly linking to GitHub!

#### Step D: Apply the Fix & Heal the Pipeline
In `main.py`, delete `def broken_demo(` and push:
```powershell
git add main.py
git commit -m "Fix: remove broken syntax to heal pipeline"
git push origin main
```
- GitHub Actions compiles cleanly with exit code `0`.
- The dashboard automatically flips to **EMERALD GREEN**: **`✅ Pipeline Healed & Passing`**.

---

### 🧪 Instance 2: Indentation Error in `diagnose.py`
*Simulates an unexpected indentation defect in a core utility module.*

#### Step A: Introduce the Error
Open `diagnose.py` in VS Code, scroll to the bottom, and add this misaligned block (with 2 leading spaces):
```python
  def misaligned_sanitizer():
  pass
```

#### Step B: Commit & Push to GitHub
```powershell
git add diagnose.py
git commit -m "Test: introduce indentation error in diagnose.py"
git push origin main
```

#### Step C: What Happens on Screen (Red Failure State)
1. GitHub Actions runs `python -m py_compile ...` and fails with `IndentationError: unexpected indent`.
2. The dashboard turns **RED**:
   - **Defect Ribbon:** Displays `Defect Location: diagnose.py` | `Category: IndentationError`.
   - **Groq AI RCA:** Explains the unexpected indent at module level and provides the exact indentation correction.

#### Step D: Apply the Fix & Heal the Pipeline
In `diagnose.py`, delete the misaligned block and push:
```powershell
git add diagnose.py
git commit -m "Fix: resolve indentation error to heal pipeline"
git push origin main
```
- GitHub Actions passes with exit code `0`.
- The dashboard automatically flips to **EMERALD GREEN**: **`✅ Pipeline Healed & Passing`**.

---

### 💡 Instant Drag-and-Drop & File Ingestion (Tab 2)
In the dashboard's **"🛠️ Manual Analyzer & File Upload"** tab:
1. **Drag-and-Drop:** Drag any `.log` or `.txt` file onto the dashed drop-zone.
2. The browser automatically parses the file and sends it to the regex sanitizer + Groq engine.
3. In under **2 seconds**, it outputs token reduction %, AI latency in ms, defect location, and formatted fixes with a **Copy Fix** button.

---

### 📊 Research Metrics & Incident History (Tab 3)
In the dashboard's **"📊 Research Metrics & Incident History"** tab:
- **Total CI Runs Analyzed:** Persistent historical count from `incidents.db`.
- **Average Token Reduction:** Empirical metric demonstrating 85–95% token savings.
- **Average Inference Latency:** Groq LPU response time (sub-1.5s).
- **Incident History Table:** Lists past builds with Run #, Failure Category, Defect Location, Latency, and Remediation Links.

---

## 4. Cloud Deployment (Zero-Terminal Experience)

To eliminate running local terminals and ngrok entirely, the project includes cloud-ready deployment assets:

- **`Dockerfile`:** Containerizes the FastAPI app with Python 3.11-slim.
- **`render.yaml`:** 1-click blueprint for [Render](https://render.com) (or Railway / Fly.io).
  - Deploy the backend with environment variables: `GROQ_API_KEY` and `GITHUB_TOKEN`.
  - Point your GitHub webhook to `https://your-service.onrender.com/api/webhook`.

---

## 5. Viva / Evaluator Technical Defense Q&A

### Q1: Why perform regex filtering before passing logs to the LLM?
> **Answer:**  
> Real-world CI logs often exceed 5,000–20,000 lines with routine environmental logs. Passing raw logs wastes API tokens, increases latency, and increases LLM hallucination risk. Our regex filter isolates critical failure signatures (`ERROR`, `FATAL`, `FAIL`, `Exception`), reducing prompt token volume by >85% while retaining full diagnostic fidelity.

### Q2: Why choose Groq and Llama-3.3-70B?
> **Answer:**  
> Groq’s LPU (Language Processing Unit) architecture delivers generation speeds of ~250–300 tokens/sec. For developer experience in CI/CD, getting an actionable diagnosis in under 2 seconds is critical. Furthermore, our code implements automatic fallback models in case the primary endpoint is unavailable.

### Q3: How does the system achieve real-time synchronization?
> **Answer:**  
> The dashboard uses native WebSockets (`/ws/telemetry`) for instantaneous, zero-delay push notifications from FastAPI, paired with automatic reconnection and HTTP polling fallback for maximum reliability.

### Q4: How is data persisted across restarts?
> **Answer:**  
> All pipeline runs, failure classifications, token reduction percentages, and AI latencies are persisted in a local SQLite database (`incidents.db`), allowing historical analytics and MTTR calculation.
