#!/usr/bin/env python3
"""
Hermes Agent — 统一开发入口

欢迎菜单功能：
  1. 启动 Hermes 后端和 WebUI（Gateway + 网页控制台）
  2. 扫码连接微信（首次登录）
  3. 系统功能
  4. 退出程序

用法：
    uv run python scripts/dev_agent.py

保留 Hermes Agent 完整内部调用链不破坏。
"""

import asyncio
import importlib
import inspect
import os
import subprocess
import sys
import threading
from datetime import datetime
from pathlib import Path

SITE_PACKAGES = Path(__file__).parent.parent / ".venv/lib/python3.11/site-packages"
sys.path.insert(0, str(SITE_PACKAGES.resolve()))

PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR))

PROJECT = "Hermes Agent 开发项目"
VERSION = "0.1.0"
DEV = "Pomelo"

_hermes_home: str = ""

# Plugin subdirectories to load (excluding __pycache__ and example)
_PROJECT_PLUGINS = [
    "init", "user_profile", "learning_log", "learning_plan", "review_scheduler",
]


def _load_project_plugins() -> None:
    """Explicitly load project plugins into Hermes' global plugin manager.

    Hermes' native discovery doesn't scan the project root ``plugins/``
    directory (it looks in bundled, ~/.hermes/plugins/, and ./.hermes/plugins/),
    so we register them manually here.
    """
    from hermes_cli.plugins import (
        PluginContext, PluginManifest, get_plugin_manager,
    )
    manager = get_plugin_manager()
    plugins_dir = PROJECT_DIR / "plugins"

    for name in _PROJECT_PLUGINS:
        plugin_dir = plugins_dir / name
        init_file = plugin_dir / "__init__.py"
        if not init_file.exists():
            continue

        spec = importlib.util.spec_from_file_location(
            f"plugins.{name}", init_file,
            submodule_search_locations=[str(plugin_dir)],
        )
        if spec is None or spec.loader is None:
            continue

        module = importlib.util.module_from_spec(spec)
        sys.modules[f"plugins.{name}"] = module
        spec.loader.exec_module(module)

        register_fn = getattr(module, "register", None)
        if register_fn is None:
            continue

        manifest = PluginManifest(
            name=name, version="0.1.0", source="project",
            path=str(plugin_dir),
        )
        ctx = PluginContext(manifest, manager)
        register_fn(ctx)


def _init() -> None:
    global _hermes_home
    from hermes_constants import get_hermes_home
    _hermes_home = str(get_hermes_home())
    _load_project_plugins()


def _clear() -> None:
    os.system("cls" if os.name == "nt" else "clear")


def _banner() -> None:
    _clear()
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    print("=" * 50)
    print(f"  {PROJECT}")
    print(f"  开发者: {DEV}")
    print(f"  版本:   {VERSION}")
    print(f"  日期:   {now}")
    print("=" * 50)


def _menu() -> None:
    print()
    print("  1. 启动 Hermes 后端和 WebUI")
    print("  2. 扫码连接微信")
    print("  3. 系统功能")
    print("  4. 退出程序")
    print()


# ── 功能 1: 后端 + WebUI ────────────────────────────────

def start_backend() -> None:
    print("\n正在启动 Hermes Gateway 和 WebUI...\n")
    # 设置项目根目录为 TERMINAL_CWD，确保 .hermes.md 被正确加载
    os.environ["TERMINAL_CWD"] = str(Path(__file__).resolve().parent.parent)
    try:
        from hermes_cli.web_server import start_server
        from gateway.run import start_gateway as gw_start

        gw_thread = threading.Thread(
            target=lambda: asyncio.run(gw_start()),
            daemon=True,
        )
        gw_thread.start()
        print("  ✓ Gateway 已启动")
        print("  ✓ 打开 WebUI...")
        start_server(host="127.0.0.1", port=9119, open_browser=True)
    except Exception as e:
        print(f"  ✗ 启动失败: {e}")
    input("\n按 Enter 返回主菜单...")


# ── 功能 2: 扫码连接微信 ──────────────────────────────

def link_wechat() -> None:
    print()
    from gateway.platforms.weixin import qr_login
    result = asyncio.run(qr_login(hermes_home=_hermes_home))
    if result:
        print(f"\n✓ 微信连接成功！account_id: {result['account_id']}")
    else:
        print("\n✗ 微信连接失败或超时")
    input("\n按 Enter 返回主菜单...")


# ── 功能 3: 系统功能 ─────────────────────────────────

def _run_hermes(cmd: str) -> None:
    print(f"\n运行: uv run hermes {cmd}\n")
    subprocess.run(
        [sys.executable, "-m", "hermes_cli.main"] + cmd.split(),
    )
    input("\n按 Enter 继续...")


def system_functions() -> None:
    while True:
        _clear()
        print("── 系统功能 ──")
        print()
        print("  1. hermes status    查看状态")
        print("  2. hermes doctor    运行诊断")
        print("  3. hermes logs      查看日志")
        print("  4. hermes config    配置向导")
        print("  5. 返回主菜单")
        print()
        c = input("请输入 [1-5]: ").strip()
        if c == "1":
            _run_hermes("status")
        elif c == "2":
            _run_hermes("doctor")
        elif c == "3":
            _run_hermes("logs")
        elif c == "4":
            _run_hermes("config wizard")
        elif c == "5":
            break


# ── 主循环 ────────────────────────────────────────────

def main() -> None:
    _init()
    while True:
        _banner()
        _menu()
        c = input("请输入 [1-4]: ").strip()
        if c == "1":
            start_backend()
        elif c == "2":
            link_wechat()
        elif c == "3":
            system_functions()
        elif c == "4":
            print("\n再见！")
            sys.exit(0)


if __name__ == "__main__":
    main()
