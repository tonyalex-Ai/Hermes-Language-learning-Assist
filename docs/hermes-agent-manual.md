# Hermes Agent v0.11.0 配置与开发手册

## 一、项目根目录结构

```
my-agent-project/
├── .env                    # [编辑] API密钥 / 环境变量
├── AGENTS.md               # [编辑] 项目上下文（Hermes自动加载，也可用 .hermes.md）
├── pyproject.toml           # Python项目定义
├── config/
│   └── config.yaml         # [编辑] Hermes配置模板
├── skills/
│   ├── SKILL_MASTER.md     # [编辑] 技能索引
│   └── my_skill/
│       └── SKILL.md        # [新建] 自定义技能
├── plugins/
│   └── my_plugin/
│       ├── plugin.yaml     # [新建] 插件清单
│       └── __init__.py     # [新建] 插件逻辑
├── scripts/
│   └── dev_agent.py        # [唯一入口] 欢迎菜单
└── docs/
    └── hermes-agent-manual.md
```

## 二、入口点（Entry Points）

Hermes Agent 有**三个**入口，**只用下面第一个**：

| 命令 | 入口文件 | 用途 |
|------|---------|------|
| `uv run python scripts/dev_agent.py` | `scripts/dev_agent.py` | **开发入口**（本项目用这个） |
| `hermes` | `hermes_cli/main.py:main` | 官方CLI（聊天/网关/配置） |
| `hermes-agent` | `run_agent.py:main` | 独立Agent运行器 |
| `hermes-acp` | `acp_adapter/entry:main` | 编辑器集成ACP服务 |

**本项目开发统一入口：`scripts/dev_agent.py`**，内部调用 `AIAgent` 类，保留完整调用链。

## 三、核心架构总览

```
.venv/lib/python3.11/site-packages/
├── hermes_cli/                  # CLI界面 + 配置管理
│   ├── main.py                  # 入口：hermes 命令
│   ├── config.py                # 配置系统（~/.hermes/config.yaml）
│   ├── auth.py                  # OAuth & API Key认证
│   ├── setup.py                 # 交互式安装向导
│   ├── gateway.py               # Gateway启动/停止/状态
│   └── skills_config.py         # 技能配置UI
├── run_agent.py                 # AIAgent类（核心对话循环）
├── model_tools.py               # 工具编排层
├── toolsets.py                  # 工具集定义
├── hermes_constants.py          # 路径/常量
├── hermes_state.py              # SQLite状态管理
├── agent/                       # Agent内核
│   ├── prompt_builder.py        # 系统提示词构建
│   ├── memory_manager.py        # 记忆管理
│   ├── context_engine.py        # 上下文引擎
│   └── skill_commands.py        # 技能命令处理
├── tools/                       # 工具实现（63个文件）
│   ├── registry.py              # 工具注册中心（单例）
│   ├── file_tools.py            # 文件操作工具
│   ├── web_tools.py             # 网络搜索工具
│   ├── terminal_tool.py         # 终端执行工具
│   └── ...
├── gateway/                     # 消息网关
│   ├── config.py                # 网关配置
│   ├── run.py                   # 网关运行器
│   └── platforms/               # 平台适配器（26个）
│       ├── weixin.py            # 微信个人号适配
│       ├── telegram.py          # Telegram
│       ├── discord.py           # Discord
│       └── ...
├── plugins/                     # 插件系统
└── cron/                        # 定时任务
```

## 四、项目上下文文件（宪法/指令）

Hermes **不**使用 `INSTRUCTION.md`。它使用以下文件作为项目级指令（按优先级从高到低）：

| 优先级 | 文件名 | 搜索范围 |
|--------|--------|----------|
| 1（最高） | `.hermes.md` 或 `HERMES.md` | 从 cwd 向上到 git 根目录 |
| 2 | `AGENTS.md` 或 `agents.md` | 仅 cwd |
| 3 | `CLAUDE.md` 或 `claude.md` | 仅 cwd |
| 4 | `.cursorrules` + `.cursor/rules/*.mdc` | 仅 cwd |
| 始终加载 | `~/.hermes/SOUL.md` | Agent 人格（独立加载） |

本项目使用 **`AGENTS.md`** 作为项目上下文文件。你也可以在根目录放一个 `.hermes.md` 获得更高优先级。

## 五、LLM API Key 放哪里

在**项目根目录**的 `.env` 文件中配置：

```env
# === LLM Provider API Keys ===
OPENAI_API_KEY=sk-xxx
ANTHROPIC_API_KEY=sk-ant-xxx

# === 第三方服务 ===
SEARCH_API_KEY=xxx
FIRECRAWL_API_KEY=xxx
EXA_API_KEY=xxx
```

> 微信不需要手动配置 API Key，使用欢迎菜单中的"扫码连接微信"即可自动完成。

### 方式二：全局 `~/.hermes/.env`

```bash
hermes setup          # 交互式设置
hermes config edit    # 编辑配置文件
```

### 方式三：环境变量

直接 export 到 shell 环境。

**加载优先级**：`~/.hermes/.env` > 项目 `.env` > 系统环境变量

## 六、Skill 放哪里

### 全局位置（Hermes默认）

```
~/.hermes/skills/
└── <skill_name>/
    └── SKILL.md
```

`skills/SKILL_MASTER.md` 是技能索引文件，列出所有可用技能。

每个 Skill 是一个包含 `SKILL.md` 的文件夹。内容格式：

```markdown
# Skill: <名称>

## 描述
<技能描述>

## 使用方式
<触发条件说明>

## 指令
<给模型的具体指令>
```

### 项目本地位置（推荐开发用）

```
my-agent-project/skills/
└── my_skill/
    └── SKILL.md
```

> 开发调试时，将 `~/.hermes/skills/` 软链到项目目录：
> ```bash
> ln -sf /path/to/your-project/skills ~/.hermes/skills
> ```
> **注意**：该目录会被 `hermes skills install` 操作影响，建议开发时手动管理。

### 管理命令

```bash
hermes skills list           # 列出所有技能
hermes skills install <name> # 从技能中心安装
hermes skills config         # 交互式启用/禁用
```

## 七、Tool 放哪里

### 内置工具

位于 `.venv/lib/python3.11/site-packages/tools/`。每个工具通过 `registry.register()` 注册。

**如需添加自定义工具**，推荐使用 **Plugin** 机制（见下一节）。

### 工具注册示例

```python
# scripts/my_tool.py
from tools.registry import registry

def my_handler(args) -> str:
    name = args.get("name", "world")
    return json.dumps({"result": f"hello {name}"})

registry.register(
    name="my_custom_tool",
    toolset="hermes-cli",
    schema={
        "type": "function",
        "function": {
            "name": "my_custom_tool",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"}
                }
            }
        }
    },
    handler=my_handler,
    check_fn=lambda: True,
    requires_env=[],
    is_async=False,
)
```

### 工具集（Toolset）配置

在 `~/.hermes/config.yaml` 或 `config/config.yaml` 中：

```yaml
toolsets:
  - "hermes-cli"       # CLI核心工具
  - "web"              # 网络工具
  - "browser"          # 浏览器
  - "file"             # 文件操作
  - "vision"           # 视觉分析

platform_toolsets:
  telegram: ["hermes-telegram", "hermes-cli"]
  weixin: ["hermes-weixin", "hermes-cli"]
```

## 八、Plugin 系统（推荐的自定义方式）

### 目录结构

```
plugins/my_plugin/
├── plugin.yaml
└── __init__.py
```

### plugin.yaml

```yaml
name: my_plugin
version: "0.1.0"
description: "自定义插件"
author: "you"
```

### __init__.py

```python
from plugins import PluginContext

def register(ctx: PluginContext) -> None:
    # 注册工具
    ctx.register_tool(
        name="my_tool",
        handler=my_handler,
        schema={...}
    )
    # 注册钩子
    ctx.register_hook("pre_tool_call", my_hook)
```

### 插件加载顺序

1. 内置插件 `.venv/plugins/`
2. 用户插件 `~/.hermes/plugins/`
3. 项目插件 `./.hermes/plugins/`（需设置环境变量启用）

## 九、~/.hermes/ 目录结构

```
~/.hermes/
├── config.yaml           # [核心] 配置文件
├── .env                  # [核心] API密钥
├── SOUL.md               # Agent人格 / 系统提示词前缀
├── state.db              # SQLite 会话数据库
├── auth.json             # OAuth令牌缓存
├── agent.log             # 运行日志
├── errors.log            # 错误日志
├── gateway.log           # 网关日志
├── skills/               # 技能目录
│   └── <name>/SKILL.md
├── profiles/             # 多配置文件隔离
│   └── <name>/...
├── plugins/              # 用户插件
├── cache/
│   ├── images/
│   └── sessions/
└── workspaces/           # 工作区记录
```

### config.yaml 核心字段

```yaml
model: "gpt-4o"                          # 默认模型
providers: {}                            # 自定义Provider覆盖
fallback_providers: []                   # 降级Provider链
toolsets: ["hermes-cli"]                 # 启用的工具集
agent:
  max_turns: 90                          # 最大对话轮次
  gateway_timeout: 1800                  # 网关超时
  api_max_retries: 3                     # API重试次数
  tool_use_enforcement: "auto"           # 工具使用策略
terminal:
  backend: "local"                       # local|docker|ssh|modal
  cwd: "."                               # 工作目录
  timeout: 180
skills:
  disabled: []                           # 禁用的技能
  platform_disabled: {}                  # 按平台禁用
platform_toolsets: {}                    # 按平台设置工具集
network:
  force_ipv4: false
logging:
  level: "INFO"
  max_size_mb: 5
timezone: "Asia/Shanghai"
```

## 十、WeChat (微信) 连接

### 工作机制

微信基于腾讯 **iLink Bot API**（`https://ilinkai.weixin.qq.com`）。

**首次连接**无需任何手动配置，欢迎菜单中的"扫码连接微信"会自动完成全部流程：

```
dev_agent.py 欢迎菜单 → 扫码连接微信
  └─ gateway.platforms.weixin.qr_login()
       ├─ 向 iLink 请求二维码
       ├─ 在终端打印二维码（ASCII + URL）
       ├─ 轮询扫码状态（等待 → 已扫码 → 确认）
       └─ 自动保存凭证到 ~/.hermes/weixin/accounts/<id>.json
```

### 操作步骤

```bash
# 1. 启动欢迎菜单
uv run python scripts/dev_agent.py

# 2. 选择「2. 扫码连接微信」
# 3. 用微信扫描终端显示的二维码
# 4. 在手机上确认登录
# 5. 连接成功，凭证自动保存，后续无需再扫码
```

> 凭证保存在 `~/.hermes/weixin/accounts/`，后续启动 Gateway 时会自动加载。

### 手动启动 Gateway

```bash
# 启动所有平台
uv run hermes gateway
```

## 十一、开发自定义 Agent（保持调用链完整）

本项目 `scripts/dev_agent.py` 是**统一开发入口**，欢迎菜单 + 功能整合。

```python
# scripts/dev_agent.py (精简示意)
import asyncio, os, sys
from pathlib import Path

SITE_PACKAGES = Path(__file__).parent.parent / ".venv/lib/python3.11/site-packages"
sys.path.insert(0, str(SITE_PACKAGES.resolve()))

def link_wechat():
    """调用 Hermes 内置 QR 登录，用户只需扫码"""
    from gateway.platforms.weixin import qr_login
    from hermes_constants import get_hermes_home
    result = asyncio.run(qr_login(hermes_home=str(get_hermes_home())))
```

> `AIAgent`、`AIAgent.run_conversation()`、工具注册、技能加载等全部保留在 `.venv` 原路径。欢迎菜单只是入口，不破坏任何内部调用链。

## 十二、常见操作速查

```bash
# 启动聊天
hermes

# 单次对话
hermes chat -m "gpt-4o" -p "你好"

# 配置管理
hermes config              # 查看配置
hermes config edit          # 编辑配置
hermes config wizard       # 运行设置向导
hermes config set model gpt-4o

# 模型管理
hermes model list          # 列出可用模型
hermes model switch        # 切换模型

# 工具管理
hermes tools               # 交互式工具配置

# 技能管理
hermes skills list
hermes skills config

# 日志
hermes logs
hermes doctor              # 诊断检查
hermes status              # 状态概览

# Gateway
hermes gateway status
hermes gateway stop

# 配置文件路径
hermes config              # 显示配置文件路径
```

## 十三、开发工作流

```
1. 配置 API Key → 编辑 .env
2. 设置项目上下文 → 编辑 AGENTS.md（或 .hermes.md 获得更高优先级）
3. 添加自定义 Skill → skills/<name>/SKILL.md + 更新 SKILL_MASTER.md
4. 添加自定义 Tool → 用 Plugin 机制 plugins/<name>/
5. 修改配置 → config/config.yaml
6. 运行 → uv run python scripts/dev_agent.py（欢迎菜单）
7. 首次连接微信 → 菜单选「2. 扫码连接微信」
8. 调试 → 查看 ~/.hermes/agent.log
```
