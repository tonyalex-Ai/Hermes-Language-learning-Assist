"""
Data manager — JSON file read/write + UID generation.
Manages 6 core JSON files in data/ directory.
"""
import json
import os
import uuid
from datetime import date, datetime, timezone
from pathlib import Path


DATA_DIR = Path(__file__).parent.parent.parent / "data"

# File paths
PROGRESS_FILE = DATA_DIR / "learning_progress.json"
LEARNING_PLAN_FILE = DATA_DIR / "learning_plan.json"
LEARNED_VOCAB_FILE = DATA_DIR / "learned_vocabulary.json"
REVIEW_SCHEDULE_FILE = DATA_DIR / "review_schedule.json"
USER_PREF_FILE = DATA_DIR / "user_preference.json"

# KB path for plan generation
KB_PATH = Path(__file__).parent.parent.parent / "skills" / "learning_kb" / "knowledge_base.json"


def _ensure_data_dir():
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def _read_json(path: Path, default=None) -> dict:
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return default if default is not None else {}


def _write_json(path: Path, data: dict):
    _ensure_data_dir()
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def generate_uid(prefix: str = "") -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    short = uuid.uuid4().hex[:6]
    return f"{prefix}_{ts}_{short}" if prefix else f"{ts}_{short}"


# ─── 60-Day Learning Plan ──────────────────────────────────────

def generate_schedule_plan():
    """Generate 60-day learning plan: map each day to KB scenario indices.
    Never needs to be read by LLM directly — init.py reads it to determine
    what raw content to extract from KB and pass to LLM each day.
    
    Distribution formula: days 1..N get 2 scenarios, remaining days get 1.
    N = total_scenarios - 60 (clamped to [0, 60]), which yields the correct
    count for any number of scenarios between 60 and 120."""
    kb = _read_json(KB_PATH, {"scenarios": []})
    total_scenarios = len(kb.get("scenarios", []))
    days_with_two = max(0, min(60, total_scenarios - 60))
    plan = []
    idx = 0
    for day in range(1, 61):
        count = 2 if day <= days_with_two else 1
        indices = list(range(idx, min(idx + count, total_scenarios)))
        if not indices:
            break
        ids = [kb["scenarios"][i].get("scenario_id", "") for i in indices]
        plan.append({"day": day, "scenario_indices": indices, "scenario_ids": ids})
        idx += count
        if idx >= total_scenarios:
            break
    data = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_days": 60,
        "total_scenarios": total_scenarios,
        "plan": plan,
    }
    _write_json(LEARNING_PLAN_FILE, data)

def get_day_plan(day_number: int) -> dict | None:
    data = _read_json(LEARNING_PLAN_FILE, {"plan": []})
    for entry in data.get("plan", []):
        if entry["day"] == day_number:
            return entry
    return None

# ─── Learning Progress ─────────────────────────────────────────

def init_progress():
    """Initialize learning_progress.json — simple day counter."""
    progress = {
        "init_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "current_day": 0,
        "phase": "general_only",
    }
    _write_json(PROGRESS_FILE, progress)
    return progress


def get_progress() -> dict:
    return _read_json(PROGRESS_FILE, {
        "current_day": 0, "phase": "general_only",
    })


def save_progress(**kwargs):
    data = get_progress()
    data.update(kwargs)
    data["updated_at"] = datetime.now(timezone.utc).isoformat()
    _write_json(PROGRESS_FILE, data)


def check_daily_status() -> dict:
    """LLM-facing: return today's status so LLM can decide whether to generate content."""
    import os
    today = date.today().isoformat()
    content_path = get_content_path(today)
    log_path = get_log_path(today)
    prog = get_progress()
    current_day = prog.get("current_day", 0)
    return {
        "today": today,
        "current_day": current_day,
        "today_content_exists": content_path.exists(),
        "today_log_exists": log_path.exists(),
        "next_day": current_day + 1,
        "phase": "dual" if (current_day + 1) >= 31 else "general_only",
        "content_file": str(content_path),
        "log_file": str(log_path),
    }


# ─── Daily Learning Content ─────────────────────────────────────

def get_content_path(log_date: str = None) -> Path:
    d = log_date or date.today().isoformat()
    return DATA_DIR / f"daily_learning_content_{d}.json"


def save_daily_content(day: int, phase: str, entries: list, log_date: str = None) -> str:
    d = log_date or date.today().isoformat()
    content_uid = f"cnt_{d}"
    data = {
        "uid": content_uid,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "day": day,
        "phase": phase,
        "entries": entries,
    }
    _write_json(get_content_path(d), data)
    return content_uid


def get_daily_content(log_date: str = None) -> dict:
    return _read_json(get_content_path(log_date), {"entries": []})


# ─── Daily Learning Log ─────────────────────────────────────────

def get_log_path(log_date: str = None) -> Path:
    d = log_date or date.today().isoformat()
    return DATA_DIR / f"daily_learning_log_{d}.json"


def init_daily_log(day: int, log_date: str = None) -> str:
    d = log_date or date.today().isoformat()
    data = {
        "log_date": d,
        "day": day,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "entries": [],
        "checkin": {"status": None, "unmastered_content_uids": []},
    }
    _write_json(get_log_path(d), data)
    return d


def log_push_status(content_uid: str, word: str, session: str,
                    status: str, log_date: str = None):
    d = log_date or date.today().isoformat()
    data = _read_json(get_log_path(d), {"entries": [], "checkin": {}})
    field = f"{session}_push"
    existing = None
    for e in data["entries"]:
        if e["content_uid"] == content_uid:
            existing = e
            break
    if existing:
        existing[field] = status
    else:
        data["entries"].append({
            "content_uid": content_uid,
            "word": word,
            "morning_push": status if session == "morning" else None,
            "afternoon_push": status if session == "afternoon" else None,
            "evening_status": None,
            "tag": None,
        })
    _write_json(get_log_path(d), data)


def _count_consecutive_fails(word: str, current_date: str) -> int:
    """Count how many consecutive days this word has been marked unmastered,
    scanning back up to 5 days.  Returns the count (0 = first fail)."""
    fails = 0
    dt = date.fromisoformat(current_date)
    for _ in range(5):
        dt = dt.__class__.fromordinal(dt.toordinal() - 1)
        prev_data = _read_json(get_log_path(dt.isoformat()), {"entries": []})
        for e in prev_data.get("entries", []):
            if e.get("word") == word and e.get("evening_status") == "unmastered":
                fails += 1
                break
    return fails


def record_checkin(status: str, unmastered_uids: list = None,
                   log_date: str = None):
    d = log_date or date.today().isoformat()
    data = _read_json(get_log_path(d), {"entries": [], "checkin": {}})
    data["checkin"] = {
        "status": status,
        "unmastered_content_uids": unmastered_uids or [],
    }

    # Build word→uid map from today's content for review_fail lookups
    content_data = _read_json(get_content_path(d), {"entries": []})
    uid_to_word = {e.get("uid", ""): e.get("word", "") for e in content_data.get("entries", [])}

    for entry in data["entries"]:
        cuid = entry["content_uid"]
        if cuid in (unmastered_uids or []):
            entry["evening_status"] = "unmastered"
            word = entry.get("word") or uid_to_word.get(cuid, "")
            if word:
                prev_fails = _count_consecutive_fails(word, d)
                if prev_fails > 0:
                    entry["tag"] = f"review_fail_{prev_fails}"
        elif status == "completed":
            entry["evening_status"] = "mastered"
    _write_json(get_log_path(d), data)


def _enrich_entry(entry: dict, from_date: str = None) -> dict:
    """Merge full learning content into a log entry by looking up
    daily_learning_content_*.json via content_uid."""
    cuid = entry.get("content_uid", "")
    if not cuid:
        return entry
    # uid = "cnt_2026-05-10_e000" → extract date by trying uid prefix
    fd = from_date or date.today().isoformat()
    content_data = _read_json(get_content_path(fd), {"entries": []})
    for ce in content_data.get("entries", []):
        if ce.get("uid") == cuid:
            enriched = dict(entry)
            enriched["_full_entry"] = ce
            return enriched
    return entry


def get_unmastered_entries(log_date: str = None) -> list:
    d = log_date or date.today().isoformat()
    data = _read_json(get_log_path(d), {"entries": [], "checkin": {}})
    result = []
    for e in data["entries"]:
        if e.get("evening_status") == "unmastered":
            tag = e.get("tag")
            if tag and tag.startswith("review_fail"):
                e["_consecutive_fails"] = int(tag.split("_")[-1])
            result.append(_enrich_entry(e, d))
    prev = date.today()
    for _ in range(5):
        prev = prev.__class__.fromordinal(prev.toordinal() - 1)
        pd = prev.isoformat()
        pd_data = _read_json(get_log_path(pd), {"entries": []})
        for e in pd_data.get("entries", []):
            if e.get("evening_status") == "unmastered":
                e["_from_date"] = pd
                tag = e.get("tag")
                if tag and tag.startswith("review_fail"):
                    e["_consecutive_fails"] = int(tag.split("_")[-1])
                result.append(_enrich_entry(e, pd))
    return result


# ─── Learned Vocabulary ─────────────────────────────────────────

def get_learned_vocabulary() -> dict:
    return _read_json(LEARNED_VOCAB_FILE, {"words": {}})


def get_learned_word_list() -> list[str]:
    data = get_learned_vocabulary()
    return list(data.get("words", {}).keys())


def add_learned_word(word: str, source_scenario_id: str = ""):
    data = get_learned_vocabulary()
    now = datetime.now(timezone.utc).isoformat()
    if word not in data["words"]:
        data["words"][word] = {
            "mastery_count": 0,
            "first_seen_at": now,
            "last_reviewed_at": now,
            "source_scenario_id": source_scenario_id,
        }
    data["words"][word]["mastery_count"] += 1
    data["words"][word]["last_reviewed_at"] = now
    data["updated_at"] = now
    _write_json(LEARNED_VOCAB_FILE, data)


def extract_learned_from_log(log_date: str = None):
    """Call after checkin: extract mastered words into learned_vocabulary.json."""
    d = log_date or date.today().isoformat()
    log_data = _read_json(get_log_path(d), {"entries": []})
    content_data = _read_json(get_content_path(d), {"entries": []})
    content_map = {}
    for e in content_data.get("entries", []):
        uid = e.get("uid")
        if uid:
            content_map[uid] = e

    for entry in log_data.get("entries", []):
        if entry.get("evening_status") == "mastered":
            cuid = entry.get("content_uid", "")
            ce = content_map.get(cuid, {})
            word = entry.get("word") or ce.get("word", "")
            sid = ce.get("source_scenario_id", "")
            if word:
                add_learned_word(word, sid)


# ─── User Preference ────────────────────────────────────────────

def get_user_preference() -> dict:
    return _read_json(USER_PREF_FILE, {
        "phonetic_standard": "ipa",
        "romanization_system": "standard",
        "native_language": "zh-CN",
    })


def save_user_preference(phonetic_standard: str = "ipa",
                         romanization_system: str = "standard",
                         native_language: str = "zh-CN"):
    data = {
        "phonetic_standard": phonetic_standard,
        "romanization_system": romanization_system,
        "native_language": native_language,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    _write_json(USER_PREF_FILE, data)


# ─── Init All ───────────────────────────────────────────────────

def init_all_files(target_language: str, daily_study_minutes: int):
    """Initialize the entire JSON file system."""
    _ensure_data_dir()
    init_progress()
    if not LEARNED_VOCAB_FILE.exists():
        _write_json(LEARNED_VOCAB_FILE, {"words": {}, "updated_at": datetime.now(timezone.utc).isoformat()})
    if not REVIEW_SCHEDULE_FILE.exists():
        _write_json(REVIEW_SCHEDULE_FILE, {"schedules": [], "updated_at": datetime.now(timezone.utc).isoformat()})
    if not USER_PREF_FILE.exists():
        save_user_preference()
