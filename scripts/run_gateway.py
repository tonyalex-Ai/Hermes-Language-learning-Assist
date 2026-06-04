#!/usr/bin/env python3
"""
快速启动 Hermes Gateway（快捷方式）

等效于主菜单选项 1 的 Gateway 部分。
完整欢迎菜单见: uv run python scripts/dev_agent.py
"""

import sys
from pathlib import Path

SITE_PACKAGES = Path(__file__).parent.parent / ".venv/lib/python3.11/site-packages"
sys.path.insert(0, str(SITE_PACKAGES.resolve()))

from hermes_cli.gateway import run_gateway

if __name__ == "__main__":
    run_gateway()
