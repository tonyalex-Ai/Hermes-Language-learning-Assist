"""
Spaced repetition system — review_schedule.json manager.
7 standard Ebbinghaus forgetting curve nodes per content entry.
Interacts with HERMES native CRON (~/.hermes/cron/jobs.json) to register
today's due repetitions.
"""
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .data_manager import _read_json, _write_json, DATA_DIR


REVIEW_SCHEDULE_FILE = DATA_DIR / "review_schedule.json"

# Standard intervals (hours from previous review)
INTERVALS_HOURS = [0, 4, 24, 72, 168, 336, 720]


def _load() -> dict:
    return _read_json(REVIEW_SCHEDULE_FILE, {"schedules": [], "updated_at": ""})


def _save(data: dict):
    data["updated_at"] = datetime.now(timezone.utc).isoformat()
    _write_json(REVIEW_SCHEDULE_FILE, data)


def _build_review_prompt(entry: dict) -> str:
    """Build a review prompt from the full learning entry (word + translation
    + pronunciation + example sentence + translation).  Presents the entire
    piece of content the user originally studied, not a bare word."""
    word = entry.get("word", "")
    translation = entry.get("translation", "")
    pron = entry.get("pronunciation", {})
    roman = pron.get("romanization", "")
    ipa = pron.get("ipa", "")
    example = entry.get("example_sentence", "")
    ex_trans = entry.get("example_translation", "")
    scene = entry.get("source_scenario_id", "")

    lines = [
        "You are a review agent for language learning. "
        "Present the full learning content below to the user for review. "
        "Ask them if they remember the word, its pronunciation, and the example sentence.",
        "",
        f"Word: {word}",
        f"Translation: {translation}",
    ]
    if roman and ipa:
        lines.append(f"Pronunciation: [{roman}] ({ipa})")
    elif roman:
        lines.append(f"Pronunciation: {roman}")
    elif ipa:
        lines.append(f"Pronunciation: {ipa}")
    if example:
        lines.append(f"Example: {example}")
    if ex_trans:
        lines.append(f"Translation: {ex_trans}")
    if scene:
        lines.append(f"(Source: {scene})")
    lines.append("")
    lines.append("Be encouraging and friendly.")
    return "\n".join(lines)


def _register_cron(review_uid: str, push_at: str, entry: dict):
    """Register a one-shot review push job with native HERMES cron format.
    The prompt contains the full learning entry so the chron job delivers
    the complete content (word + translation + pronunciation + example)."""
    cron_dir = Path.home() / ".hermes" / "cron"
    cron_file = cron_dir / "jobs.json"
    cron_dir.mkdir(parents=True, exist_ok=True)

    jobs = []
    if cron_file.exists():
        try:
            raw = json.loads(cron_file.read_text(encoding="utf-8"))
            if isinstance(raw, dict) and "jobs" in raw:
                jobs = raw["jobs"]
            elif isinstance(raw, list):
                jobs = raw
        except (json.JSONDecodeError, OSError):
            pass

    for j in jobs:
        if j.get("id") == review_uid:
            return

    prompt = _build_review_prompt(entry)
    word = entry.get("word", "")
    schedule = {"kind": "once", "run_at": push_at}
    now_iso = datetime.now(timezone.utc).isoformat()

    jobs.append({
        "id": review_uid,
        "name": f"Review: {word or review_uid}",
        "prompt": prompt,
        "schedule": schedule,
        "deliver": "origin",
        "repeat": {"times": 1, "completed": 0},
        "enabled": True,
        "state": "scheduled",
        "created_at": now_iso,
        "next_run_at": push_at,
    })
    cron_file.write_text(
        json.dumps({"jobs": jobs, "updated_at": now_iso}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


# ─── Public API ─────────────────────────────────────────────────

def schedule_first_review(content_uid: str, entry: dict, push_timestamp: str):
    """Create review schedule + register ALL 6 forgetting-curve cron jobs
    at once (nodes 1-6).  The review prompt contains the full learning entry
    (word + translation + pronunciation + example) — same content the user
    originally studied. Never relies on user sign-off to advance."""
    data = _load()
    schedules = data["schedules"]

    for s in schedules:
        if s.get("content_uid") == content_uid:
            return

    future = _compute_future_plan(push_timestamp)  # [T+4h, T+24h, …, T+720h]
    word = entry.get("word", "")
    schedules.append({
        "content_uid": content_uid,
        "word": word,
        "entry": entry,
        "scenario_source": entry.get("source_scenario_id", ""),
        "first_pushed_at": push_timestamp,
        "next_push_at": future[0] if future else push_timestamp,
        "future_push_plan": future,
        "completed_count": 0,
        "remaining_count": len(INTERVALS_HOURS),
        "active": True,
    })
    _save(data)

    # Register ALL 6 future nodes at once — chain runs to completion
    # regardless of user interaction after each push.
    for idx, ts in enumerate(future, start=1):
        if ts:
            _register_cron(f"sr_{content_uid}_{idx}", ts, entry)


def complete_review(content_uid: str):
    """Mark one review node as done (tracking only).
    ALL future crons were already registered by schedule_first_review,
    so this function never registers a new cron."""
    data = _load()
    for s in data["schedules"]:
        if s["content_uid"] == content_uid and s["active"]:
            completed = s["completed_count"] + 1
            s["completed_count"] = completed
            s["remaining_count"] = max(0, len(INTERVALS_HOURS) - completed)

            if completed >= len(INTERVALS_HOURS) or not s.get("future_push_plan"):
                s["active"] = False
                s["next_push_at"] = None
            else:
                next_ts = s["future_push_plan"].pop(0) if s.get("future_push_plan") else None
                s["next_push_at"] = next_ts or s["next_push_at"]
            break
    _save(data)


def get_today_reviews() -> list[dict]:
    """Return all active schedules that have ANY node due today
    (checks both next_push_at and all items in future_push_plan)."""
    data = _load()
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = now.replace(hour=23, minute=59, second=59, microsecond=999999)
    results = []
    for s in data.get("schedules", []):
        if not s.get("active"):
            continue
        candidates = [s.get("next_push_at")] + (s.get("future_push_plan") or [])
        for ts in candidates:
            if not ts:
                continue
            try:
                dt = datetime.fromisoformat(ts)
                if today_start <= dt <= today_end:
                    results.append(s)
                    break
            except (ValueError, TypeError):
                continue
    return results


def get_overdue_reviews() -> list[dict]:
    """Return all active schedules with any node past due
    (checks both next_push_at and all items in future_push_plan)."""
    data = _load()
    now_iso = datetime.now(timezone.utc).isoformat()
    results = []
    for s in data.get("schedules", []):
        if not s.get("active"):
            continue
        candidates = [s.get("next_push_at")] + (s.get("future_push_plan") or [])
        for ts in candidates:
            if ts and ts <= now_iso:
                results.append(s)
                break
    return results


def register_all_today_crons():
    """Batch register ALL remaining forgetting-curve nodes for every active
    schedule.  Used for recovery after ~/.hermes/cron/jobs.json is wiped.
    Each _register_cron call is idempotent (dedup by cron id)."""
    data = _load()
    count = 0
    for s in data.get("schedules", []):
        if not s.get("active"):
            continue
        entry = s.get("entry", {})
        future = s.get("future_push_plan", [])
        completed_base = s.get("completed_count", 0)
        for offset, ts in enumerate(future):
            if not ts:
                continue
            node_idx = completed_base + offset + 1
            _register_cron(f"sr_{s['content_uid']}_{node_idx}", ts, entry)
            count += 1
    return count


# ─── Internal ───────────────────────────────────────────────────

def _compute_future_plan(first_push: str) -> list[str]:
    """Compute all 7 review timestamps from first push."""
    try:
        base = datetime.fromisoformat(first_push)
    except (ValueError, TypeError):
        base = datetime.now(timezone.utc)
    plan = []
    for h in INTERVALS_HOURS[1:]:  # skip 0 (first push itself)
        plan.append((base + timedelta(hours=h)).isoformat())
    return plan
