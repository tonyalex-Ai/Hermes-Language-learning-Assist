# Polyglot — AI Language Learning Agent

**学习任何语言，按你的节奏。**

基于 Hermes Agent v0.11.0 构建的 AI 语言学习智能体，支持任意语种，自动生成每日学习内容并推送。

## 核心亮点

- **🌍 任意语种支持** — 不限于主流语言，小语种同样可学。配置目标语言和母语即可
- **⏱️ 完全自由化学习时间** — 每日学习时长由你设定，内容量自动适配
- **📊 高频词优先** — 内置知识库按场景高频词编排学习次序，先学最常用的
- **🧠 遗忘曲线自动复习** — 基于 Ebbinghaus 遗忘曲线，6 节点自动排期复习，到期推送提醒
- **📈 N+1 可理解输入** — 基于 i+1 理论框架，每日内容难度逐级递进，始终处于舒适区边缘

## 工作机制

```
用户设定目标语言 + 每日时间
        ↓
AI 分析知识库，生成 60 天学习计划
        ↓
每日自动生成学习内容（8-12 条）
        ↓
三段式推送（早/中/晚）
        ↓
晚间打卡 → 提取已掌握词汇
        ↓
遗忘曲线自动排期复习
```

## 快速开始

```bash
# 1. 配置 API Key
cp .env.example .env && vim .env

# 2. 选择启动方式

# 方式 A：Router 模式（轻量 HTTP API，供外部 Router 对接）
uv run python main.py --server

# 方式 B：Gateway 模式（完整消息路由 + 微信/TG/Discord 推送）
uv run python scripts/dev_agent.py

# 方式 C：Gateway + WebUI 控制台
uv run python scripts/run_gateway.py
```

## 技术栈

- **Hermes Agent v0.11.0** — AI 智能体框架
- **DeepSeek / Gemini** — LLM 内容生成
- **Plugin + Skill 架构** — 模块化可扩展
- **Cron 调度 + 遗忘曲线算法** — 自动化复习推送
