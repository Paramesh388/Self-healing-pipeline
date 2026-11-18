"""
diagnose.py - Regex Sanitization, Failure Classification & Groq AI Inference Engine
"""

import os
import re
import sys
import time
import json
from dataclasses import dataclass, field
from typing import List, Dict, Any, Tuple
from dotenv import load_dotenv
from openai import OpenAI, NotFoundError

load_dotenv()

# Regex patterns for error identification and context extraction
LOG_ERROR_PATTERN = re.compile(
    r"(ERROR|FATAL|FAIL|Exception|SyntaxError|IndentationError|TypeError|NameError|AssertionError|ModuleNotFoundError|error TS)",
    re.IGNORECASE,
)

TRANSIENT_PATTERNS = re.compile(
    r"(503 Service Unavailable|502 Bad Gateway|ETIMEDOUT|ECONNRESET|Connection timed out|connection reset by peer|temporary failure in name resolution|rate limit exceeded|runner lost communication)",
    re.IGNORECASE,
)

FILE_LINE_PATTERN = re.compile(
    r'(?:File\s+["\']([^"\']+)["\'],\s+line\s+(\d+))|(?:([a-zA-Z0-9_\-\./\\]+\.(?:py|ts|js|jsx|tsx|java|cpp|go|rs))(?:\:|\()(\d+))'
)

# Configure UTF-8 output encoding for Windows terminals
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


@dataclass
class AppConfig:
    api_key: str = os.getenv("GROQ_API_KEY")
    base_url: str = "https://api.groq.com/openai/v1"
    model_name: str = "llama-3.3-70b-versatile"
    fallback_models: List[str] = field(default_factory=lambda: ["openai/gpt-oss-120b", "qwen/qwen3.8-27b"])
    log_file_path: str = "error.log"


config = AppConfig()


def clean_log_text(raw_text: str) -> str:
    """
    Filters raw log text, isolating error lines along with surrounding traceback/context.
    Reduces token payload by >80% while preserving diagnostic fidelity.
    """
    if not raw_text:
        return ""
    lines = raw_text.splitlines()
    selected = set()
    for index, line in enumerate(lines):
        if LOG_ERROR_PATTERN.search(line):
            # Include preceding lines for stack traces and following lines for the error message
            selected.update(range(max(0, index - 5), min(len(lines), index + 4)))

    if not selected:
        # Fallback to lines matching basic ERROR keywords
        matching = [line.rstrip("\r") for line in lines if LOG_ERROR_PATTERN.search(line)]
        return "\n".join(matching) if matching else raw_text[:2000]

    result = []
    previous = -2
    for index in sorted(selected):
        if index > previous + 1:
            result.append("...")
        result.append(lines[index].rstrip("\r"))
        previous = index
    return "\n".join(result)


def clean_log(log_path: str = None) -> str:
    """Reads a file path and filters out non-critical lines."""
    path = log_path or config.log_file_path
    if not os.path.exists(path):
        raise FileNotFoundError(f"Log file not found at: {path}")

    with open(path, "r", encoding="utf-8", errors="replace") as file:
        return clean_log_text(file.read())


def classify_failure(log_text: str) -> Tuple[str, bool, str, str]:
    """
    Classifies the failure type, detects if it's transient, and extracts the defect file/line.
    Returns: (failure_type: str, is_transient: bool, defect_file: str, defect_line: str)
    """
    is_transient = bool(TRANSIENT_PATTERNS.search(log_text))
    if is_transient:
        return "TransientInfrastructureGlitch", True, "", ""

    # Detect specific error types
    failure_type = "BuildFailure"
    if "SyntaxError" in log_text:
        failure_type = "SyntaxError"
    elif "IndentationError" in log_text:
        failure_type = "IndentationError"
    elif "ModuleNotFoundError" in log_text or "No module named" in log_text:
        failure_type = "ModuleNotFoundError"
    elif "AssertionError" in log_text:
        failure_type = "AssertionFailure"
    elif "error TS" in log_text or "TypeScript" in log_text:
        failure_type = "TypeScriptCompileError"

    # Extract file and line
    defect_file = ""
    defect_line = ""
    match = FILE_LINE_PATTERN.search(log_text)
    if match:
        groups = match.groups()
        defect_file = groups[0] or groups[2] or ""
        defect_line = groups[1] or groups[3] or ""

    return failure_type, False, defect_file, defect_line


def diagnose_structured(cleaned_logs: str, raw_logs: str = "", cfg: AppConfig = config) -> Dict[str, Any]:
    """
    Sends cleaned logs to Groq, measuring inference latency and token savings.
    Returns a comprehensive diagnostic record.
    """
    api_key = cfg.api_key or os.getenv("GROQ_API_KEY")
    if not api_key or api_key.startswith("YOUR_"):
        raise ValueError("Groq API key is missing. Please set GROQ_API_KEY in .env.")

    # Calculate token reduction metrics
    effective_raw = raw_logs if raw_logs.strip() else cleaned_logs
    raw_size_bytes = len(effective_raw.encode("utf-8"))
    sanitized_size_bytes = len(cleaned_logs.encode("utf-8"))
    raw_word_count = len(effective_raw.split())
    sanitized_word_count = len(cleaned_logs.split())
    
    if raw_word_count > 0:
        reduction_pct = round(max(0.0, (1.0 - (sanitized_word_count / raw_word_count)) * 100.0), 1)
    else:
        reduction_pct = 0.0

    # Quick pre-classification
    failure_type, is_transient, defect_file, defect_line = classify_failure(effective_raw)

    client = OpenAI(
        api_key=api_key,
        base_url=cfg.base_url
    )

    system_prompt = (
        "You are an expert autonomous DevOps engineer. Analyze the provided CI/CD error log. "
        "Your task is to identify the defect file and line, pinpoint the exact root cause, and provide a concrete fix. "
        "Format your answer with standard markdown containing:\n"
        "### Root Cause\n<one concise sentence>\n\n"
        "### Defect Location\n<file and line if known>\n\n"
        "### Step-by-Step Fix\n<numbered actionable steps>\n\n"
        "### Suggested Code Fix\n```<language>\n<exact corrected code or patch>\n```"
    )

    user_prompt = (
        f"Filtered CI/CD error log:\n```\n{cleaned_logs}\n```\n"
        f"Pre-detected failure category: {failure_type}. Please provide definitive root cause and remediation."
    )

    models_to_try = [cfg.model_name] + [m for m in cfg.fallback_models if m != cfg.model_name]
    last_error = None
    start_time = time.perf_counter()

    for model in models_to_try:
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.2
            )
            elapsed_ms = round((time.perf_counter() - start_time) * 1000.0, 1)
            raw_response_text = response.choices[0].message.content

            # Post-process response to pull out specific fields if not already detected
            if not defect_file:
                file_match = re.search(r'[`"]([a-zA-Z0-9_\-\./\\]+\.(?:py|ts|js|jsx|tsx|java|cpp))[`"]', raw_response_text)
                if file_match:
                    defect_file = file_match.group(1)

            if not defect_line:
                line_match = re.search(r'line\s+(\d+)', raw_response_text, re.IGNORECASE)
                if line_match:
                    defect_line = line_match.group(1)

            # Extract suggested patch/code block
            patch_match = re.search(r'```(?:python|ts|js|bash|diff)?\n([\s\S]*?)```', raw_response_text)
            suggested_patch = patch_match.group(1).strip() if patch_match else ""

            return {
                "diagnosis": raw_response_text,
                "failure_type": failure_type,
                "is_transient": is_transient,
                "defect_file": defect_file,
                "defect_line": defect_line,
                "suggested_patch": suggested_patch,
                "raw_log_size": raw_size_bytes,
                "sanitized_log_size": sanitized_size_bytes,
                "token_reduction_pct": reduction_pct,
                "inference_latency_ms": elapsed_ms,
                "model_used": model
            }
        except NotFoundError as err:
            last_error = err
            print(f"[Notice] Model '{model}' not found on Groq, attempting fallback...")
            continue

    if last_error:
        raise last_error
    raise RuntimeError("Failed to obtain diagnosis from Groq.")


def diagnose_error(cleaned_logs: str, cfg: AppConfig = config) -> str:
    """Backward-compatible helper returning markdown diagnosis string."""
    result = diagnose_structured(cleaned_logs, cleaned_logs, cfg)
    return result["diagnosis"]


def main():
    print("=" * 60)
    print(" AI-Assisted Build Failure Diagnosis Engine (Groq Llama-3.3-70B)")
    print("=" * 60)

    try:
        filtered_log = clean_log(config.log_file_path)
    except FileNotFoundError as err:
        print(f"[Error] {err}")
        sys.exit(1)

    print(f"\nAnalyzing '{config.log_file_path}'...")
    result = diagnose_structured(filtered_log, filtered_log, config)
    print(f"\n[Latency: {result['inference_latency_ms']}ms | Token Reduction: {result['token_reduction_pct']}%]")
    print(f"[Defect: {result['defect_file'] or 'N/A'}:{result['defect_line'] or 'N/A'} | Type: {result['failure_type']}]")
    print("\n--- Diagnosis ---")
    print(result["diagnosis"])


if __name__ == "__main__":
    main()
