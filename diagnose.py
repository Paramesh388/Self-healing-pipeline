import os
import re
import sys
import os
from dotenv import load_dotenv

load_dotenv()
from dataclasses import dataclass, field
from typing import List
from openai import OpenAI, NotFoundError

# Configure UTF-8 output encoding for Windows terminals to support rich characters
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# ==============================================================================
# SINGLE CONFIGURATION OBJECT
# ==============================================================================
# All API keys, endpoints, and settings are stored in this single object.
@dataclass
class AppConfig:
    api_key: str =os.getenv("GROQ_API_KEY")
    base_url: str = "https://api.groq.com/openai/v1"
    model_name: str = "llama-3.3-70b-versatile"
    fallback_models: List[str] = field(default_factory=lambda: ["openai/gpt-oss-120b", "qwen/qwen3.8-27b"])
    log_file_path: str = "error.log"

# Global config instance used everywhere
config = AppConfig()


def clean_log(log_path: str = None) -> str:
    """
    Reads the given log file and filters out all lines EXCEPT those
    containing 'ERROR', 'FATAL', 'FAIL', or 'Exception'.
    """
    path = log_path or config.log_file_path
    if not os.path.exists(path):
        raise FileNotFoundError(f"Log file not found at: {path}")

    pattern = re.compile(r"(ERROR|FATAL|FAIL|Exception)")
    matching_lines = []

    with open(path, "r", encoding="utf-8") as file:
        for line in file:
            if pattern.search(line):
                matching_lines.append(line.rstrip("\r\n"))

    return "\n".join(matching_lines)


def diagnose_error(cleaned_logs: str, cfg: AppConfig = config) -> str:
    """
    Sends cleaned log lines to Groq using the OpenAI SDK and returns the diagnosis.
    Tries cfg.model_name and falls back to cfg.fallback_models if the requested model is not found.
    """
    if not cfg.api_key or cfg.api_key.startswith("YOUR_"):
        raise ValueError(
            "Groq API key is missing. Please set config.api_key in diagnose.py "
            "or set the GROQ_API_KEY environment variable."
        )

    client = OpenAI(
        api_key=cfg.api_key,
        base_url=cfg.base_url
    )

    system_prompt = (
        "You are an expert DevOps engineer. Analyze this CI/CD log. "
        "Provide the 'Root Cause' in one sentence, followed by a 'Step-by-Step Fix'."
    )

    user_prompt = f"Filtered CI/CD error log:\n```\n{cleaned_logs}\n```"

    models_to_try = [cfg.model_name] + [m for m in cfg.fallback_models if m != cfg.model_name]
    last_error = None

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
            return response.choices[0].message.content
        except NotFoundError as err:
            last_error = err
            print(f"[Notice] Model '{model}' not available on this Groq endpoint, attempting fallback...")
            continue

    if last_error:
        raise last_error
    raise RuntimeError("Failed to obtain diagnosis from Groq.")


def main():
    print("=" * 60)
    print(" AI-Assisted Build Failure Diagnosis - Phase 1 (Groq)")
    print("=" * 60)

    print(f"\n[1/3] Reading and cleaning '{config.log_file_path}'...")
    try:
        filtered_log = clean_log(config.log_file_path)
    except FileNotFoundError as err:
        print(f"[Error] {err}")
        sys.exit(1)

    if not filtered_log.strip():
        print("[Warning] No matching error lines ('ERROR', 'FATAL', 'FAIL', 'Exception') found.")
        sys.exit(0)

    print("\n--- Filtered Log Lines Sent to AI ---")
    print(filtered_log)
    print("-------------------------------------")

    print(f"\n[2/3] Querying Groq ({config.model_name})...")
    try:
        diagnosis = diagnose_error(filtered_log, config)
    except ValueError as err:
        print(f"\n[Authentication Error] {err}")
        sys.exit(1)
    except Exception as err:
        print(f"\n[API Error] An error occurred while communicating with Groq: {err}")
        sys.exit(1)

    print("\n[3/3] Diagnosis Result:")
    print("=" * 60)
    print(diagnosis.strip())
    print("=" * 60)


if __name__ == "__main__":
    main()
