"""
plugins/init — Orchestration plugin
"""
import json
from hermes_cli.plugins import PluginContext
from .init import init_system, generate_daily_learning, handle_checkin
from .data_manager import check_daily_status
from .spaced_repetition import register_all_today_crons, complete_review


def register(ctx: PluginContext) -> None:
    tools = [
        ("init_system", "Init JSON files + generate 60-day learning plan after profile",
         {"target_language": {"type": "string"}, "daily_study_minutes": {"type": "integer"}},
         ["target_language", "daily_study_minutes"]),
        ("generate_daily_learning", "Generate today's learning content (call this when today_content_exists=false)",
         {"day_number": {"type": "integer"}}, ["day_number"]),
        ("check_daily_status", "Check if today's content is already generated (call this first every morning)",
         {}, []),
        ("handle_checkin", "Record evening check-in result",
         {"status": {"type": "string", "enum": ["completed", "unmastered"]},
          "unmastered_content_uids": {"type": "array", "items": {"type": "string"}}},
         ["status"]),
        ("register_today_reviews", "Register today's due spaced repetition reviews with HERMES cron",
         {}, []),
        ("complete_review", "Mark a spaced repetition review as completed",
         {"content_uid": {"type": "string"}}, ["content_uid"]),
    ]
    for name, desc, props, required in tools:
        if name == "check_daily_status":
            h = lambda a: json.dumps(check_daily_status(), ensure_ascii=False)
        else:
            fn = {"init_system": init_system, "generate_daily_learning": generate_daily_learning,
                  "handle_checkin": handle_checkin, "register_today_reviews": lambda a: json.dumps(
                      {"registered": register_all_today_crons()}),
                  "complete_review": lambda a: complete_review(a["content_uid"]) or json.dumps({"ok": True}),
                  }.get(name)
            h = _make_handler(fn, required)
        ctx.register_tool(
            name=name, toolset="hermes-cli", handler=h,
            schema={"type": "function", "function": {
                "name": name, "description": desc,
                "parameters": {"type": "object", "properties": props, "required": required},
            }},
        )


def _make_handler(fn, required):
    def handler(args):
        for k in required:
            if k not in args:
                return json.dumps({"error": f"missing: {k}"})
        return fn(args)
    return handler
