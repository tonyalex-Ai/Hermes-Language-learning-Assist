# Hermes Agent 开发项目 — opencode 开发规则

本项目基于 Hermes Agent v0.11.0 构建自定义 AI 智能体。

## 目录结构

- `scripts/dev_agent.py` — **统一开发入口**，不要创建其他入口
- `skills/` — 自定义技能（SKILL.md）
- `skills/SKILL_MASTER.md` — 技能索引
- `plugins/` — 自定义插件（plugin.yaml + __init__.py）
- `config/config.yaml` — Hermes 配置模板
- `.env` — API 密钥环境变量
- `docs/hermes-agent-manual.md` — 完整架构配置手册

## 开发约定

1. **入口唯一**：所有开发测试统一从 `scripts/dev_agent.py` 启动
2. **自定义技能**放在 `skills/<name>/SKILL.md`
3. **自定义工具**使用 Plugin 机制放到 `plugins/<name>/`
4. **API Key** 在 `.env` 中配置
5. 全局配置 `~/.hermes/` 由 Hermes 自动管理，不手动修改

## 工具架构编码原则（opencode 必须遵守）

Hermes Agent 采用 **LLM JSON function-calling** 模式，不是 CLI 直连函数调用。

```
LLM 返回 {tool_calls: [{function: {name, arguments: '{...}'}}]}
  → 解析 JSON
  → registry.dispatch(name, args)
  → handler(args) → 返回 JSON string
  → 结果喂回 LLM
```

### 编码铁律

1. **工具即 Schema + Handler** — 写工具 = 定义 OpenAI JSON Schema + 注册纯函数 handler
2. **不解析 CLI 参数** — 所有入参由 LLM 从 schema 理解后以 JSON 传入
3. **不做手动路由** — 不写 if-else 分发，不解析用户自然语言
4. **handler 接收 dict，返回 JSON string** — `args.get("key")` 取值，`json.dumps(...)` 返回
5. **LLM 决定调用时机** — 你只需提供 schema 让 LLM 理解工具能力，不要猜测或限制 LLM 何时调用

### 工具注册规范

```python
registry.register(
    name="my_tool",                     # 工具名（LLM 通过此名调用）
    toolset="hermes-cli",               # 所属工具集
    schema={...},                       # OpenAI JSON Schema
    handler=my_handler,                 # def handler(args: dict) -> str
    check_fn=lambda: True,              # 可用性检查
    is_async=False,                     # 是否异步
)
```

## Git 使用准则

1. **按功能提交**：每个 commit 对应一个完整的功能或修复，不允许用时间戳作为 commit message
2. **提交前检查**：确保代码可运行（`uv sync` 通过）、无语法错误
3. **消息规范**：英文前缀 + 中文简述，如 `feat: 添加微信扫码登录` / `fix: 修复二维码超时重试逻辑`
4. **不提交敏感信息**：`.env`、`*.key`、`credentials.json` 等不得入库
5. **不提交临时文件**：`__pycache__/`、`*.pyc`、`.DS_Store` 等排除在外

## UV 使用准则

1. 所有依赖通过 `uv add <pkg>` 添加，不手动编辑 `pyproject.toml` 的 `dependencies` 段
2. 不使用 `pip install`，统一使用 `uv` 管理虚拟环境
3. 运行脚本用 `uv run python <script>`，确保始终在 .venv 上下文中执行

## 常用命令

```bash
uv run python main.py                  # 启动开发版Agent（欢迎菜单，根目录入口）
uv run python scripts/dev_agent.py     # 同上（scripts 入口，与 main.py 等效）
uv run hermes                          # 启动完整Hermes CLI
uv run hermes gateway                  # 启动网关
```

打包 EXE:
```bash
pip install pyinstaller
pyinstaller --onefile main.py --name hermes-agent
```

## HERMES 原生架构交互规则

**涉及项目功能与 HERMES 原生架构交互时，禁止在根目录直接创建新的 .py 文件来实现功能。**

必须先查看原生 HERMES 架构中已有的交互方式和命名规范（如 `lib/` 目录下的模块结构、约定文件命名等），并使用原生机制进行交互设计：

| 交互类型 | 原生实现方式 | 存放位置 |
|---------|------------|---------|
| **Skill** | 创建 `SKILL.md`，定义 LLM 指令和技能描述 | `skills/<name>/SKILL.md` |
| **Tool** | 使用 Plugin 机制注册，定义 OpenAI JSON Schema + handler | `plugins/<name>/__init__.py` |
| **Memory** | 通过 Hermes 原生 Memory 接口存取 | 查阅 `lib/` 下 Memory 模块 |
| **SQL/DB** | 通过 Hermes 原生 DB 工具或 Plugin 封装 | 查阅 `lib/` 下 DB 模块 |

**核心原则**：先查阅、后编码。在编写任何与 Hermes 交互的代码前，先阅读 Hermes 原生源码（`lib/`、`hermes/` 等目录）理解其已有的交互模式、基类、注册机制和命名约定，再基于这些模式进行扩展，而不是绕过原生架构另起炉灶。
