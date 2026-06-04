"""
Learning log plugin — query daily_learning_log JSON files
"""
import json
from datetime import date, timedelta
from pathlib import Path
from hermes_cli.plugins import PluginContext

DATA_DIR = Path(__file__).parent.parent.parent / "data"


def get_recent_log(args: dict) -> str:
    raw = args.get("days", 3)
    if not isinstance(raw, int) or raw < 0:
        return json.dumps({"error": "days must be a non-negative integer", "logs": []})
    days = raw
    results = []
    for i in range(days):
        d = (date.today() - timedelta(days=i)).isoformat()
        path = DATA_DIR / f"daily_learning_log_{d}.json"
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            results.append(data)
    return json.dumps({"logs": results}, ensure_ascii=False)


def get_log_by_date(args: dict) -> str:
    log_date = args.get("date", date.today().isoformat())
    if not isinstance(log_date, str) or not log_date.strip():
        return json.dumps({"exists": False, "error": "date must be a non-empty string (YYYY-MM-DD)"})
    path = DATA_DIR / f"daily_learning_log_{log_date.strip()}.json"
    if not path.exists():
        return json.dumps({"exists": False})
    data = json.loads(path.read_text(encoding="utf-8"))
    return json.dumps({"exists": True, "log": data}, ensure_ascii=False)


def register(ctx: PluginContext) -> None:
    ctx.register_tool(
        name="get_recent_log", toolset="hermes-cli", handler=get_recent_log,
        schema={
            "type": "function",
            "function": {
                "name": "get_recent_log",
                "description": "Get recent daily learning logs",
                "parameters": {
                    "type": "object",
                    "properties": {"days": {"type": "integer", "description": "Number of recent days"}},
                    "required": [],
                },
            },
        },
    )
    ctx.register_tool(
        name="get_log_by_date", toolset="hermes-cli", handler=get_log_by_date,
        schema={
            "type": "function",
            "function": {
                "name": "get_log_by_date",
                "description": "Get learning log for a specific date",
                "parameters": {
                    "type": "object",
                    "properties": {"date": {"type": "string", "description": "YYYY-MM-DD"}},
                    "required": ["date"],
                },
            },
        },
    )
