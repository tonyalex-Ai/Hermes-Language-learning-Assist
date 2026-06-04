"""
Unified LLM client — supports DeepSeek (OpenAI-compatible) and Gemini.
Provider selection via LLM_PROVIDER env var ("deepseek" | "gemini").
Auto-loads .env from project root at import time.
"""
import json
import os
import sys
from pathlib import Path


# Auto-load .env from project root (idempotent)
_PROJECT_ENV = Path(__file__).resolve().parent.parent.parent / ".env"
if _PROJECT_ENV.exists():
    try:
        from dotenv import load_dotenv
        load_dotenv(dotenv_path=_PROJECT_ENV, override=False)
    except ImportError:
        # Fallback: manual parse
        for line in _PROJECT_ENV.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            key = key.strip()
            val = val.strip().strip("\"'")
            if key and not os.getenv(key):
                os.environ[key] = val


def _cfg() -> dict:
    provider = os.getenv("LLM_PROVIDER", "deepseek").lower().strip()
    if provider == "gemini":
        return {
            "provider": "gemini",
            "api_key": os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY", ""),
            "model": os.getenv("GEMINI_MODEL") or os.getenv("LLM_MODEL", "gemini-2.0-flash"),
        }
    return {
        "provider": "deepseek",
        "api_key": os.getenv("DEEPSEEK_API_KEY") or os.getenv("KEY", ""),
        "base_url": (os.getenv("DEEPSEEK_BASE_URL") or os.getenv("BASE_URL", "https://api.deepseek.com")).replace(" ", "").rstrip("/"),
        "model": os.getenv("DEEPSEEK_MODEL") or os.getenv("MODEL", "deepseek-chat"),
    }


def call_llm(
    system: str,
    prompt: str,
    schema: dict | None = None,
    temperature: float = 0.7,
    max_tokens: int = 8192,
) -> str:
    cfg = _cfg()
    if cfg["provider"] == "gemini":
        return _call_gemini(cfg, system, prompt, schema, temperature, max_tokens)
    return _call_openai(cfg, system, prompt, temperature, max_tokens)


def _call_openai(
    cfg: dict, system: str, prompt: str,
    temperature: float, max_tokens: int,
) -> str:
    import httpx

    api_key = cfg["api_key"]
    if not api_key:
        raise RuntimeError("DEEPSEEK_API_KEY not set")

    url = f"{cfg['base_url']}/chat/completions"
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": prompt},
    ]
    body = {
        "model": cfg["model"],
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "response_format": {"type": "json_object"},
    }

    resp = httpx.post(
        url,
        json=body,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        timeout=120,
    )
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"].strip()


def _call_gemini(
    cfg: dict, system: str, prompt: str,
    schema: dict | None, temperature: float, max_tokens: int,
) -> str:
    api_key = cfg["api_key"]
    model = cfg["model"]

    try:
        from google.genai import Client
        client = Client(api_key=api_key)
        gen_config = {
            "system_instruction": system,
            "response_mime_type": "application/json",
            "temperature": temperature,
            "max_output_tokens": max_tokens,
        }
        if schema:
            gen_config["response_schema"] = schema
        resp = client.models.generate_content(
            model=model, contents=prompt, config=gen_config,
        )
        return resp.text.strip()
    except ImportError:
        pass

    import httpx
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    gen_config = {
        "response_mime_type": "application/json",
        "temperature": temperature,
        "maxOutputTokens": max_tokens,
    }
    payload = {
        "system_instruction": {"parts": [{"text": system}]},
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": gen_config,
    }
    resp = httpx.post(url, json=payload, timeout=120)
    resp.raise_for_status()
    return resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
