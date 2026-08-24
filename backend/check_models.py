"""List Gemini generateContent models available to the single configured API key.

Run from backend:
    python check_models.py
"""

import os
import requests


api_key = os.environ.get("GEMINI_API_KEY", "")
if not api_key and os.path.exists(".env"):
    with open(".env", encoding="utf-8") as f:
        for line in f:
            if line.strip().startswith("gemini_api_key="):
                api_key = line.strip().split("=", 1)[1].strip()
                break

if not api_key:
    raise SystemExit("Set GEMINI_API_KEY or gemini_api_key in .env first.")

resp = requests.get(
    "https://generativelanguage.googleapis.com/v1beta/models",
    params={"key": api_key},
    timeout=15,
)
resp.raise_for_status()

models = resp.json().get("models", [])
for model in models:
    if "generateContent" not in model.get("supportedGenerationMethods", []):
        continue
    print(f"{model.get('name')} | {model.get('displayName', '')}")
