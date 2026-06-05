# Polyglot — AI Language Learning Agent

**学习任何语言，按你的节奏。**  
**Learn any language, at your own pace.**

基于 Hermes Agent v0.11.0 构建的 AI 语言学习智能体，支持任意语种，自动生成每日学习内容并推送。  
An AI-powered language learning agent built on Hermes Agent v0.11.0. Supports any language, automatically generates daily learning content and delivers it to you.

## 核心亮点 / Highlights

- **🌍 任意语种支持 / Any Language** — 不限于主流语言，小语种同样可学。配置目标语言和母语即可  
  Not limited to major languages — minority languages are supported too. Just set your target language and native language.
- **⏱️ 完全自由化学习时间 / Flexible Schedule** — 每日学习时长由你设定，内容量自动适配  
  Set your daily study duration, and the content volume adapts automatically.
- **📊 高频词优先 / High-Frequency First** — 内置知识库按场景高频词编排学习次序，先学最常用的  
  Built-in knowledge base prioritizes high-frequency words by scenario — learn what's most useful first.
- **🧠 遗忘曲线自动复习 / Spaced Repetition** — 基于 Ebbinghaus 遗忘曲线，6 节点自动排期复习，到期推送提醒  
  Based on the Ebbinghaus forgetting curve, with 6 scheduled review points and push reminders.
- **📈 N+1 可理解输入 / Comprehensible Input** — 基于 i+1 理论框架，每日内容难度逐级递进，始终处于舒适区边缘  
  Built on the i+1 framework, daily content gradually increases in difficulty, keeping you at the edge of your comfort zone.

## 工作机制 / How It Works

```
用户设定目标语言 + 每日时间 / Set target language + daily time
        ↓
AI 分析知识库，生成 60 天学习计划 / AI analyzes knowledge base, generates 60-day plan
        ↓
每日自动生成学习内容（8-12 条） / Auto-generate daily content (8-12 items)
        ↓
三段式推送（早/中/晚） / 3-part push (morning/afternoon/evening)
        ↓
晚间打卡 → 提取已掌握词汇 / Evening check-in → extract mastered words
        ↓
遗忘曲线自动排期复习 / Forgetting-curve auto review scheduling
```

## 快速开始 / Quick Start

```bash
# 1. 配置 API Key（推荐 OpenAI）/ Configure API Key (OpenAI recommended)
cp .env.example .env && vim .env

# 2. 选择启动方式 / Choose a launch mode

# 方式 A：Router 模式（轻量 HTTP API，供外部 Router 对接）
# Mode A: Router mode (lightweight HTTP API for external Router integration)
uv run python main.py --server

# 方式 B：Gateway 模式（完整消息路由 + 微信/TG/Discord 推送）
# Mode B: Gateway mode (full message routing + WeChat/TG/Discord push)
uv run python scripts/dev_agent.py

# 方式 C：Gateway + WebUI 控制台
# Mode C: Gateway + WebUI console
uv run python scripts/run_gateway.py
```

## 技术栈 / Tech Stack

- **Hermes Agent v0.11.0** — AI 智能体框架 / AI agent framework
- **OpenAI** — LLM 内容生成 / LLM content generation
- **Plugin + Skill 架构** — 模块化可扩展 / Modular and extensible
- **Cron 调度 + 遗忘曲线算法** — 自动化复习推送 / Automated review push
