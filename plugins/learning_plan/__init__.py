"""
Learning plan plugin — query today's plan from daily_learning_content JSON
"""
import json
from datetime import date
from pathlib import Path
from hermes_cli.plugins import PluginContext

DATA_DIR = Path(__file__).parent.parent.parent / "data"


def get_today_plan(args: dict) -> str:
    today = date.today().isoformat()
    path = DATA_DIR / f"daily_learning_content_{today}.json"
    if not path.exists():
        return json.dumps({"exists": False, "note": "今日内容尚未生成"})
    data = json.loads(path.read_text(encoding="utf-8"))
    return json.dumps({"exists": True, "plan": data}, ensure_ascii=False)


def get_plan_by_date(args: dict) -> str:
    log_date = args.get("date", date.today().isoformat())
    path = DATA_DIR / f"daily_learning_content_{log_date}.json"
    if not path.exists():
        return json.dumps({"exists": False})
    data = json.loads(path.read_text(encoding="utf-8"))
    return json.dumps({"exists": True, "plan": data}, ensure_ascii=False)


def register(ctx: PluginContext) -> None:
    ctx.register_tool(
        name="get_today_plan", toolset="hermes-cli", handler=get_today_plan,
        schema={
            "type": "function",
            "function": {
                "name": "get_today_plan",
                "description": "Get today's learning plan from daily_learning_content JSON",
                "parameters": {"type": "object", "properties": {}, "required": []},
            },
        },
    )
    ctx.register_tool(
        name="get_plan_by_date", toolset="hermes-cli", handler=get_plan_by_date,
        schema={
            "type": "function",
            "function": {
                "name": "get_plan_by_date",
                "description": "Get learning plan for a specific date",
                "parameters": {
                    "type": "object",
                    "properties": {"date": {"type": "string", "description": "YYYY-MM-DD"}},
                    "required": ["date"],
                },
            },
        },
    )
