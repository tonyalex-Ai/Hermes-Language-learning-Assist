"""
daily_push.py — 3-session daily content delivery via native HERMES cron.

After LLM returns today's learning content, this module:
1. Splits entries into 3 batches (morning / afternoon / evening)
2. Registers 3 one-shot HERMES cron jobs with proper native format
3. Each job fires at its scheduled time → LLM formats & delivers the batch

Also registers the daily pre-generation cron (01:00 recurring) at system init.
"""
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

PUSH_TIMES = ["08:00", "13:00", "18:00"]
SESSION_NAMES = ["morning", "afternoon", "evening"]


def _split_entries(entries: list) -> list[list]:
    """Split entries into 3 batches by round-robin or chunking."""
    n = len(entries)
    if n == 0:
        return [[], [], []]
    if n <= 3:
        # One per session if <= 3
        return [[e] for e in entries] + [[] for _ in range(3 - n)]
    # Chunk into 3 roughly equal parts
    s1 = n // 3
    s2 = n * 2 // 3
    return [entries[:s1], entries[s1:s2], entries[s2:]]


def _build_push_prompt(session_name: str, batch: list[dict]) -> str:
    """Build the prompt for a push cron job.
    The prompt contains the pre-generated content batch;
    the LLM receives it and delivers it to the user with minimal formatting.
    """
    header = (
        f"You are a learning content delivery agent. "
        f"Present the following {session_name} session content "
        f"to the user in a friendly, encouraging tone."
    )
    lines = [header, "", f"## Today's {session_name.title()} Session", ""]
    for i, entry in enumerate(batch, 1):
        word = entry.get("word", "")
        translation = entry.get("translation", "")
        pron = entry.get("pronunciation", {})
        roman = pron.get("romanization", "")
        ipa = pron.get("ipa", "")
        example = entry.get("example_sentence", "")
        ex_trans = entry.get("example_translation", "")
        lines.append(f"{i}. **{word}** - {translation}")
        if roman or ipa:
            lines.append(f"   Pron: [{roman}] ({ipa})" if roman and ipa else f"   Pron: {roman or ipa}")
        if example:
            lines.append(f"   Eg: {example}")
            if ex_trans:
                lines.append(f"   ({ex_trans})")
        lines.append("")
    lines.append("---")
    lines.append("After you have presented the content, tell the user to take their time and practice.")
    return "\n".join(lines)


def _register_native_cron(job_id: str, name: str, prompt: str, run_at: str, deliver: str = "origin"):
    """Register a one-shot cron job using the native HERMES format
    (compatible with cron.jobs.load_jobs / get_due_jobs).

    Reads/writes ~/.hermes/cron/jobs.json with the correct schema:
    {"jobs": [{"id", "name", "prompt", "schedule", "next_run_at", ...}]}
    """
    cron_dir = Path.home() / ".hermes" / "cron"
    cron_file = cron_dir / "jobs.json"
    cron_dir.mkdir(parents=True, exist_ok=True)

    # Load jobs using the native structure
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

    # Dedup by id
    for j in jobs:
        if j.get("id") == job_id:
            return

    schedule = {"kind": "once", "run_at": run_at}
    now_iso = datetime.now(timezone.utc).isoformat()

    jobs.append({
        "id": job_id,
        "name": name,
        "prompt": prompt,
        "schedule": schedule,
        "deliver": deliver,
        "repeat": {"times": 1, "completed": 0},
        "enabled": True,
        "state": "scheduled",
        "created_at": now_iso,
        "next_run_at": run_at,
    })

    # Write in native format
    cron_file.write_text(
        json.dumps({"jobs": jobs, "updated_at": now_iso}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


PREGEN_CRON_ID = "daily_content_pregen"
PREGEN_PROMPT = """Daily learning content pre-generation task (01:00 UTC).

You have access to these tools:
- check_daily_status
- generate_daily_learning(day_number)
- get_progress

Workflow:
1. Call `get_progress`. If current_day >= 60 → course complete, respond with [SILENT]
2. Otherwise, call `check_daily_status`
3. If today_content_exists = false → call `generate_daily_learning(day_number = next_day)`
4. If today_content_exists = true → respond with [SILENT]"""


def _next_run_at_cron(expr: str) -> str:
    """Compute the next execution time for a cron expression (daily 01:00 UTC)."""
    now = datetime.now(timezone.utc)
    target = now.replace(hour=1, minute=0, second=0, microsecond=0)
    if now >= target:
        target += timedelta(days=1)
    return target.isoformat()


def register_pregen_cron():
    """Register a daily recurring cron job at 01:00 to auto-generate
    learning content.  Runs forever (repeat=None).

    Idempotent — uses a fixed job ID so it only registers once.
    """
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
        if j.get("id") == PREGEN_CRON_ID:
            return

    next_run = _next_run_at_cron("0 1 * * *")
    now_iso = datetime.now(timezone.utc).isoformat()

    jobs.append({
        "id": PREGEN_CRON_ID,
        "name": "Daily content pre-generation (01:00)",
        "prompt": PREGEN_PROMPT,
        "schedule": {"kind": "cron", "expr": "0 1 * * *", "display": "0 1 * * *"},
        "deliver": "origin",
        "repeat": {"times": None, "completed": 0},
        "enabled": True,
        "state": "scheduled",
        "created_at": now_iso,
        "next_run_at": next_run,
    })
    cron_file.write_text(
        json.dumps({"jobs": jobs, "updated_at": now_iso}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def schedule_daily_sessions(content_uid: str, entries: list, target_date: str):
    """Split today's LLM output into 3 push sessions and register cron jobs.

    Args:
        content_uid: e.g. "cnt_2026-05-10"
        entries: LLM output entries with uid assigned
        target_date: ISO date string "2026-05-10"
    """
    batches = _split_entries(entries)
    for session_name, time_str, batch in zip(SESSION_NAMES, PUSH_TIMES, batches):
        if not batch:
            continue
        push_at = f"{target_date}T{time_str}:00"
        job_id = f"push_{content_uid}_{session_name}"
        prompt = _build_push_prompt(session_name, batch)
        _register_native_cron(
            job_id=job_id,
            name=f"Daily {session_name} push ({content_uid})",
            prompt=prompt,
            run_at=push_at,
            deliver="origin",
        )
