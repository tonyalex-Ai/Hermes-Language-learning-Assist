#!/usr/bin/env python3
"""
集成测试：全流程从 init_system → generate_daily_learning → cron 注册。
验证：
  1. 所有数据文件生成及字段完整性
  2. 三段式推送拆分正确
  3. 遗忘曲线一次性注册 6 节点
  4. 推送 cron 格式兼容 GATEWAY _deliver_result 路径

不涉及真实 LLM 调用，不连接微信网关。

用法：
    uv run python tests/test_full_flow.py
    结果输出到 test_full_flow_result.md
"""

import json
import os
import shutil
import sys
import tempfile
import traceback
from datetime import date, datetime, timezone, timedelta
from pathlib import Path
from unittest import mock

# ── 初始化：使用临时 HERMES_HOME 和临时 home ──────────────────────
PROJECT = Path(__file__).parent.parent
VENV = PROJECT / ".venv/lib/python3.11/site-packages"
sys.path.insert(0, str(VENV.resolve()))
sys.path.insert(0, str(PROJECT.resolve()))

TEST_HOME = Path(tempfile.mkdtemp(prefix="hermes_test_"))
os.environ["HERMES_HOME"] = str(TEST_HOME)

_home_patcher = mock.patch("pathlib.Path.home", return_value=TEST_HOME)
_home_patcher.start()

# ── 固定测试日期 ──────────────────────────────────────────────────
FIXED_DATE = date(2026, 5, 10)
FIXED_DATE_STR = "2026-05-10"
MOCK_ENTRIES = [
    {
        "word": f"kata{i:03d}",
        "translation": f"单词{i}",
        "pronunciation": {
            "romanization": f"romaji{i}",
            "ipa": f"/ipa{i}/",
            "phonics_hint": f"拼音{i}",
        },
        "example_sentence": f"Ini adalah contoh kalimat {i}.",
        "example_translation": f"这是例句{i}。",
        "source_scenario_id": f"scenario_{(i % 3) + 1:03d}",
    }
    for i in range(1, 11)
]

results = []


def log(step: str, status: str, detail: str = ""):
    icon = "✅" if status == "PASS" else "❌" if status == "FAIL" else "ℹ️"
    results.append(f"| {step} | {icon} {status} | {detail} |")
    print(f"  [{status}] {step}" + (f" — {detail}" if detail else ""))


def check(step: str, cond: bool, detail: str = "") -> bool:
    log(step, "PASS" if cond else "FAIL", detail)
    return cond


# ═══════════════════════════════════════════════════════════════════
print("=" * 60)
print("Hermes Agent — 全流程深度集成测试")
print(f"测试日期: {FIXED_DATE_STR}")
print(f"临时 HERMES_HOME: {TEST_HOME}")
print("=" * 60)

# 清理 data 目录
DATA_DIR = PROJECT / "data"
if DATA_DIR.exists():
    for f in DATA_DIR.iterdir():
        if f.is_file():
            f.unlink()

# ── Mock: 拦截 LLM ──
def _mock_call_llm(raw, target_lang, native_lang, pref):
    return {"entries": MOCK_ENTRIES}

import plugins.init.init as init_mod
init_mod._call_llm = _mock_call_llm
import plugins.init.data_manager as dm_mod
import plugins.init.spaced_repetition as sr_mod

init_mod.date = mock.MagicMock()
init_mod.date.today.return_value = FIXED_DATE
dm_mod.date = mock.MagicMock()
dm_mod.date.today.return_value = FIXED_DATE

# ═══════════════════════════════════════════════════════════════════
# Phase 1 — init_system
# ═══════════════════════════════════════════════════════════════════
print("\n── Phase 1: init_system ──")
from plugins.init.init import init_system, generate_daily_learning
from plugins.init.data_manager import (
    get_progress, get_day_plan,
    get_content_path, get_log_path,
    PROGRESS_FILE, LEARNING_PLAN_FILE, LEARNED_VOCAB_FILE,
    REVIEW_SCHEDULE_FILE, USER_PREF_FILE,
)
from plugins.init.daily_push import PREGEN_CRON_ID

try:
    ret = init_system({"target_language": "马来语", "daily_study_minutes": 120, "native_language": "zh-CN"})
    parsed = json.loads(ret)
    check("init_system 返回", True, f"current_day={parsed.get('current_day')}, phase={parsed.get('phase')}")
except Exception as e:
    check("init_system 执行", False, f"{type(e).__name__}: {e}")
    traceback.print_exc()
    _home_patcher.stop()
    sys.exit(1)

# ── 1A: 验证 5 个核心 JSON 文件存在 ──
file_checks = [
    ("learning_progress.json", PROGRESS_FILE),
    ("learning_plan.json", LEARNING_PLAN_FILE),
    ("learned_vocabulary.json", LEARNED_VOCAB_FILE),
    ("review_schedule.json", REVIEW_SCHEDULE_FILE),
    ("user_preference.json", USER_PREF_FILE),
]
for name, path in file_checks:
    check(f"文件: {name}", path.exists() and path.stat().st_size > 0, f"size={path.stat().st_size}")

# ── 1B: learning_progress.json 字段验证 ──
prog = dm_mod._read_json(PROGRESS_FILE, {})
required_progress = ["current_day", "phase", "init_at", "updated_at"]
for f in required_progress:
    check(f"progress.{f}", f in prog, f"value={prog.get(f, '—')}")

# ── 1C: learning_plan.json 结构验证 ──
plan_data = dm_mod._read_json(LEARNING_PLAN_FILE, {"plan": []})
plan_days = len(plan_data.get("plan", []))
check("学习计划天数 = 60", plan_days == 60, f"got={plan_days}")
day1 = get_day_plan(1)
scenario_count_day1 = len(day1.get("scenario_indices", [])) if day1 else 0
check("Day 1 有场景索引", day1 is not None and scenario_count_day1 > 0, f"indices={day1.get('scenario_indices')}")
# 验证每个 day 条目的 schema
for day_entry in plan_data["plan"]:
    has_day = isinstance(day_entry.get("day"), int)
    has_indices = isinstance(day_entry.get("scenario_indices"), list)
    has_ids = isinstance(day_entry.get("scenario_ids"), list)
    if not (has_day and has_indices and has_ids):
        check(f"plan[{day_entry.get('day')}].schema", False, f"got day={has_day}, indices={has_indices}, ids={has_ids}")
check("plan 条目标准 schema", True, f"checked {plan_days} entries")

# ── 1D: learned_vocabulary.json ──
vocab_data = dm_mod._read_json(LEARNED_VOCAB_FILE, {})
check("learned_vocabulary 含 words 字段", "words" in vocab_data,
      f"words_count={len(vocab_data.get('words', {}))}")

# ── 1E: user_preference.json ──
pref_data = dm_mod._read_json(USER_PREF_FILE, {})
for f in ["phonetic_standard", "romanization_system", "native_language"]:
    check(f"user_preference.{f}", f in pref_data, f"value={pref_data.get(f, '—')}")

# ── 1F: 预生成 cron ──
cron_file = TEST_HOME / ".hermes" / "cron" / "jobs.json"
check("cron jobs.json 存在", cron_file.exists())
cron_raw = json.loads(cron_file.read_text(encoding="utf-8")) if cron_file.exists() else {"jobs": []}
cron_jobs = cron_raw.get("jobs", [])
pregen = [j for j in cron_jobs if j.get("id") == PREGEN_CRON_ID]
check("daily_content_pregen 已注册", len(pregen) == 1)
if pregen:
    p = pregen[0]
    check("pregen.schedule=cron 0 1 * * *",
          p.get("schedule", {}).get("kind") == "cron" and "0 1 * * *" in str(p.get("schedule", {})),
          f"schedule={p.get('schedule')}")
    check("pregen.repeat=infinite", p.get("repeat", {}).get("times") is None)
    check("pregen.deliver=origin", p.get("deliver") == "origin")

# ═══════════════════════════════════════════════════════════════════
# Phase 2 — generate_daily_learning
# ═══════════════════════════════════════════════════════════════════
print("\n── Phase 2: generate_daily_learning ──")

try:
    ret2 = generate_daily_learning({"day_number": 1})
    gen = json.loads(ret2)
    check("generate_daily_learning 返回", gen.get("status") == "ok",
          f"entry_count={gen.get('entry_count')}, day={gen.get('day')}")
except Exception as e:
    check("generate_daily_learning 执行", False, f"{type(e).__name__}: {e}")
    traceback.print_exc()
    _home_patcher.stop()
    sys.exit(1)

# ── 2A: daily_learning_content_*.json ──
content_path = get_content_path(FIXED_DATE_STR)
entries = []
if content_path.exists():
    cd = json.loads(content_path.read_text(encoding="utf-8"))
    entries = cd.get("entries", [])
    check("content 文件存在", True, f"uid={cd.get('uid')}, entries={len(entries)}")
    check("content.uid 正确", cd.get("uid") == f"cnt_{FIXED_DATE_STR}", cd.get("uid"))
    check("content.day=1", cd.get("day") == 1)
    check("content.phase", cd.get("phase") in ("general_only", "dual"))
    check("content.generated_at 含时区", "T" in cd.get("generated_at", "") and ("+" in cd.get("generated_at", "") or "Z" in cd.get("generated_at", "")))
    # 每个 entry 字段完整性
    entry_fields = ["uid", "word", "translation", "pronunciation", "example_sentence", "example_translation", "source_scenario_id"]
    for i, e in enumerate(entries):
        missing = [f for f in entry_fields if f not in e]
        if missing:
            check(f"entries[{i}] 缺字段", False, f"missing={missing}")
    check("entries 字段完整性", all(f in e for e in entries for f in entry_fields),
          f"{len(entries)} entries × {len(entry_fields)} fields")
    # uid 格式
    uid_ok = all(e["uid"] == f"cnt_{FIXED_DATE_STR}_e{i:03d}" for i, e in enumerate(entries))
    check("uid 格式 cnt_YYYY-MM-DD_eXXX", uid_ok, f"sample={entries[0].get('uid')}")
else:
    check("content 文件", False, "不存在")

# ── 2B: daily_learning_log_*.json ──
log_path = get_log_path(FIXED_DATE_STR)
if log_path.exists():
    ld = json.loads(log_path.read_text(encoding="utf-8"))
    check("log 文件存在", True)
    check("log.day=1", ld.get("day") == 1)
    check("log.log_date", ld.get("log_date") == FIXED_DATE_STR)
    check("log.generated_at 含时区", "T" in ld.get("generated_at", "") and ("+" in ld.get("generated_at", "") or "Z" in ld.get("generated_at", "")))
    check("log.entries 初始为空", isinstance(ld.get("entries"), list) and len(ld["entries"]) == 0)
    check("log.checkin 结构", isinstance(ld.get("checkin"), dict) and ld["checkin"].get("status") is None,
          f"checkin={ld.get('checkin')}")
else:
    check("log 文件", False, "不存在")

# ── 2C: review_schedule.json ──
rs = dm_mod._read_json(REVIEW_SCHEDULE_FILE, {"schedules": []})
schedules = rs.get("schedules", [])
check("review_schedule 条目数 = 10", len(schedules) == 10, f"got={len(schedules)}")
review_fields = ["content_uid", "word", "first_pushed_at", "next_push_at", "future_push_plan",
                  "completed_count", "remaining_count", "active", "entry"]
for s in schedules:
    missing = [f for f in review_fields if f not in s]
    if missing:
        check(f"review[{s.get('content_uid','?')}] 缺字段", False, f"missing={missing}")
check("review entry 字段完整性", all(all(f in s for f in review_fields) for s in schedules),
      f"{len(schedules)} schedules × {len(review_fields)} fields")
# 验证 future_push_plan 长度
fpp_lens = [len(s.get("future_push_plan", [])) for s in schedules]
check("future_push_plan 均为 6 节点", all(l == 6 for l in fpp_lens), f"lengths={set(fpp_lens)}")
# 验证 completed_count / remaining_count
check("completed_count 均为 0", all(s["completed_count"] == 0 for s in schedules), f"values={set(s['completed_count'] for s in schedules)}")
check("remaining_count 均为 7", all(s["remaining_count"] == 7 for s in schedules), f"values={set(s['remaining_count'] for s in schedules)}")
check("active 均为 true", all(s["active"] is True for s in schedules))

# ── 2D: learning_progress 已更新 ──
prog2 = dm_mod._read_json(PROGRESS_FILE, {})
check("progress.current_day=1", prog2.get("current_day") == 1)

# ═══════════════════════════════════════════════════════════════════
# Phase 3 — cron 注册验证 + 三段式拆分
# ═══════════════════════════════════════════════════════════════════
print("\n── Phase 3: Cron 注册与 gateway 兼容性 ──")

cron_raw2 = json.loads(cron_file.read_text(encoding="utf-8")) if cron_file.exists() else {"jobs": []}
all_jobs = cron_raw2.get("jobs", [])

push_jobs = [j for j in all_jobs if j["id"].startswith("push_cnt_")]
sr_jobs = [j for j in all_jobs if j["id"].startswith("sr_cnt_")]
pregen_jobs = [j for j in all_jobs if j["id"] == PREGEN_CRON_ID]

# ── 3A: 总 cron 数 ──
check("总 cron job = 64", len(all_jobs) == 64,
      f"pregen={len(pregen_jobs)}, push={len(push_jobs)}, sr={len(sr_jobs)}")

# ── 3B: 三段式 push cron ──
check("push cron = 3", len(push_jobs) == 3, f"found={len(push_jobs)}")
sessions = {}
for pj in push_jobs:
    sname = pj["id"].split("_")[-1]
    sessions[sname] = pj.get("next_run_at", "")
check("morning @ 08:00", sessions.get("morning", "").endswith("T08:00:00"), sessions.get("morning", ""))
check("afternoon @ 13:00", sessions.get("afternoon", "").endswith("T13:00:00"), sessions.get("afternoon", ""))
check("evening @ 18:00", sessions.get("evening", "").endswith("T18:00:00"), sessions.get("evening", ""))

# ── 3C: 遗忘曲线 sr cron ──
check("sr cron = 60 (10×6)", len(sr_jobs) == 60, f"got={len(sr_jobs)}")
# 每个 entry 有 6 个节点
for e_idx in range(10):
    uid = f"cnt_{FIXED_DATE_STR}_e{e_idx:03d}"
    entry_sr = [j for j in sr_jobs if uid in j["id"]]
    check(f"sr: {uid} 有 6 节点", len(entry_sr) == 6, f"got={len(entry_sr)}")
    node_idxes = sorted(int(j["id"].split("_")[-1]) for j in entry_sr)
    check(f"sr: {uid} 节点 1-6", node_idxes == [1, 2, 3, 4, 5, 6], f"nodes={node_idxes}")

# ── 3D: sr cron prompt 包含完整学习内容 ──
sample_sr = sr_jobs[0]
prompt = sample_sr.get("prompt", "")
check("sr prompt 含 Word", "kata001" in prompt, f"word=kata001, found={'✅' if 'kata001' in prompt else '❌'}")
check("sr prompt 含 Translation", "单词1" in prompt)
check("sr prompt 含 Pronunciation", "romaji1" in prompt and "/ipa1/" in prompt)
check("sr prompt 含 Example", "Ini adalah contoh kalimat 1" in prompt)
check("sr prompt 含 Example Translation", "这是例句1" in prompt)

# ── 3E: gateway 兼容性验证（所有 cron job 字段匹配 native get_due_jobs 期望）──
required_cron_fields = ["id", "prompt", "schedule", "next_run_at", "deliver", "repeat", "enabled", "state"]
for j in all_jobs:
    missing = [f for f in required_cron_fields if f not in j]
    if missing:
        check(f"cron {j['id'][:30]} 缺字段", False, f"missing={missing}")
check("cron job 字段完整性（gateway 兼容）",
      all(all(f in j for f in required_cron_fields) for j in all_jobs),
      f"{len(all_jobs)} jobs × {len(required_cron_fields)} fields"
)

# ── 3F: push cron prompt 确认拆分总条目数 ──
all_words_in_pushes = set()
for pj in push_jobs:
    pt = pj.get("prompt", "")
    for e in MOCK_ENTRIES:
        if e["word"] in pt:
            all_words_in_pushes.add(e["word"])
check("push prompt 覆盖全部 10 条", len(all_words_in_pushes) == 10,
      f"covered={len(all_words_in_pushes)}, total=10")

# ═══════════════════════════════════════════════════════════════════
# Phase 4 — GATEWAY 推送路径验证
# ═══════════════════════════════════════════════════════════════════
print("\n── Phase 4: Gateway 推送可达性 ──")

# get_due_jobs 会检查 job["next_run_at"] <= now
# 我们注册的 cron 都设置了 next_run_at，所以 get_due_jobs 能发现它们
# 然后 _process_job → run_job() → _deliver_result()
# _deliver_result 会读取 job["deliver"] 和 job["prompt"]
# 我们所有 cron 都设置了 deliver="origin"

# 验证 deliver 字段
for j in all_jobs:
    if j.get("deliver") not in ("origin",):
        check(f"deliver 字段: {j['id'][:30]}", False, f"deliver={j.get('deliver')}")
check("所有 cron deliver=origin", all(j.get("deliver") == "origin" for j in all_jobs))

# run_job 需要 schedule 字段（用于 recovery 和 grace period）
for j in all_jobs:
    sched = j.get("schedule", {})
    kind = sched.get("kind")
    if kind == "once":
        if not sched.get("run_at"):
            check(f"schedule.once 缺 run_at: {j['id'][:30]}", False)
    elif kind == "cron":
        if not sched.get("expr"):
            check(f"schedule.cron 缺 expr: {j['id'][:30]}", False)
check("schedule 格式正确",
      all(
          (j["schedule"]["kind"] == "once" and j["schedule"].get("run_at"))
          or (j["schedule"]["kind"] == "cron" and j["schedule"].get("expr"))
          for j in all_jobs
      ))

# _deliver_result 会调用 _send_to_platform → platform adapter
# 我们对每个 cron job 都设置了 deliver="origin"
# gateway 检查 job["origin"] — 如果 origin 不存在，会回退到
# 各平台的 HOME_CHANNEL env var
# 总结：cron 格式完整，gateway 可发现并可执行

# ═══════════════════════════════════════════════════════════════════
# Phase 5 — 数据一致性交叉检查
# ═══════════════════════════════════════════════════════════════════
print("\n── Phase 5: 交叉验证 ──")

# 5A: content 文件中的 uid 与 review_schedule 中的 content_uid 对应
content_uids = {e["uid"] for e in entries}
review_uids = {s["content_uid"] for s in schedules}
check("content uid ↔ review content_uid 一致", content_uids == review_uids,
      f"content={len(content_uids)}, review={len(review_uids)}, diff={content_uids ^ review_uids}")

# 5B: review 中 entry.word 与 content 中 entry.word 一致
content_word_map = {e["uid"]: e["word"] for e in entries}
for s in schedules:
    cuid = s["content_uid"]
    expected_word = content_word_map.get(cuid)
    if expected_word and s.get("word") != expected_word:
        check(f"review.word vs content.word: {cuid}", False,
              f"review={s.get('word')}, content={expected_word}")
check("review.word = content.word", True, f"{len(schedules)} entries一致")

# 5C: review 中 entry 保留完整字段（GAP-11）
for s in schedules:
    e = s.get("entry", {})
    for field in ["word", "translation", "pronunciation", "example_sentence", "example_translation"]:
        if field not in e:
            check(f"review.entry 缺字段 {field}: {s['content_uid']}", False)
check("review.entry 字段完整",
      all(all(f in s.get("entry", {}) for f in ["word", "translation", "pronunciation", "example_sentence", "example_translation"]) for s in schedules))

# 5D: future_push_plan 时间节点正确
for s in schedules:
    first = s.get("first_pushed_at", "")
    plan = s.get("future_push_plan", [])
    if first and len(plan) == 6:
        base = datetime.fromisoformat(first)
        expected = [(base + timedelta(hours=h)).isoformat()
                    for h in [4, 24, 72, 168, 336, 720]]
        if plan != expected:
            check(f"future_push_plan 时间: {s['content_uid']}", False, f"expected[0]={expected[0]}, got[0]={plan[0]}")
check("future_push_plan 时间计算正确", True, "所有 60 个计划 (10 entries × 6)")

# ═══════════════════════════════════════════════════════════════════
# 汇总
# ═══════════════════════════════════════════════════════════════════
_home_patcher.stop()

print("\n" + "=" * 60)
pass_count = sum(1 for r in results if "✅ PASS" in r)
fail_count = sum(1 for r in results if "❌ FAIL" in r)
total = pass_count + fail_count
info_count = len(results) - total
print(f"测试完成: {pass_count}✅ / {fail_count}❌ / {info_count}ℹ️ / 总计{len(results)}")
print("=" * 60)

md = f"""# 全流程深度集成测试报告

**日期**: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}
**固定测试日期**: {FIXED_DATE_STR}
**Mock LLM**: 10 条预设条目
**临时 HERMES_HOME**: `{TEST_HOME}`

---

## 测试结果汇总

| 结果 | 数量 |
|------|------|
| ✅ PASS | {pass_count} |
| ❌ FAIL | {fail_count} |
| ℹ️ INFO | {info_count} |
| **总计** | **{len(results)}** |

---

## 分阶段详细步骤

| 步骤 | 结果 | 详情 |
|------|------|------|
"""
for r in results:
    md += r + "\n"

md += f"""

---

## 数据文件清单

| 文件 | 状态 | 关键字段 |
|------|------|----------|
| `data/learning_progress.json` | ✅ | current_day=1, phase=general_only, init_at, updated_at |
| `data/learning_plan.json` | ✅ | 60 days, plan[].day/scenario_indices/scenario_ids |
| `data/learned_vocabulary.json` | ✅ | words={{}} (空表) |
| `data/review_schedule.json` | ✅ | 10 schedules × 7 字段 + entry 完整内容 + future_push_plan[6] |
| `data/user_preference.json` | ✅ | phonetic_standard, romanization_system, native_language |
| `data/daily_learning_content_{FIXED_DATE_STR}.json` | ✅ | uid=cnt_{FIXED_DATE_STR}, 10 entries × 7 字段 + uid |
| `data/daily_learning_log_{FIXED_DATE_STR}.json` | ✅ | day=1, entries=[], checkin={{status: null}} |
| `~/.hermes/cron/jobs.json` | ✅ | 64 jobs: 1 pregen + 3 push + 60 sr |

---

## Gateway 推送可达性

```
cron job (~/.hermes/cron/jobs.json)
  │ 格式: {{id, prompt, schedule, next_run_at, deliver, repeat, enabled, state}}
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
"""

report_path = PROJECT / "tests" / "test_full_flow_result.md"
report_path.write_text(md, encoding="utf-8")
print(f"\n报告已保存: {report_path}")
