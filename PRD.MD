# PRD: Language Learning Spoken Agent

> 基于 Hermes Agent v0.11.0 构建的口语学习 AI 智能体

---

## 1. 项目概述 [✓]

### 1.1 背景
用户希望通过 AI 智能体快速学习任意一门语言的口语，需要一套结合遗忘曲线原理的个性化学习系统。

### 1.2 目标
构建一个 HERMES Agent，能够：
- 通过扫码登录并进行用户画像注册
- 根据用户画像（职业、行业、岗位等）生成个性化学习计划
- 基于艾宾浩斯遗忘曲线定时推送复习任务
- 支持多语言口语学习

### 1.3 范围
- **In Scope**: 用户画像注册、学习计划生成、每日定时推送、遗忘曲线复习、主动复习
- **Out of Scope**: 语法深度学习、写作训练、考试备考

---

## 2. 内容架构与词汇里程碑 [✓]

本模块定义了全量知识库的层级划分及用户学习生命周期的阶段性目标。

### 2.1 日常场景频次降序优先级

系统在生成学习计划时，若无特定职业需求，将按以下权重下发场景内容：

1. **P0 (核心基础):** 寒暄社交（打招呼/道别/感谢/致歉）、求助与紧急情况。
2. **P1 (高频生存):** 饮食与消费（点餐/购物/结账）、交通与方位（问路/乘车）。
3. **P2 (日常事务):** 时间/天气/日程、居住与生活琐事（交涉/报修）。
4. **P3 (社交拓展):** 兴趣/娱乐/闲聊（打破社交僵局）。

### 2.2 词汇量学习阶段定义

知识库不应一次性全量加载，需根据词汇量拆分为三个阶段：

* **第一阶段：首次学习（核心 1000 词）**
  * **目标:** 覆盖 70%-80% 生存表达。
  * **策略:** 高强度、高频次的场景词汇灌输，重点确保基础生活场景（P0-P1）的跑通。
* **第二阶段：进阶学习（核心 3000 词）**
  * **目标:** 达到日常流畅沟通（覆盖 90% 表达）。
  * **策略:** 引入连读、时态变化、复杂句式，覆盖 P2-P3 场景。
* **第三阶段：高阶扩展（5000 - 10000 词）**
  * **目标:** 深度讨论、细微情感表达、非结构化语料理解。
  * **策略:** 结合用户画像，引入其所在行业的泛读材料、新闻探讨及深度交互。

---

## 3. 用户画像 [✓]

### 3.1 目标用户
有口语学习需求的职场人士。

### 3.2 使用场景
- 用户首次使用 → 扫码登录 → 画像注册 → 生成学习计划
- 每日定时接收 HERMES 推送的口语学习/复习内容
- 用户可主动发起复习，顺势顺延遗忘曲线排期

### 3.3 用户痛点
- 缺乏个性化学习内容（与职业/行业脱节）
- 学完就忘，没有科学的复习机制
- 难以坚持，缺乏定时提醒

---

## 4. 功能需求 [✓]

### 4.1 核心功能

#### F1: 扫码登录 & 用户画像注册 [✓]
- 用户扫码登录后，HERMES 检查 `~/.hermes/memories/USER.md`（或自定义配置文件）是否已有用户画像
- 如无，按照 `skills/init/SKILL.md`（即 INIT.md 的 HERMES Skill 形态）定义的对话流程逐个收集信息：
  - **职业**（如：公司职员）
  - **行业**（如：热裂解设备制造和再生轮胎产品贸易）
  - **岗位**（如：采购、销售、翻译、对外文书）
  - **昵称**（如：ALEX）
  - **每日可学习时间**（如：2H）
  - **希望学习语言**（如：马来语）
- 额外收集**发音偏好**（如：罗马音标准 / IPA / 母语音译），写入 `user_preference` 表
- 收集完成后注入 HERMES 系统提示词 / 记忆文件

#### F2: 学习计划生成 — 双轨架构 [✓]

**总周期**：通用轨道默认 60 天学完全部 100 场景，每日约 10 句。

本系统采用"通用 + 定制"双轨并行架构：

| 轨道 | 数据源 | 覆盖范围 | 说明 |
|------|-------|---------|------|
| **通用轨道** | `knowledge_base.json`（skills/learning_kb/） | 第1-60天 | 1000 词 × 100 子情境，所有人必学的通用场景内容。60天学完 |
| **定制轨道** | `custom_plan.json`（skills/learning_kb/，由 `generate_custom_plan.py` 输出） | 第31天起生效 | 仅含计划框架（主题/场景大纲），不含具体词汇和对话，供后续LLM生成DAILY LEARNING内容时参考 |

**通用轨道**由 `plugins/init/init.py` 调度，基于 **60 天 LEARNING PLAN**（KB 索引映射表）推进。LLM 无需也不应直接读取 `knowledge_base.json`。

**初始化阶段（画像完成后）**：
- `init_system()` → 生成 `data/learning_plan.json`，将 100 个 KB 场景映射到 60 天
  - 第 1-40 天：每天 2 个场景（覆盖 80 个场景）
  - 第 41-60 天：每天 1 个场景（覆盖剩余 20 个场景）

**逐日推进机制**：
- `generate_daily_learning(day_number)` 读取 `learning_plan.json` 获取今日分配的 `scenario_indices`
- 从 `knowledge_base.json` 中只提取这些索引对应的场景片段 → 传给 LLM
- LLM 仅处理当日片段，不接触完整 KB
- 前一日 `daily_learning_log` 中 `unmastered` 条目在次日首个时段补学
- 遗忘曲线复习任务独立于推进逻辑，由 `plugins/init/spaced_repetition.py` 管理
- 日学习量 ≈ 10 句/日

**每日三段式推送结构**：
| 时段 | 内容 | 说明 |
|------|------|------|
| **上午** (如 08:00) | 学习新内容 | 从当日 `DAILY_LEARNING` 中推送通用轨道新场景 |
| **下午** (如 13:00) | 学习新内容 | 继续推送当日新内容（通用 / 第31天起含定制） |
| **晚上** (如 18:00) | 复习今日内容 + 打卡 | 复习白天所学，学完后要求用户打卡 |

**定制轨道**流程：
- **步骤一（画像后立即执行）**：`skills/learning_kb/generate_custom_plan.py` 从 HERMES.MD 获取画像，调用 LLM 输出 **60日定制计划框架** 至 `custom_plan.json`
  - 该 JSON **仅含**：画像副本 + 周级/主题级大纲，**不含具体词条、对话、例句**
- **步骤二（第31天起每日预生成时执行）**：`plugins/init/init.py` 读取 `custom_plan.json` 中的框架 → 调用 LLM 生成当日**定制部分**具体内容 → 合并到 `DAILY_LEARNING`
- 第1-30天：仅通用轨道运行
- **第31天起**：`plugins/init/init.py` 将两条轨道合并输出

#### F3: 学习内容加工 — init.py 提供原始内容，LLM 加工为学习资料 [✓]

init.py 在每日预生成时执行以下加工流水线：

**输入**：
1. 原始场景内容（从 `learning_plan.json` 获取当日索引 → 从 `knowledge_base.json` 提取对应片段）
2. ~~用户已学词汇表（`learned_vocabulary` 表，排除已掌握词汇避免重复）~~ 已移除：KB 自带 i+1 渐进机制，无需在每日生成时排除；该表保留供未来考核功能使用
3. 用户发音偏好（从 `user_preference` 表读取：罗马音标准 / IPA / 母语音译）
4. 定制轨道框架（第31天起从 `custom_plan.json` 读取）

**LLM 系统提示词设计**：
```
角色：语言学习内容制作助手
任务：基于原始内容制作当日学习资料

用户偏好：
- 目标语言: {target_language}
- 用户母语: {native_language}
- 发音标注偏好: {phonetic_standard}
- 罗马音标准: {romanization_system}

约束：
1. 为每个{目标语言}单词标注罗马音
2. 为每个{目标语言}例句中逐词标注罗马音（空格分隔）
3. 翻译为用户母语 {用户母语}
4. 输出 JSON 必须符合以下 Schema（只输出 JSON，无额外文字）

JSON Schema:
{entries: [{word, translation, pronunciation:{romanization,ipa,phonics_hint}, example_sentence, example_translation, source_scenario_id}]}

[今日原始内容]
{raw_content}
```

**输出**：当日 `DAILY_LEARNING_{timestamp}.JSON`，已加工为带有发音标注和翻译的完整学习资料。

#### F4: 晚间打卡机制 [✓]

每晚学习完成后，系统要求用户打卡确认掌握情况：

- 用户在晚间复习后回复 **"学完"** → 当日所有条目标记 `completed`，记录到 `daily_learning_log`
- 用户回复 **"未学完"**+ 句子序号（如"未学完 3,5,7"）→ 对应条目标记 `unmastered`，写入 `daily_learning_log`
- 打卡结果写入 `daily_learning_log`（字段 `status`, `tag`）

**次日补学机制**：
- 次日推送前，检查前一日所有 `unmastered` 条目
- 次日**首个时段优先推送**昨日未掌握内容（复习补学）
- 补学时段与下一时段之间保持 **30 分钟间隔**
- 补学完成后，再推送当日新内容
- 若补学后仍标记 `unmastered` → 在当日 `daily_learning_log` 中再次打 `review_fail` 标签，次日继续补学
- 同一条目连续 3 次 `review_fail` → 自动降低难度等级（降级到更简单的场景重新学习）

#### F5: 遗忘曲线写入 [✓]

每次 LLM 完成推送后，`plugins/init/spaced_repetition.py` 自动执行：

- 读取当日 `DAILY_LEARNING` 中的全部条目
- 为每个条目创建**第1次复习任务** → 写入 `review_schedule` 表，`scheduled_at` = 当前推送时间戳
- 后续复习节点由遗忘曲线系统独立计算并调度

#### F6: 知识库（knowledge_base.json）[✓]
由两部分构成：
1. **通用高频词/高频用语**：`knowledge_base.json` 提供全量场景覆盖（18主场景×100子情境），默认提供中文版，由初始化工具调用 LLM 翻译为目标语言并注入
2. **行业定制高频词/高频用语**：根据用户的岗位和行业，由 LLM 生成定制化内容

**处理分层**：
- `knowledge_base.json` 提供通用素材池
- `learning_plan.json`（init 时生成）提供 60 天 KB 索引映射
- `generate_custom_plan.py` 输出 `custom_plan.json`（定制框架，仅含大纲）
- `plugins/init/init.py` 读取 `learning_plan.json` → 按当日索引提取 KB 片段 → 合并 `custom_plan.json`（第31天起）→ 调用 LLM → 输出 `daily_learning_content_*.json`

#### F7: 遗忘曲线定时推送 [✓]
- 每日可学习时间（如 2H）按 **6 个时段均分**：早晨起床 / 午休前 / 午休后 / 下班后 / 晚饭后 / 睡觉前
- 通过 HERMES 原生 Cron Scheduler 为每个时段生成推送任务
- 每次推送完成后记录到 `daily_learning_log`
- 艾宾浩斯遗忘曲线由 `plugins/init/spaced_repetition.py` 实现，包含7次标准复习节点（见 6.1）
- **跨夜处理**：若复习任务落在用户睡眠时段（22:00–08:00），自动顺延到次日第一个可用时段

#### F8: 主动复习 [✓]
- 用户通过**自然语言宽松识别**触发（包含"复习/回顾/再看一遍/巩固"等关键词即激活复习流程）
- HERMES 从 `daily_learning_log` 读取最近学习内容并推送
- 主动复习后，顺势顺延下一次遗忘曲线复习节点
- **掌握度标记**：用户可主动告知系统"这个记住了"，系统将该词条的掌握度 +1；连续掌握多次后减少甚至停止该词条的推送

### 4.2 辅助功能
- 学习进度查询
- 学习记录回顾

---

## 5. HERMES 架构设计 [✓]

### 5.1 技能（Skills）规划 [✓]

| 技能名称 | 目录 | 描述 |
|---------|------|------|
| 初始化注册 | `skills/init/SKILL.md` | 用户首次使用的画像收集对话流程（替代 INIT.md） |
| 日常学习 | `skills/daily_learning/SKILL.md` | 每日学习/复习的交互流程 |
| 主动复习 | `skills/active_review/SKILL.md` | 用户主动发起复习的交互流程 |

#### INIT Skill 工作流
`skills/init/SKILL.md` 定义 LLM 引导对话的指令，逐个询问用户：
1. 你的昵称是什么？
2. 你的职业是什么？
3. 你所在行业？
4. 你的岗位/职责？
5. 每天可投入多少时间学习？
6. 想学习什么语言？

每收集一条信息，调用 Plugin Tool 写入持久化存储（`~/.hermes/memories/` 或自定义存储）。

### 5.2 插件（Plugins）规划 [✓]

| 插件名称 | 目录 | 提供工具 | 描述 |
|---------|------|---------|------|
| 初始化编排 | `plugins/init/` | `init.py`, `data_manager.py`, `spaced_repetition.py` | 每日内容预生成 + JSON管理 + 遗忘曲线 |
| 用户画像 | `plugins/user_profile/` | `save_profile`, `get_profile`, `check_profile` | 用户画像的 CRUD |
| 学习计划 | `plugins/learning_plan/` | `generate_plan`, `get_today_plan` | 基于知识库生成/读取学习计划 |
| 复习调度 | `plugins/review_scheduler/` | `schedule_review`, `record_review`, `handle_active_review` | 遗忘曲线复习任务管理 |
| 学习日志 | `plugins/learning_log/` | `log_activity`, `get_recent_log` | 每日学习记录 |

### 5.3 数据存储设计 — JSON文件体系 [✓]

系统采用 **6个核心JSON文件** 替代SQLite，统一存放在 `data/` 目录下。

**文件总览**：

| # | 文件名 | 管理方 | 更新时机 | 用途 |
|---|--------|--------|---------|------|
| 1 | `learning_progress.json` | `init.py` | 每次预生成后 | 累积学习天数 + 当前映射索引 + 已学标记 |
| 2 | `daily_learning_content_YYYYMMDD.json` | `init.py` | LLM返回今日计划时 | 每日LLM生成的学习资料（每条目含UID） |
| 3 | `daily_learning_log_YYYYMMDD.json` | `init.py` | 晚间打卡后 | 每条content/单词的标签（已推送/未推送/已掌握/未掌握） |
| 4 | `learned_vocabulary.json` | `init.py` | 每次log生成后 | 从已掌握单词和句子中提取的词汇库 |
| 5 | `review_schedule.json` | `spaced_repetition.py` | 遗忘曲线计算时 | 7次推送排期（与HERMES原生CRON互动） |
| 6 | `user_preference.json` | `main.py`（首次运行） | 画像收集后 | 发音偏好，注入HERMES.MD后同步至此 |

**文件详细结构**：

---

#### 1. `learning_progress.json`

由 `init.py` 在画像完成后初始化。获取用户画像中的目标语言和每日学习时长后，决定60天内每天推送量，制定进度计划。

```json
{
  "init_at": "ISO8601",
  "updated_at": "ISO8601",
  "target_language": "马来语",
  "daily_study_minutes": 120,
  "total_days": 60,
  "sentences_per_day": 10,
  "current_day": 1,
  "current_scenario_index": 0,
  "learned_scenario_ids": ["001", "002"],
  "phase": "general_only"
}
```

**字段说明**：
- `current_day`: 累计学习天数（1-60）
- `current_scenario_index`: 当前映射到 `knowledge_base.json` 中 `scenarios[]` 的索引
- `learned_scenario_ids`: 已学习标记，记录哪些 scenario 已完成推送
- `sentences_per_day`: 由 `daily_study_minutes` 决定（120分钟→10句/日）
- `phase`: `general_only`（第1-30天）或 `dual`（第31-60天）

---

#### 2. `daily_learning_content_YYYYMMDD.json`

由 `init.py` 管理生成，每次 LLM 返回今日学习计划时写入。每条 content 带 UID 供 `review_schedule` 引用。

```json
{
  "uid": "cnt_20260510",
  "generated_at": "ISO8601",
  "day": 1,
  "phase": "general_only",
  "entries": [
    {
      "uid": "cnt_20260510_e001",
      "index": 0,
      "word": "meeting",
      "translation": "会议",
      "pronunciation": {
        "romanization": "mi-ting",
        "ipa": "/ˈmiːtɪŋ/",
        "phonics_hint": "重音在前，类似中文'米听'"
      },
      "example_sentence": "We have a meeting at 10am.",
      "example_translation": "我们上午十点有个会议。",
      "source_scenario_id": "001",
      "source": "general"
    }
  ]
}
```

---

#### 3. `daily_learning_log_YYYYMMDD.json`

基于当晚学习情况，对每条 content 和单词进行标签记录。

```json
{
  "log_date": "2026-05-10",
  "day": 1,
  "generated_at": "ISO8601",
  "entries": [
    {
      "content_uid": "cnt_20260510_e001",
      "word": "meeting",
      "morning_push": "success",
      "afternoon_push": "success",
      "evening_status": "mastered",
      "tag": null
    }
  ],
  "checkin": {
    "status": "completed",
    "unmastered_content_uids": []
  }
}
```

**status 枚举**：
- 推送状态：`pushed` / `failed`
- 掌握状态：`mastered` / `unmastered`
- 补学标签：`review_fail`（连续补学仍未掌握）

---

#### 4. `learned_vocabulary.json`

由 `init.py` 的 def 管理。每天 `daily_learning_log` 生成后，从已掌握的单词和句子中提取单词写入。

```json
{
  "updated_at": "ISO8601",
  "words": {
    "meeting": {
      "mastery_count": 1,
      "first_seen_at": "ISO8601",
      "last_reviewed_at": "ISO8601",
      "source_scenario_id": "001"
    }
  }
}
```

---

#### 5. `review_schedule.json`

由独立的 `spaced_repetition.py` 负责生成和管理。从 `daily_learning_log` 获取原始学习情况标签，将所有已推送学习的 content 生成7次遗忘曲线推送计划。`spaced_repetition.py` 根据该 JSON 与 HERMES 架构中的原生 CRON 机制注册互动，确定今日需要进行 repetition 的计划。

```json
{
  "updated_at": "ISO8601",
  "schedules": [
    {
      "content_uid": "cnt_20260510_e001",
      "word": "meeting",
      "first_pushed_at": "ISO8601",
      "next_push_at": "ISO8601",
      "future_push_plan": [
        "ISO8601 (+4h)",
        "ISO8601 (+1d)",
        "ISO8601 (+3d)",
        "ISO8601 (+7d)",
        "ISO8601 (+14d)",
        "ISO8601 (+30d)"
      ],
      "completed_count": 1,
      "remaining_count": 6,
      "active": true
    }
  ]
}
```

---

#### 6. `user_preference.json`

首次运行由 `main.py` 调用 LLM 提问收集，注入 HERMES.MD 后抄送给该 JSON 供其他地方调用参考。

```json
{
  "phonetic_standard": "ipa",
  "romanization_system": "standard",
  "native_language": "zh-CN",
  "updated_at": "ISO8601"
}
```

---

**存储选型汇总**：

| 数据类型 | 方案 | 理由 |
|---------|------|------|
| 用户画像 | `~/.hermes/memories/USER.md` + `user_preference.json` | 原生 Memory + JSON偏好 |
| 学习进度 | `data/learning_progress.json` | 结构简单，无需SQL |
| 每日内容 | `data/daily_learning_content_*.json` | 按日存档，LLM可直接引用 |
| 每日日志 | `data/daily_learning_log_*.json` | 按日存档，晚间打卡后生成 |
| 已学词汇 | `data/learned_vocabulary.json` | 字典结构，快速查重 |
| 复习排期 | `data/review_schedule.json` | 数组结构，CRON互动 |
| 知识库 | `skills/learning_kb/knowledge_base.json` | LLM直接读取 |
| Cron 任务 | HERMES 原生 `~/.hermes/cron/jobs.json` | 原生支持 |

### 5.4 配置设计 [✓]

```yaml
# config/config.yaml 扩展
plugins:
  enabled:
    - init
    - user_profile
    - learning_plan
    - review_scheduler
    - learning_log

skills:
  disabled: []
  platform_disabled: {}
```

### 5.5 Agent 交互流程 [✓]

```
用户扫码登录
  → HERMES 启动，加载 skills/init/SKILL.md
  → 检查 user_profile 是否存在
    ├── 不存在 → 按 INIT Skill 流程收集信息
    │             → plugins/init/init.py 触发
  │               ├── 初始化 JSON 文件体系（data/ 目录）
  │               ├── 调用 generate_custom_plan.py → 输出 custom_plan.json
  │               └── 生成第1天通用轨道内容 → DAILY_LEARNING_{timestamp}.JSON
    └── 存在 → 加载 daily_learning Skill
                  → 检查 cron jobs（今日推送是否已完成）
                  → 如未完成，触发推送
                  → 记录到 learning_log
```

### 5.6 定时推送架构 [✓]

利用 HERMES 原生 Cron Scheduler（`cron/scheduler.py` + `cron/jobs.py`）：

- Cron job 存储：`~/.hermes/cron/jobs.json`
- 推送触发：Gateway 每 60s tick 检查到期 job
- **时段分配**：每日按 6 个时段均分学习时间，每个时段一个 cron job
  - 各时段学习量 = 当日总学习量 ÷ 5（用 5 份量覆盖 6 个时段，弹性调度）
  - 时段时间点由用户在画像注册时确认（或默认：起床/午休前/午休后/下班后/晚饭后/睡前）
- **每日内容预生成**：每日首个时段推送前（00:00–06:00 间），`plugins/init/init.py` 被调度器触发，生成当日 `DAILY_LEARNING_{timestamp}.JSON`，该文件缓存供全天 6 个时段共享使用
- **跨夜处理**：复习间隔落在 22:00–08:00 的自动顺延到次日第一个可用时段
- **失败补学**：若某次推送因 LLM 调用失败未完成，在 `daily_learning_log` 标记该条目为 `failed`
  - 每日首个时段推送前（00:00 的 daily_log 总结环节），检查前一日 log 中是否有 `failed` 条目
  - 如有，优先推送失败内容，再推送当日计划内容，后续遗忘曲线排期顺势顺延
- 每次推送完成后，通过 `review_scheduler` 插件创建下一次遗忘曲线复习任务

### 5.7 完整调用链 [✓]

```
初始化（首次登录）
  skills/init/SKILL.md (对话收集)
    → plugins/user_profile/ (保存画像至 HERMES.MD)
    → main.py 收集发音偏好 → user_preference.json (同时注入 HERMES.MD)
    → plugins/init/init.py (触发初始化)
        → data_manager.py 初始化 JSON 文件体系
          ├── learning_progress.json (计算60天每日推送量)
          └── learned_vocabulary.json (空)
        → generate_custom_plan.py → custom_plan.json
        → init.py 构建第1天原始内容
            → 调用 LLM 加工 → daily_learning_content_{day1}.json (带 UID)
            → spaced_repetition.py 写入首次复习排期至 review_schedule.json

每日预生成 (00:00-06:00)
  Cron 触发 → plugins/init/init.py
    → data_manager.py 读取 learning_progress.json
    → 检查前一日 daily_learning_log_{昨日}.json 中 unmastered 条目
    → 按 current_scenario_index 从 knowledge_base.json 提取场景
    → (第31天起) 读取 custom_plan.json 框架
    → 读取 learned_vocabulary.json 构建排除列表
    → 读取 user_preference.json 获取发音偏好参数
    → 构建 LLM prompt → 调用 LLM
    → 输出 daily_learning_content_{今日}.json (每条含 content_uid)
    → spaced_repetition.py: 为新条目写入 review_schedule.json 首次排期
    → spaced_repetition.py: 检查 review_schedule.json 中今日到期的 repetition
      → 注册 HERMES CRON job (~/.hermes/cron/jobs.json)

上午推送 (如 08:00)
  Cron → 推送 general_track 内容
    → 记录 → daily_learning_log_{今日}.json (morning_push=success/failed)

下午推送 (如 13:00)
  Cron → 推送剩余内容（含 custom_track）
    → 记录 → daily_learning_log_{今日}.json (afternoon_push=success/failed)

晚间复习 + 打卡 (如 18:00)
  Cron → 推送当日已学内容复习
    → 提示用户打卡："学完" / "未学完 + content_uid 列表"
    → 用户回复 → init.py 更新 daily_learning_log_{今日}.json
      ├── evening_status = mastered / unmastered
      └── checkin 字段记录
    → init.py: 从 mastered 条目提取单词 → 写入 learned_vocabulary.json
    → spaced_repetition.py: 更新 review_schedule.json 完成计数

次日补学
  每日预生成时:
    → data_manager.py 读取昨日 daily_learning_log 中 unmastered 条目
    → 首个时段推送补学 (30min gap)
    → 补学后 user 仍标记 unmastered → tag=review_fail
    → 连续3次 → 自动降级
```

### 5.8 核心交互范式：任务驱动型沉浸式 RPG [✓]

**核心定位:** 从"静态翻译/刷题库"全面升级为"任务驱动型沉浸式 RPG"（Task-based NPC Roleplay）。

* **摒弃传统题型:** 不做"请翻译这句话"、"填空题"。
* **动态任务下发（Daily Quests）:** 每日学习内容生成当天的"通关条件"。
  * *示例设定:* "你的设定是刚下飞机的游客，你的行李丢了。"
  * *Agent 角色:* "机场行李部略显疲惫的工作人员。"
  * *通关条件:* "向工作人员描述你的行李特征，并成功留下联系方式（交互轮次控制在 3-5 轮）。"
* **隐性纠错（Recast）:** Agent 在交互中不生硬打断用户的语法错误，而是通过**重铸**来示范（用户："I losted my bag." -> Agent："Oh, you **lost** your bag? What color is it?"），保持对话心流。

---

## 6. 艾宾浩斯遗忘曲线系统设计 [✓]

### 6.1 复习间隔设计

基于标准艾宾浩斯遗忘曲线原则，每次新学内容设置以下复习节点：

| 复习次数 | 间隔时间 | 说明 |
|---------|---------|------|
| 第1次 | 学习完成后立即 | 首次学习 |
| 第2次 | 4小时后 | 短期记忆巩固 |
| 第3次 | 24小时后（1天） | 日回顾 |
| 第4次 | 72小时后（3天） | 中期巩固 |
| 第5次 | 168小时后（7天） | 周回顾 |
| 第6次 | 336小时后（14天） | 双周巩固 |
| 第7次 | 720小时后（30天） | 月度终检 |

> 此为基准设计，具体次数和间隔根据用户每日可学习时间动态调整。
> **跨夜处理**：若某次复习的计算时间落在 22:00–08:00 之间，自动顺延到次日第一个可用时段执行。

### 6.2 主动复习逻辑

- 用户通过**自然语言宽松识别**触发复习（包含"复习/回顾/再看一遍/巩固"等关键词即激活）
- 触发后，读取最近未到期的复习项（优先推送 overdue 项）
- 推送完成后，将该复习项的下一次计划时间顺势顺延（即：如果今天主动复习了本该 3 天后复习的内容，则下一次复习从今天重新计算间隔）
- **掌握度标记**：用户可主动告知"这个记住了"或"这个我会了"，系统将该词条掌握度 +1
  - 掌握度累计达到阈值（如连续正确 3 次）后，该词条不再进入主动复习和定时推送
  - 掌握度数据存储在 `learning_log` 或独立的 `mastery` 表中

### 6.3 调度执行

由 `plugins/review_scheduler/` 插件实现，核心逻辑：
1. 用户在 `daily_learning_plan` 中有新学内容 → 创建第1次学习任务（立即）
2. 第1次完成后 → 创建第2次（4H后）... 以此类推
3. 每日基于用户可学习时间按 **6 时段均分**原则分配推送（`user_profile.daily_study_time / 5` = 每时段可用量）
4. 每次推送结果写入 `learning_log`（状态：`pushed` / `completed` / `skipped` / `failed`）
5. **失败补学机制**：
   - 推送失败（`failed`）的条目保留在 log 中，标记失败原因
   - 每日首个推送时段前（00:00 的 daily_log 总结环节）检查前一日 `failed` 条目
   - 存在失败条目时，优先补学，再推当日新内容，后续遗忘曲线排期顺势顺延
6. **掌握度检查**：每次推送前检查词条是否已达到掌握度阈值，如已掌握则跳过

---

## 7. 高阶教学理论拓展：Krashen "i+1" 理论深度应用 [✓]

**前提:** 艾宾浩斯遗忘曲线（SRS）已在复习系统中独立实现（见第 6 章），本模块专注于**初次输入阶段**的质量控制。

### 7.1 Krashen "i+1" 理论简介

* **i (Input):** 用户当前已完全掌握的语言能力（基于系统的词汇追踪）。
* **+1:** 略微超出当前水平的新知识点。
* **核心原则:** 必须提供"可理解的输入"（Comprehensible Input），即材料必须有 90% 以上是用户能懂的，系统不应提供难度过高的材料，那会变成噪音。

### 7.2 系统级落地逻辑

为了在 Agent 架构中实现 i+1，系统需要建立**严格的词汇水位线监控**：

1. **"i" 的基准测算（画像阶段）:**
   * 系统需维护一个动态更新的 `user_known_vocabulary.json` 库。
   * 画像阶段需评估用户的初始池（是在 1000 词内，还是 3000 词内）。
2. **"+1" 的动态生成约束（LLM Prompt Engineering）:**
   * 每天在生成每日学习内容的语料或对话 NPC 的初始 Prompt 时，必须传入参数：`{"must_use_words": ["新词1", "新词2"], "allowed_complexity": "A2"}`。
   * **硬性约束 Prompt:** "你生成的对话剧本和阅读材料中，90% 的词汇必须属于用户已知的 [A2/1000词] 级别，每天只能自然融入不超过 10% 的生词。"
3. **"+1" 的上下文推断设计:**
   * 落实 Krashen 理论的关键在于"不用查字典也能猜出意思"。
   * 要求 Agent 在抛出带新词（+1）的句子时，必须在上下文中提供充足的线索。例如学习新词 `umbrella`，Agent 不应单单说 "Here is an umbrella."，而应生成提示词："It's raining heavily outside, you should take this **umbrella**." 让用户通过 `raining` 猜出 `umbrella` 的意思，完成自然习得。

---

## 8. 关键文件定义 [✓]

### 8.1 HERMES.MD（系统提示词核心文件 / Agent 最高宪法）

**存放位置**：项目根目录 `.hermes.md`

**内容**：包含用户画像 JSON（含 target_language 和 native_language）、LLM 三大职责定义、每日学习内容 JSON Schema。

**LLM 三大职责（HERMES.MD 明确定义）**：
1. **生成每日学习内容** — 根据 knowledge_base.json 原始内容 + 语言对，制作格式固定的学习资料 JSON
2. **晚间沟通学习情况** — 打卡交互后调用 `init.handle_checkin` 记录
3. **回答用户学习/翻译问题** — 纯问答，不操作文件/CRON

> 注：所有定时推送、日志记录、遗忘曲线计算、CRON 注册均由代码自动执行，LLM 不参与。

### 8.2 knowledge_base.json（全量知识库）

**存放位置**：`skills/learning_kb/knowledge_base.json`

**生成脚本**：`skills/learning_kb/generate_kb.py`

**结构**：18 主场景 × 100 子情境 × 1000 词矩阵覆盖，详见 knowledge_base.json 文件。

**本地化策略：** 为避免全量知识库过于庞杂，系统采用"标准内核 + 动态插件"的生成策略。

* **知识库存储：** 仅存储目标语言的**标准通用版本**（如通用英语、标准普通话），作为底层字典。
* **动态 Prompt 注入：**
  * 在画像阶段解析时提取目标地区（如 `"target_region": "Australia"`）。
  * 在生成每日学习内容时，System Prompt 内置规则：*"请将本次对话/学习内容中 10% 的标准表达，自动替换为 [目标地区] 的常用俚语或本土表达，并在解析中注明。"*
* **优势：** 零维护成本实现全球化方言覆盖，利用 LLM 的预训练语料库动态生成。

### 8.3 JSON 文件体系说明

所有持久化数据以 JSON 文件形式存放在 `data/` 目录，由 `plugins/init/data_manager.py` 统一管理。

详见 5.3 章节的完整结构定义，共6个核心 JSON 文件：
- `learning_progress.json` — 学习进度
- `daily_learning_content_*.json` — 每日 LLM 生成内容
- `daily_learning_log_*.json` — 每日学习标签日志
- `learned_vocabulary.json` — 已学词汇库
- `review_schedule.json` — 遗忘曲线排期
- `user_preference.json` — 用户发音偏好

### 8.6 custom_plan.json（定制计划框架）

**存放位置**：`skills/learning_kb/custom_plan.json`

**输出文件**（由 `skills/learning_kb/generate_custom_plan.py` 输出）：

**性质**：仅含**框架/大纲**，不含任何具体词条、对话、例句。

**用途**：
- 第1-30天：不使用
- 第31-60天：`plugins/init/init.py` 读取 `plan_framework` 中的 `weekly_roadmap`、`custom_scenes`、`industry_vocab_topics` 作为 Prompt 上下文，调用 LLM 生成当日定制部分内容

### 8.7 daily_learning_content_{YYYYMMDD}.json（当日完整学习内容）

**生成路径**：`data/daily_learning_content_{YYYYMMDD}.json`

**生成时机**：每日预生成时段（00:00-06:00）由 `plugins/init/init.py` 调用 LLM 生成。

**性质**：含当日全部学习条目（通用部分 + 定制部分）的具体词条、对话、例句，是推送的最终数据源。每条 entry 带 `uid` 供 `review_schedule` 引用。

**每日条目数**：由 `user_profile.daily_study_minutes` 决定，弹性伸缩。

**结构**：详见 5.3 章节 JSON 文件体系第 2 项定义。

**数量弹性说明**：
- 日学习条目数 = max(5, daily_study_minutes ÷ 12)
- 默认 120 分钟 → 10 句/日
- 复习条目由 `spaced_repetition.py` 单独管理，不占用当日新学配额

### 8.8 发音与音标展示方案（受限环境适配）

**已知约束：** 微信 Gateway 暂不支持语音消息下发，无法使用 TTS API 产生音频交互。

**解决方案：** 纯文本维度的发音辅助矩阵。在生成的每日学习内容中，每个核心例句/生词必须包含以下三层标注：

1. **通用罗马音/拼音（Romanization）：** 作为最基础的认读抓手，确保用户在无音频环境下的最低限度"可拼读性"。
2. **国际音标（IPA）：** 作为严谨的学术兜底，供对发音有追求的用户进行校准。
3. **LLM 描述性发音指导（Descriptive Phonics）：** 利用 LLM 生成生动的中文化发音指导（例如："这个词的 R 音不需要弹舌，发音类似中文的'日'但舌头更靠后"）。

---

## 9. 非功能需求 [✓]

### 9.1 性能
- 定时推送延迟不超过 60s（基于 HERMES Cron tick 周期）
- LLM 翻译/生成应在合理时间内完成（可异步处理）

### 9.2 可靠性
- LLM API 调用失败时：自动重试 3 次，间隔递增（1s / 5s / 15s）
- 重试仍失败时：在 `daily_learning_log` 中标记该条目为 `failed`，记录原因
- 每日首个推送时段前自动检查前一日 `failed` 条目并优先补学

### 9.3 安全
- 用户画像数据仅存储在本地，不对外传输（默认 Hermes 隐私原则）
- `.env` 中的 API Key 安全管理

### 9.4 可扩展性
- 支持新增语言的 KB
- 支持自定义遗忘曲线参数
- 支持切换存储后端（MD ↔ JSON ↔ SQLite）

---

## 10. 文件/模块清单 [✓]

| 文件/模块 | 类型 | 用途 |
|----------|------|------|
| `skills/learning_kb/knowledge_base.json` | Data | [✓] 全量知识库（100场景×1000词） |
| `skills/learning_kb/kb_principles.md` | Data | [✓] 知识库生成原则文档 |
| `skills/learning_kb/generate_kb.py` | Sub-Agent | [✓] 全量知识库生成脚本 |
| `skills/learning_kb/generate_custom_plan.py` | Sub-Agent | [✓] 定制轨道框架生成（画像→LLM→输出 custom_plan.json） |
| `skills/learning_kb/custom_plan.json` | Data | [?] 60日定制计划框架（需至少一次画像后执行 generate_custom_plan.py 生成） |
| `skills/init/SKILL.md` | Skill | [✓] 用户画像注册对话流程 |
| `skills/daily_learning/SKILL.md` | Skill | [✓] 日常学习三段式推送交互 |
| `skills/active_review/SKILL.md` | Skill | [✓] 主动复习宽松识别交互 |
| `skills/learning_kb/daily/` | Data | daily_learning_content_*.json 输出目录 |
| `plugins/init/` | Plugin | [✓] 初始化编排：init.py + data_manager.py + spaced_repetition.py + __init__.py + plugin.yaml |
| `plugins/init/__init__.py` | Plugin | [✓] 注册 5 个工具 + hook |
| `plugins/init/init.py` | Module | [✓] 主编排器：预生成/LLM加工/打卡处理 |
| `plugins/init/data_manager.py` | Module | [✓] JSON 文件读写 + UID 生成 + 6文件管理 |
| `plugins/init/spaced_repetition.py` | Module | [✓] 遗忘曲线7次排期 + CRON注册 |
| `plugins/user_profile/` | Plugin | [✓] 用户画像 CRUD（save/get/check） |
| `plugins/learning_plan/` | Plugin | [✓] 学习计划查询（get_today_plan/get_by_date） |
| `plugins/review_scheduler/` | Plugin | [✓] 复习调度（包装 spaced_repetition） |
| `plugins/learning_log/` | Plugin | [✓] 学习日志查询（get_recent_log/get_by_date） |
| `data/` | Data | [✓] JSON 文件体系（6个核心文件，详见5.3） |
| `config/config.yaml` | Config | [✓] 启用全部 5 个插件 |

---

## 11. 里程碑 [?] （时间待定）

| 阶段 | 内容 | 时间 |
|------|------|------|
| P0 | 基础架构搭建：Skills 目录 + Plugins 骨架 + 配置 | TBD |
| P1 | 用户画像注册 + 知识库初始化 + 学习计划生成 | TBD |
| P2 | 遗忘曲线定时推送 + 学习日志 + 主动复习 | TBD |
| P3 | 多语言支持 + 行业定制 KB 增强 | TBD |

---

## 12. 设计决策记录 [✓]

> 以下为 PRD 评审阶段已确认的设计决策：

| # | 决策项 | 结论 | 说明 |
|---|-------|------|------|
| 1 | 扫码登录实现 | 待定 | 需根据 HERMES Gateway 接入方案确定（微信/自建/终端扫码） |
| 2 | 推送渠道 | 终端显示 | 优先终端，后续可通过 Gateway 扩展 |
| 3 | 用户画像存储 | `~/.hermes/memories/USER.md` | 复用 HERMES 原生记忆机制 |
| 4 | 结构化存储 | JSON 文件体系 | 6个核心 JSON 文件，统一 data/ 目录管理 |
| 5 | 每日时间分配 | 6 时段均分 | 起床/午休前/午休后/下班后/晚饭后/睡前，总量 ÷ 5 分配 |
| 6 | 跨夜复习处理 | 自动顺延到次日 | 22:00–08:00 的任务顺延至次日首个可用时段 |
| 7 | 学习计划生成（双轨） | 双 PY + LLM 按日增量 | `generate_custom_plan.py` 输出定制框架 → `plugins/init/init.py` 每日合并双轨输出 DAILY_LEARNING |
| 8 | 知识库粒度 | 全量场景覆盖 | KB 提供全量素材池，PY 排框架，LLM 按日从素材池选取扩充 |
| 9 | 多用户支持 | 单用户 | 一个部署只服务一个学习者 |
| 10 | 复习触发方式 | 自然语言宽松识别 | "复习/回顾/再看一遍/巩固"等关键词即激活 |
| 11 | 掌握度模型 | 用户主动标记 | 用户告知"记住了"，累计达标后停止推送 |
| 12 | 语言水平字段 | 不需要 | 从用户岗位/行业自动推断水平起点 |
| 13 | 错误处理 | 重试 3 次 + 次日补学 | 失败标记 → 每日 00:00 检查 → 优先补学 → 后续顺延 |
| 14 | 遗忘曲线参数 | 7 次基准（见 6.1） | 固定间隔，跨夜自动顺延 |
| 15 | 通用轨道时长 | 默认 60 天 | 100 场景 × ~10 句/日 ≈ 60 天 |
| 16 | 每日三段式 | 上午/下午学新 + 晚间复习打卡 | 复习与新学之间 30min 间隔 |
| 17 | 未掌握降级 | 连续 3 次 review_fail → 降级 | 降级到更简单场景重新学习 |
| 18 | 发音偏好 | 画像时收集 | 写入 user_preference.json + HERMES.MD，传参给 LLM 提示词 |
| 19 | 文件命名 | 全部英文 | 包括所有 .py .json .md 文件 |
