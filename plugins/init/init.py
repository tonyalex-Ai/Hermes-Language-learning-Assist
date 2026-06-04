"""
init.py — Daily learning orchestrator.
1. After profile collection: generates 60-day LEARNING PLAN (KB index mapping),
   so LLM never needs to read the full knowledge_base.json directly.
2. Each day: reads the pre-generated plan to determine what KB scenarios
   are allocated to today, extracts those from KB, and passes to LLM.
3. Manages evening check-in + learned vocabulary extraction (for future assessment).
"""
import json
import os
import sys
from datetime import date, datetime, timezone
from pathlib import Path

from .data_manager import (
    init_all_files, get_progress, save_progress,
    generate_schedule_plan, get_day_plan,
    save_daily_content, init_daily_log, record_checkin,
    extract_learned_from_log, get_user_preference,
    get_unmastered_entries,
)
from .spaced_repetition import schedule_first_review
from .daily_push import schedule_daily_sessions, PUSH_TIMES, _split_entries as _split_push_batches, register_pregen_cron
from .llm_client import call_llm as _call_llm_api


SKILL_DIR = Path(__file__).parent.parent.parent / "skills" / "learning_kb"
KB_PATH = SKILL_DIR / "knowledge_base.json"
CUSTOM_PLAN_PATH = SKILL_DIR / "custom_plan.json"
MAX_RETRY = 3


LLM_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "entries": {
            "type": "array",
            "description": "今日学习内容条目列表，至少6条，建议8-12条。按场景出现顺序排列。",
            "items": {
                "type": "object",
                "properties": {
                    "word": {"type": "string", "description": "目标语言单词/短语"},
                    "translation": {"type": "string", "description": "用户母语翻译"},
                    "pronunciation": {
                        "type": "object",
                        "properties": {
                            "romanization": {"type": "string"},
                            "ipa": {"type": "string"},
                            "phonics_hint": {"type": "string"},
                        },
                    },
                    "example_sentence": {"type": "string", "description": "目标语言例句"},
                    "example_translation": {"type": "string", "description": "例句的用户母语翻译"},
                    "source_scenario_id": {"type": "string"},
                },
            },
        },
    },
}

EXAMPLE_OUTPUT = json.dumps({
    "entries": [
        {
            "word": "apprendre",
            "translation": "学习",
            "pronunciation": {"romanization": "apʁɑ̃dʁ", "ipa": "/a.pʁɑ̃dʁ/", "phonics_hint": "阿庞德赫"},
            "example_sentence": "J'apprends le français depuis deux ans.",
            "example_translation": "我已经学了两年法语。",
            "source_scenario_id": "intro_01",
        },
    ],
}, ensure_ascii=False, indent=2)

MIN_ENTRIES = 6
TARGET_ENTRIES = 10


def init_system(args: dict) -> str:
    """Called after profile collection.
    1. Init JSON files
    2. Generate 60-day schedule plan (KB index mapping)
    3. Register daily 01:00 pre-generation cron
    """
    target_language = args.get("target_language", "")
    if not isinstance(target_language, str) or not target_language.strip():
        return json.dumps({"error": "target_language is required and must be a non-empty string"})
    dsm = args.get("daily_study_minutes", 120)
    if not isinstance(dsm, int) or dsm < 1:
        return json.dumps({"error": "daily_study_minutes must be a positive integer"})
    daily_study_minutes = dsm
    init_all_files(target_language, daily_study_minutes)
    generate_schedule_plan()
    register_pregen_cron()
    return json.dumps(get_progress(), ensure_ascii=False)


def generate_daily_learning(args: dict) -> str:
    """Main entry: called daily by cron 00:00-06:00.
    Reads the pre-generated LEARNING PLAN to determine today's KB scenarios,
    extracts those from KB, passes to LLM, writes result."""
    day_number = args.get("day_number", 0)
    if not day_number:
        prog = get_progress()
        day_number = prog.get("current_day", 0) + 1

    target_lang = args.get("target_language") or _read_hermes_field("target_language") or ""
    native_lang = args.get("native_language") or _read_hermes_field("native_language") or "zh-CN"
    phase = "dual" if day_number >= 31 else "general_only"
    unmastered = get_unmastered_entries()
    pref = get_user_preference()

    # Read the pre-generated plan to get today's KB scenario indices
    day_plan = get_day_plan(day_number)
    scenario_indices = day_plan.get("scenario_indices", []) if day_plan else []

    raw = _build_raw_content(day_number, scenario_indices, phase, unmastered)
    processed = _call_llm(raw, target_lang, native_lang, pref)
    entries = processed.get("entries", [])
    error = processed.get("_error")

    if error or not entries:
        err_msg = error or "LLM returned empty entries"
        return json.dumps({
            "status": "error",
            "day": day_number,
            "error": err_msg,
        }, ensure_ascii=False)

    # Assign UIDs to entries BEFORE save, so daily_learning_content has them
    today_str = date.today().isoformat()
    content_uid = f"cnt_{today_str}"
    for i, entry in enumerate(entries):
        entry["uid"] = f"{content_uid}_e{i:03d}"

    save_daily_content(day_number, phase, entries, today_str)
    init_daily_log(day_number, today_str)

    # Daily push: split entries into 3 sessions (morning/afternoon/evening)
    # and register HERMES cron jobs for delivery
    schedule_daily_sessions(content_uid, entries, today_str)

    # Schedule forgetting-curve reviews per session, using session push time
    # as the reference timestamp (not generation time)
    _schedule_session_reviews(entries, content_uid, today_str)

    save_progress(current_day=day_number, phase=phase)

    return json.dumps({
        "status": "ok", "day": day_number, "phase": phase,
        "content_uid": content_uid,
        "entry_count": len(entries),
    }, ensure_ascii=False)


def handle_checkin(args: dict) -> str:
    """Record evening check-in result and extract learned vocabulary."""
    status = args.get("status", "completed")
    unmastered_uids = args.get("unmastered_content_uids", [])
    today_str = date.today().isoformat()
    record_checkin(status, unmastered_uids, today_str)
    extract_learned_from_log(today_str)
    return json.dumps({
        "ok": True, "status": status,
        "unmastered_count": len(unmastered_uids),
    }, ensure_ascii=False)


# ─── Private ────────────────────────────────────────────────────

def _calc_target_count(daily_study_minutes: int | None = None) -> int:
    """PRD formula: max(5, daily_study_minutes / 12)."""
    if not daily_study_minutes:
        pref = get_user_preference()
        daily_study_minutes = pref.get("daily_study_minutes", 120)
    return max(5, int(daily_study_minutes / 12))


def _build_raw_content(day: int, scenario_indices: list[int], phase: str,
                       unmastered: list) -> dict:
    """Build raw content from KB using pre-planned scenario indices.
    LLM never sees knowledge_base.json directly — only the extracted snippets."""
    kb = _load_json(KB_PATH, {"scenarios": []})
    scenarios = kb.get("scenarios", [])
    target_count = _calc_target_count()
    payload = {"day": day, "phase": phase, "target_count": target_count}

    general = []
    if unmastered:
        review_items = unmastered[:target_count // 3]
        if review_items:
            general.append({"type": "review_section", "items_to_review": review_items})

    for idx in scenario_indices:
        if idx < len(scenarios):
            sc = scenarios[idx]
            general.append({
                "type": "new_scenario",
                "scenario_id": sc.get("scenario_id", ""),
                "scene": sc.get("master_scene", ""),
                "sub_situation": sc.get("sub_situation", ""),
                "new_vocabulary": sc.get("new_vocabulary", [])[:5],
                "dialogues": sc.get("dialogue", []),
            })
    payload["general_track_raw"] = general

    if phase == "dual":
        custom = _load_json(CUSTOM_PLAN_PATH, {})
        fw = custom.get("plan_framework", {})
        week_idx = min((day - 1) // 7, len(fw.get("weekly_roadmap", [])) - 1)
        week = fw.get("weekly_roadmap", [{}])[week_idx] if week_idx >= 0 else {}
        payload["custom_track_raw"] = {
            "week_direction": week.get("direction", ""),
            "custom_scenes": fw.get("custom_scenes", []),
            "industry_vocab_topics": fw.get("industry_vocab_topics", []),
        }

    return payload


def _build_system_prompt(target_lang: str, native_lang: str, pref: dict) -> str:
    """Build the system instruction for the LLM content generation prompt."""
    schema_text = json.dumps(LLM_OUTPUT_SCHEMA, ensure_ascii=False, indent=2)
    return (
        f"你是语言学习内容制作助手。\n"
        f"你根据今日原始内容制作每日学习资料，输出JSON。\n\n"
        f"语言对: {native_lang} ↔ {target_lang}\n"
        f"原始内容以英文为基底，你翻译并制作成 {native_lang}-{target_lang} 对照的学习资料。\n\n"
        f"发音标注偏好: {pref.get('phonetic_standard', 'ipa')}\n"
        f"罗马音标准: {pref.get('romanization_system', 'standard')}\n\n"
        f"约束:\n"
        f"1. 输出 {MIN_ENTRIES}-{TARGET_ENTRIES} 个条目，覆盖今日所有场景\n"
        f"2. 条目按场景出现顺序排列（不可打乱）— 遇多个场景时按 raw 中的 scene 顺序拼接\n"
        f"3. 为每个 {target_lang} 单词标注罗马音\n"
        f"4. 为每个 {target_lang} 例句中逐词标注罗马音（空格分隔）\n"
        f"5. 翻译为用户母语 {native_lang}\n"
        f"6. 每个 entry 必须包含 word、translation、example_sentence\n\n"
        f"你必须严格按照以下JSON Schema输出，只输出JSON本身，不要任何其他文字:\n"
        f"{schema_text}\n\n"
        f"---\n"
        f"参考示例输出格式:\n{EXAMPLE_OUTPUT}\n---\n"
        f"今日原始内容:\n"
    )


def _call_llm(raw: dict, target_lang: str, native_lang: str, pref: dict) -> dict:
    system = _build_system_prompt(target_lang, native_lang, pref)
    raw_text = json.dumps(raw, ensure_ascii=False)
    last_error = ""

    for attempt in range(MAX_RETRY):
        try:
            prompt = raw_text
            if attempt > 0 and last_error:
                # 兜底追问：把上次错误喂给 LLM，要求纠正
                correction_hint = (
                    f"\n\n--- 兜底纠正要求 ---\n"
                    f"你上一次的返回未能通过校验。\n"
                    f"错误原因: {last_error}\n\n"
                    f"请严格按照以下 JSON Schema 重新输出，确保:\n"
                    f"1. 输出有效JSON（可用 {target_lang} 中的字符）\n"
                    f"2. 包含 {MIN_ENTRIES}-{TARGET_ENTRIES} 个条目\n"
                    f"3. 每个条目必须有 word、translation、example_sentence\n"
                    f"4. 条目按场景顺序排列\n\n"
                    f"参考示例格式:\n{EXAMPLE_OUTPUT}\n\n"
                    f"今日原始内容（同上）:\n"
                )
                prompt = correction_hint + raw_text

            text = _call_llm_api(system, prompt, schema=LLM_OUTPUT_SCHEMA if attempt == 0 else None)
            result = _parse_json(text)

            if result is None:
                last_error = f"JSON解析失败，原始响应: {text[:500]}"
                continue

            entries = result.get("entries", [])
            if not isinstance(entries, list):
                last_error = f"entries 不是数组: {type(entries).__name__}"
                continue

            if len(entries) < MIN_ENTRIES:
                last_error = f"entries 数量不足: 得到 {len(entries)} 条，需要至少 {MIN_ENTRIES} 条"
                continue

            # 验证每个 entry 的必要字段
            missing = []
            for i, e in enumerate(entries):
                if not e.get("word") or not e.get("translation"):
                    missing.append(f"entries[{i}] 缺少 word 或 translation")
            if missing:
                last_error = "; ".join(missing)
                continue

            return result

        except Exception as e:
            last_error = f"{type(e).__name__}: {str(e)[:300]}"
            if attempt == MAX_RETRY - 1:
                break

    # 全部重试失败
    error_msg = f"LLM content generation failed after {MAX_RETRY} attempts. Last error: {last_error}"
    print(error_msg, file=sys.stderr)
    return {"entries": [], "_error": error_msg}





def _parse_json(text: str) -> dict | None:
    import re
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                return None
    return None


def _schedule_session_reviews(entries: list, content_uid: str, target_date: str):
    """Split entries into 3 push sessions and schedule forgetting-curve
    reviews using each session's push time (not generation time) as
    the reference timestamp.

    Uses the same split logic as daily_push._split_entries so that
    push delivery and review scheduling are consistent.
    """
    batches = _split_push_batches(entries)
    for batch, push_time in zip(batches, PUSH_TIMES):
        if not batch:
            continue
        push_at = f"{target_date}T{push_time}:00"
        for entry in batch:
            e_uid = entry.get("uid", "")
            if e_uid:
                schedule_first_review(e_uid, entry, push_at)


def _load_json(path: Path, default=None) -> dict:
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return default or {}


def _read_hermes_field(field: str) -> str | None:
    """Read a field from .hermes.md user profile JSON block."""
    import re
    hermes_path = Path(__file__).parent.parent.parent / ".hermes.md"
    if not hermes_path.exists():
        return None
    text = hermes_path.read_text(encoding="utf-8")
    m = re.search(r"```(?:json)?\s*\n?(\{.*?\})\s*\n?```", text, re.DOTALL)
    if m:
        try:
            profile = json.loads(m.group(1))
            return profile.get(field)
        except json.JSONDecodeError:
            return None
    return None
