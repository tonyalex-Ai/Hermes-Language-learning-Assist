"""
定制轨道框架生成子Agent v1
画像注入完成后触发，从 HERMES.MD 获取用户画像，
调用 LLM (Gemini 3.1) 生成 60日定制学习计划框架（仅含大纲/方向），
输出目标为 custom_plan.json。

该JSON不包含任何具体词条/对话/例句，仅作为后续LLM生成DAILY LEARNING内容的参考框架。
从第31天起，HERMES调度器参考本框架生成当日定制部分内容。
"""
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

# Insert plugins package into path so we can import the shared LLM client
_PLUGIN_DIR = Path(__file__).parent.parent.parent / "plugins"
if str(_PLUGIN_DIR) not in sys.path:
    sys.path.insert(0, str(_PLUGIN_DIR))
from init.llm_client import call_llm as _call_llm_api

SCRIPT_DIR = Path(__file__).parent.resolve()
OUTPUT_PATH = SCRIPT_DIR / "custom_plan.json"

PROFILE_PATHS = [
    Path.home() / ".hermes" / "memories" / "USER.md",
    Path.home() / ".hermes" / "memories" / "MEMORY.md",
    SCRIPT_DIR.parent.parent / ".hermes.md",
    Path.cwd() / ".hermes.md",
]


def extract_profile(text: str) -> dict:
    """Extract user profile from markdown text."""
    json_match = re.search(
        r'```(?:json)?\s*\n?(\{.*?\})\s*\n?```', text, re.DOTALL
    )
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass

    patterns = {
        "name": r"(?:昵称|name|Name)[：:\s]+(.+)",
        "profession": r"(?:职业|profession|Profession)[：:\s]+(.+)",
        "industry": r"(?:行业|industry|Industry)[：:\s]+(.+)",
        "position": r"(?:岗位|position|Position)[：:\s]+(.+)",
        "target_language": r"(?:学习语言|language|Language)[：:\s]+(.+)",
        "daily_study_minutes": r"(?:学习时间|time)[：:\s]*(\d+)",
    }
    profile = {}
    for key, pattern in patterns.items():
        m = re.search(pattern, text)
        if m:
            profile[key] = m.group(1).strip()
    return profile


def read_profile() -> dict | None:
    """Read user profile from standard paths."""
    for path in PROFILE_PATHS:
        if path.exists():
            text = path.read_text(encoding="utf-8")
            profile = extract_profile(text)
            if profile:
                print(f"Found profile at: {path}", file=sys.stderr)
                return profile
    return None


def build_prompt(profile: dict) -> str:
    """Build LLM prompt. Output-only-json instruction via system prompt."""
    return json.dumps(
        {
            "instruction": (
                "根据用户画像生成60日定制学习计划框架。"
                "只输出JSON，不要任何额外文字和markdown代码块标记。"
            ),
            "user_profile": profile,
            "output_schema": {
                "type": "object",
                "properties": {
                    "meta": {
                        "type": "object",
                        "properties": {
                            "generated_at": {"type": "string", "format": "ISO8601"},
                            "model": {"type": "string", "const": MODEL},
                            "total_days": {"type": "integer", "const": 60},
                            "target_language": {"type": "string"},
                            "user_name": {"type": "string"},
                        },
                        "required": ["generated_at", "model", "total_days", "target_language", "user_name"],
                    },
                    "user_profile": {"type": "object"},
                    "plan_framework": {
                        "type": "object",
                        "properties": {
                            "overall_goal": {
                                "type": "string",
                                "description": "结合用户职业行业岗位的一句话总目标",
                            },
                            "weekly_roadmap": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "week": {"type": "integer"},
                                        "scope": {"type": "string"},
                                        "direction": {"type": "string"},
                                    },
                                    "required": ["week", "scope", "direction"],
                                },
                                "description": "周级别方向规划，共9周覆盖60天",
                            },
                            "custom_scenes": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "与用户岗位直接相关的定制场景列表(6-10个)",
                            },
                            "industry_vocab_topics": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "行业词汇主题分类列表(4-8个)",
                            },
                        },
                        "required": ["overall_goal", "weekly_roadmap", "custom_scenes", "industry_vocab_topics"],
                    },
                },
                "required": ["meta", "user_profile", "plan_framework"],
            },
        },
        ensure_ascii=False,
    )


def call_llm(prompt: str) -> str:
    """Call LLM (DeepSeek / Gemini) via unified client."""
    system_prompt = (
        "你是专业语言学习课程设计师。根据用户画像生成60日定制学习计划框架JSON。"
        "只输出原始JSON，不要任何解释、markdown代码块标记或其他文字。"
    )
    return _call_llm_api(system_prompt, prompt)


def main():
    if not API_KEY:
        print("Error: GEMINI_API_KEY or GOOGLE_API_KEY not set", file=sys.stderr)
        sys.exit(1)

    profile = read_profile()
    if not profile:
        print("Error: No user profile found", file=sys.stderr)
        print(f"Searched: {[str(p) for p in PROFILE_PATHS]}", file=sys.stderr)
        sys.exit(1)

    prompt = build_prompt(profile)
    print("Calling LLM to generate plan framework...", file=sys.stderr)
    raw = call_llm(prompt)

    try:
        framework = json.loads(raw)
    except json.JSONDecodeError:
        json_match = re.search(r"\{.*\}", raw, re.DOTALL)
        if json_match:
            framework = json.loads(json_match.group(0))
        else:
            print(f"Error: LLM output is not valid JSON:\n{raw}", file=sys.stderr)
            sys.exit(1)

    framework["meta"]["generated_at"] = datetime.now(timezone.utc).isoformat()

    OUTPUT_PATH.write_text(
        json.dumps(framework, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"Written: {OUTPUT_PATH}", file=sys.stderr)
    print(json.dumps({"status": "ok", "path": str(OUTPUT_PATH)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
