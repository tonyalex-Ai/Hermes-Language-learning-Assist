"""
Review scheduler plugin — delegates to plugins/init/spaced_repetition.py
Provides: schedule_review, record_review, handle_active_review
"""
import json
import sys
from pathlib import Path
from hermes_cli.plugins import PluginContext

# Import from sibling plugin
INIT_DIR = Path(__file__).parent.parent / "init"
sys.path.insert(0, str(INIT_DIR.parent))

from init.spaced_repetition import (
    schedule_first_review, complete_review,
    get_overdue_reviews, get_today_reviews, register_all_today_crons,
)
from init.data_manager import log_push_status, get_unmastered_entries


def schedule_review(args: dict) -> str:
    content_uid = args.get("content_uid", "")
    word = args.get("word", "")
    push_ts = args.get("push_timestamp", "")
    if not all([content_uid, word]):
        return json.dumps({"error": "missing content_uid or word"})
    entry = {
        "word": word,
        "translation": args.get("translation", ""),
        "pronunciation": args.get("pronunciation", {}),
        "example_sentence": args.get("example_sentence", ""),
        "example_translation": args.get("example_translation", ""),
        "source_scenario_id": args.get("scenario_source", ""),
    }
    schedule_first_review(content_uid, entry, push_ts)
    return json.dumps({"ok": True, "content_uid": content_uid})


def record_review(args: dict) -> str:
    content_uid = args.get("content_uid", "")
    if not content_uid:
        return json.dumps({"error": "missing content_uid"})
    complete_review(content_uid)
    return json.dumps({"ok": True, "content_uid": content_uid})


def handle_active_review(args: dict) -> str:
    overdue = get_overdue_reviews()
    unmastered = get_unmastered_entries()
    today_r = get_today_reviews()
    return json.dumps({
        "overdue_count": len(overdue),
        "unmastered_count": len(unmastered),
        "today_review_count": len(today_r),
        "overdue": overdue[:5],
        "unmastered": unmastered[:5],
    }, ensure_ascii=False)


def register_all(args: dict) -> str:
    count = register_all_today_crons()
    return json.dumps({"registered": count})


def register(ctx: PluginContext) -> None:
    for name, handler, desc, params in [
        ("schedule_review", schedule_review, "Schedule first review for a content entry",
         {"content_uid": {"type": "string"}, "word": {"type": "string"},
          "scenario_source": {"type": "string"}, "push_timestamp": {"type": "string"}}),
        ("record_review", record_review, "Mark a review as completed and schedule next",
         {"content_uid": {"type": "string"}}),
        ("handle_active_review", handle_active_review, "Get overdue + unmastered items for active review",
         {}),
        ("register_today_crons", register_all, "Register all today's due reviews with HERMES cron",
         {}),
    ]:
        ctx.register_tool(
            name=name, toolset="hermes-cli", handler=handler,
            schema={
                "type": "function",
                "function": {
                    "name": name, "description": desc,
                    "parameters": {"type": "object", "properties": params,
                                   "required": list(params.keys()) if name in ("schedule_review", "record_review") else []},
                },
            },
        )
