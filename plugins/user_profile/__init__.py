"""
User profile plugin — CRUD for profile stored in ~/.hermes/memories/USER.md
"""
import json
import os
from pathlib import Path
from hermes_cli.plugins import PluginContext

MEMORY_DIR = Path.home() / ".hermes" / "memories"
PROFILE_FILE = MEMORY_DIR / "USER.md"


def save_profile(args: dict) -> str:
    dsm = args.get("daily_study_minutes", 120)
    if not isinstance(dsm, int) or dsm < 1:
        return json.dumps({"error": "daily_study_minutes must be a positive integer"}, ensure_ascii=False)
    profile = {
        "name": args.get("name", ""),
        "profession": args.get("profession", ""),
        "industry": args.get("industry", ""),
        "position": args.get("position", ""),
        "daily_study_minutes": dsm,
        "target_language": args.get("target_language", ""),
        "phonetic_standard": args.get("phonetic_standard", "ipa"),
        "romanization_system": args.get("romanization_system", "standard"),
    }
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    content = "# User Profile\n\n```json\n" + json.dumps(profile, ensure_ascii=False, indent=2) + "\n```\n"
    PROFILE_FILE.write_text(content, encoding="utf-8")
    return json.dumps({"ok": True, "path": str(PROFILE_FILE)}, ensure_ascii=False)


def get_profile(args: dict) -> str:
    if not PROFILE_FILE.exists():
        return json.dumps({"exists": False})
    text = PROFILE_FILE.read_text(encoding="utf-8")
    import re
    m = re.search(r"```(?:json)?\s*\n?(\{.*?\})\s*\n?```", text, re.DOTALL)
    if m:
        try:
            return json.dumps({"exists": True, "profile": json.loads(m.group(1))}, ensure_ascii=False)
        except json.JSONDecodeError:
            pass
    return json.dumps({"exists": True, "profile": {"raw": text}}, ensure_ascii=False)


def check_profile(args: dict) -> str:
    exists = PROFILE_FILE.exists()
    return json.dumps({"exists": exists}, ensure_ascii=False)


def register(ctx: PluginContext) -> None:
    for name, handler, desc, params in [
        ("save_profile", save_profile, "Save user profile to USER.md", {
            "name": {"type": "string"}, "profession": {"type": "string"},
            "industry": {"type": "string"}, "position": {"type": "string"},
            "daily_study_minutes": {"type": "integer"},
            "target_language": {"type": "string"},
            "phonetic_standard": {"type": "string"},
            "romanization_system": {"type": "string"},
        }),
        ("get_profile", get_profile, "Get user profile from USER.md", {}),
        ("check_profile", check_profile, "Check if profile exists", {}),
    ]:
        ctx.register_tool(
            name=name, toolset="hermes-cli", handler=handler,
            schema={
                "type": "function",
                "function": {
                    "name": name, "description": desc,
                    "parameters": {"type": "object", "properties": params,
                                   "required": list(params.keys()) if name == "save_profile" else []},
                },
            },
        )
