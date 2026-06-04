# 全流程深度集成测试报告

**日期**: 2026-06-01 04:36 UTC
**固定测试日期**: 2026-05-10
**Mock LLM**: 10 条预设条目
**临时 HERMES_HOME**: `/tmp/hermes_test_9__4j4i1`

---

## 测试结果汇总

| 结果 | 数量 |
|------|------|
| ✅ PASS | 82 |
| ❌ FAIL | 0 |
| ℹ️ INFO | 0 |
| **总计** | **82** |

---

## 分阶段详细步骤

| 步骤 | 结果 | 详情 |
|------|------|------|
| init_system 返回 | ✅ PASS | current_day=0, phase=general_only |
| 文件: learning_progress.json | ✅ PASS | size=150 |
| 文件: learning_plan.json | ✅ PASS | size=8591 |
| 文件: learned_vocabulary.json | ✅ PASS | size=69 |
| 文件: review_schedule.json | ✅ PASS | size=73 |
| 文件: user_preference.json | ✅ PASS | size=151 |
| progress.current_day | ✅ PASS | value=0 |
| progress.phase | ✅ PASS | value=general_only |
| progress.init_at | ✅ PASS | value=2026-06-01T04:36:58.476836+00:00 |
| progress.updated_at | ✅ PASS | value=2026-06-01T04:36:58.476912+00:00 |
| 学习计划天数 = 60 | ✅ PASS | got=60 |
| Day 1 有场景索引 | ✅ PASS | indices=[0, 1] |
| plan 条目标准 schema | ✅ PASS | checked 60 entries |
| learned_vocabulary 含 words 字段 | ✅ PASS | words_count=0 |
| user_preference.phonetic_standard | ✅ PASS | value=ipa |
| user_preference.romanization_system | ✅ PASS | value=standard |
| user_preference.native_language | ✅ PASS | value=zh-CN |
| cron jobs.json 存在 | ✅ PASS |  |
| daily_content_pregen 已注册 | ✅ PASS |  |
| pregen.schedule=cron 0 1 * * * | ✅ PASS | schedule={'kind': 'cron', 'expr': '0 1 * * *', 'display': '0 1 * * *'} |
| pregen.repeat=infinite | ✅ PASS |  |
| pregen.deliver=origin | ✅ PASS |  |
| generate_daily_learning 返回 | ✅ PASS | entry_count=10, day=1 |
| content 文件存在 | ✅ PASS | uid=cnt_2026-05-10, entries=10 |
| content.uid 正确 | ✅ PASS | cnt_2026-05-10 |
| content.day=1 | ✅ PASS |  |
| content.phase | ✅ PASS |  |
| content.generated_at 含时区 | ✅ PASS |  |
| entries 字段完整性 | ✅ PASS | 10 entries × 7 fields |
| uid 格式 cnt_YYYY-MM-DD_eXXX | ✅ PASS | sample=cnt_2026-05-10_e000 |
| log 文件存在 | ✅ PASS |  |
| log.day=1 | ✅ PASS |  |
| log.log_date | ✅ PASS |  |
| log.generated_at 含时区 | ✅ PASS |  |
| log.entries 初始为空 | ✅ PASS |  |
| log.checkin 结构 | ✅ PASS | checkin={'status': None, 'unmastered_content_uids': []} |
| review_schedule 条目数 = 10 | ✅ PASS | got=10 |
| review entry 字段完整性 | ✅ PASS | 10 schedules × 9 fields |
| future_push_plan 均为 6 节点 | ✅ PASS | lengths={6} |
| completed_count 均为 0 | ✅ PASS | values={0} |
| remaining_count 均为 7 | ✅ PASS | values={7} |
| active 均为 true | ✅ PASS |  |
| progress.current_day=1 | ✅ PASS |  |
| 总 cron job = 64 | ✅ PASS | pregen=1, push=3, sr=60 |
| push cron = 3 | ✅ PASS | found=3 |
| morning @ 08:00 | ✅ PASS | 2026-05-10T08:00:00 |
| afternoon @ 13:00 | ✅ PASS | 2026-05-10T13:00:00 |
| evening @ 18:00 | ✅ PASS | 2026-05-10T18:00:00 |
| sr cron = 60 (10×6) | ✅ PASS | got=60 |
| sr: cnt_2026-05-10_e000 有 6 节点 | ✅ PASS | got=6 |
| sr: cnt_2026-05-10_e000 节点 1-6 | ✅ PASS | nodes=[1, 2, 3, 4, 5, 6] |
| sr: cnt_2026-05-10_e001 有 6 节点 | ✅ PASS | got=6 |
| sr: cnt_2026-05-10_e001 节点 1-6 | ✅ PASS | nodes=[1, 2, 3, 4, 5, 6] |
| sr: cnt_2026-05-10_e002 有 6 节点 | ✅ PASS | got=6 |
| sr: cnt_2026-05-10_e002 节点 1-6 | ✅ PASS | nodes=[1, 2, 3, 4, 5, 6] |
| sr: cnt_2026-05-10_e003 有 6 节点 | ✅ PASS | got=6 |
| sr: cnt_2026-05-10_e003 节点 1-6 | ✅ PASS | nodes=[1, 2, 3, 4, 5, 6] |
| sr: cnt_2026-05-10_e004 有 6 节点 | ✅ PASS | got=6 |
| sr: cnt_2026-05-10_e004 节点 1-6 | ✅ PASS | nodes=[1, 2, 3, 4, 5, 6] |
| sr: cnt_2026-05-10_e005 有 6 节点 | ✅ PASS | got=6 |
| sr: cnt_2026-05-10_e005 节点 1-6 | ✅ PASS | nodes=[1, 2, 3, 4, 5, 6] |
| sr: cnt_2026-05-10_e006 有 6 节点 | ✅ PASS | got=6 |
| sr: cnt_2026-05-10_e006 节点 1-6 | ✅ PASS | nodes=[1, 2, 3, 4, 5, 6] |
| sr: cnt_2026-05-10_e007 有 6 节点 | ✅ PASS | got=6 |
| sr: cnt_2026-05-10_e007 节点 1-6 | ✅ PASS | nodes=[1, 2, 3, 4, 5, 6] |
| sr: cnt_2026-05-10_e008 有 6 节点 | ✅ PASS | got=6 |
| sr: cnt_2026-05-10_e008 节点 1-6 | ✅ PASS | nodes=[1, 2, 3, 4, 5, 6] |
| sr: cnt_2026-05-10_e009 有 6 节点 | ✅ PASS | got=6 |
| sr: cnt_2026-05-10_e009 节点 1-6 | ✅ PASS | nodes=[1, 2, 3, 4, 5, 6] |
| sr prompt 含 Word | ✅ PASS | word=kata001, found=✅ |
| sr prompt 含 Translation | ✅ PASS |  |
| sr prompt 含 Pronunciation | ✅ PASS |  |
| sr prompt 含 Example | ✅ PASS |  |
| sr prompt 含 Example Translation | ✅ PASS |  |
| cron job 字段完整性（gateway 兼容） | ✅ PASS | 64 jobs × 8 fields |
| push prompt 覆盖全部 10 条 | ✅ PASS | covered=10, total=10 |
| 所有 cron deliver=origin | ✅ PASS |  |
| schedule 格式正确 | ✅ PASS |  |
| content uid ↔ review content_uid 一致 | ✅ PASS | content=10, review=10, diff=set() |
| review.word = content.word | ✅ PASS | 10 entries一致 |
| review.entry 字段完整 | ✅ PASS |  |
| future_push_plan 时间计算正确 | ✅ PASS | 所有 60 个计划 (10 entries × 6) |


---

## 数据文件清单

| 文件 | 状态 | 关键字段 |
|------|------|----------|
| `data/learning_progress.json` | ✅ | current_day=1, phase=general_only, init_at, updated_at |
| `data/learning_plan.json` | ✅ | 60 days, plan[].day/scenario_indices/scenario_ids |
| `data/learned_vocabulary.json` | ✅ | words={} (空表) |
| `data/review_schedule.json` | ✅ | 10 schedules × 7 字段 + entry 完整内容 + future_push_plan[6] |
| `data/user_preference.json` | ✅ | phonetic_standard, romanization_system, native_language |
| `data/daily_learning_content_2026-05-10.json` | ✅ | uid=cnt_2026-05-10, 10 entries × 7 字段 + uid |
| `data/daily_learning_log_2026-05-10.json` | ✅ | day=1, entries=[], checkin={status: null} |
| `~/.hermes/cron/jobs.json` | ✅ | 64 jobs: 1 pregen + 3 push + 60 sr |

---

## Gateway 推送可达性

```
cron job (~/.hermes/cron/jobs.json)
  │ 格式: {id, prompt, schedule, next_run_at, deliver, repeat, enabled, state}
  │       ✅ get_due_jobs 可发现 (next_run_at <= now)
  │       ✅ _resolve_delivery_targets 可解析 (deliver="origin")
  │       ✅ run_job 可执行 (prompt 非空, schedule 含 kind)
  │       ✅ _deliver_result 可投递 (origin fallback → HOME_CHANNEL env var)
  │
  └─→ gateway cron ticker (60s 轮询)
       → get_due_jobs() → find job
       → advance_next_run() → for recurring: compute next (pregen)
       → _process_job(job)
         ├─ run_job(job) → AIAgent(prompt) → final_response
         ├─ save_job_output()
         └─ _deliver_result(job, response)
            ├─ _resolve_delivery_targets() → platform + chat_id
            └─ runtime_adapter.send() OR _send_to_platform() → 用户收到
```

三段式推送 (3 jobs) 和遗忘曲线 (60 jobs) 全部使用 `deliver="origin"` 格式，
gateway 可发现、可解析、可投递。实际发送需要平台适配器（如 WEIXIN_HOME_CHANNEL 配置）。

---

## 关键交叉验证

| 验证 | 结果 |
|------|------|
| content uid ↔ review content_uid | 完全一致 (10/10) |
| review.word = content.word | 完全一致 (10/10) |
| review.entry 含完整字段 | 全部含 word/translation/pronunciation/example |
| future_push_plan 时间计算 | 6 节点准确 (4h/24h/72h/168h/336h/720h) |
| push prompt 覆盖条目 | 3 个 push 合计覆盖全部 10 条 |
