#!/usr/bin/env python3
"""
Hermes Agent — 统一启动入口（根目录）
用法:
    uv run python main.py                    # 交互菜单（原有）
    uv run python main.py --server --port 5001  # HTTP 服务模式（新增）
"""
import sys
import json
import asyncio
import threading
import os
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler


def _ensure_path():
    pkg_dir = Path(__file__).parent / ".venv/lib/python3.11/site-packages"
    if pkg_dir.exists():
        sys.path.insert(0, str(pkg_dir.resolve()))


def main():
    _ensure_path()
    # ── 新增: --server 模式（供 ROUTER 对接）──
    if "--server" in sys.argv:
        port = 5001
        for i, arg in enumerate(sys.argv):
            if arg == "--port" and i + 1 < len(sys.argv):
                port = int(sys.argv[i + 1])
        _run_server_mode(port)
        return
    # ── 原有逻辑不变 ──
    from scripts.dev_agent import main as dev_main
    dev_main()


def _run_server_mode(port: int = 5001) -> None:
    """HTTP 服务模式：完整初始化后等待 ROUTER 转发消息"""
    # 1. 加载环境变量
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / ".env")
    # 2. 初始化 Hermes 环境
    from scripts.dev_agent import _init as dev_init
    dev_init()
    # 3. 读取配置
    import yaml
    cfg_path = Path(__file__).parent / "config" / "config.yaml"
    with open(cfg_path) as f:
        cfg = yaml.safe_load(f) or {}
    model = cfg.get("llm", {}).get("openai_model", "gpt-4o")
    provider = cfg.get("llm", {}).get("provider", "openai")
    toolsets = cfg.get("toolsets", ["hermes-cli", "web", "file", "vision"])
    # 4. 启动 Hermes Gateway 后台（加载 skills/plugins）
    print("正在启动 Hermes Gateway（后台）...")
    try:
        from gateway.run import start_gateway as gw_start
        gw_thread = threading.Thread(
            target=lambda: asyncio.run(gw_start()),
            daemon=True,
        )
        gw_thread.start()
        print("  ✓ Gateway 后台运行")
    except Exception as e:
        print(f"  ⚠ Gateway 启动失败: {e}")
    # 5. 创建 AIAgent
    from run_agent import AIAgent
    agent = AIAgent(
        model=model,
        provider=provider,
        enabled_toolsets=toolsets,
        max_iterations=cfg.get("agent", {}).get("max_turns", 90),
        session_id="router_default",
        quiet_mode=True,
    )
    print(f"  ✓ AIAgent 就绪 (模型: {model}, provider: {provider})")
    # 6. HTTP 服务
    class RouterHandler(BaseHTTPRequestHandler):
        def do_POST(self):
            if self.path != "/chat":
                self._json(404, {"error": "not found"})
                return
            try:
                length = int(self.headers.get("content-length", 0))
                body = json.loads(self.rfile.read(length).decode())
                message = body.get("message", "")
                print(f"  → ROUTER 消息: {message[:60]}")
                reply = agent.chat(message)
                print(f"  ← 回复: {reply[:60]}")
                self._json(200, {"reply": reply})
            except Exception as e:
                self._json(500, {"error": str(e)})
        def do_GET(self):
            if self.path == "/health":
                self._json(200, {
                    "agent": "language-learning",
                    "ready": True,
                    "model": model,
                })
            else:
                self._json(404, {"error": "not found"})
        def _json(self, status, data):
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))
    print(f"\nAGENT1 ROUTER 服务启动: http://0.0.0.0:{port}")
    print(f"  POST /chat  接收消息")
    print(f"  GET  /health 健康检查")
    HTTPServer(("0.0.0.0", port), RouterHandler).serve_forever()


if __name__ == "__main__":
    main()
