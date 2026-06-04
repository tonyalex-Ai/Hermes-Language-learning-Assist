"""
Unified LLM client — OpenAI-compatible API (works with OpenAI, DeepSeek, etc.).
Key is read from OPENAI_API_KEY env var. Auto-loads .env from project root.
"""
import json
import os
import sys
from pathlib import Path


_PROJECT_ENV = Path(__file__).resolve().parent.parent.parent / ".env"
if _PROJECT_ENV.exists():
    try:
        from dotenv import load_dotenv
        load_dotenv(dotenv_path=_PROJECT_ENV, override=False)
    except ImportError:
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
    return {
        "api_key": os.getenv("OPENAI_API_KEY") or os.getenv("KEY", ""),
        "base_url": (os.getenv("OPENAI_BASE_URL") or os.getenv("BASE_URL", "https://api.openai.com/v1")).replace(" ", "").rstrip("/"),
        "model": os.getenv("OPENAI_MODEL") or os.getenv("MODEL", "gpt-4o"),
    }


def call_llm(
    system: str,
    prompt: str,
    schema: dict | None = None,
    temperature: float = 0.7,
    max_tokens: int = 8192,
) -> str:
    cfg = _cfg()
    return _call_openai(cfg, system, prompt, temperature, max_tokens)


def _call_openai(
    cfg: dict, system: str, prompt: str,
    temperature: float, max_tokens: int,
) -> str:
    import httpx

    api_key = cfg["api_key"]
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not set")

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
