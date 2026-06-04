# Skill: 初始化注册

## 描述
用户首次使用的画像收集流程。

## 指令

逐个收集：
1. 昵称
2. 职业
3. 行业
4. 岗位
5. 每日可学习分钟数
6. 想学什么语言
7. 母语是什么
8. 发音标注偏好（IPA / 罗马音 / 母语音译）

收集完成 → 调用 `user_profile.save_profile` 写入 `~/.hermes/memories/USER.md`。

然后按顺序：
1. 更新 `.hermes.md` 中的用户画像 JSON
2. 调用 `init.init_system(target_language, daily_study_minutes)`
3. 调用 `init.generate_daily_learning(day_number=1)`
4. 告知用户："已生成第 1 天内容，明天起我会每天早上检查并推送"

之后每天 00:00-06:00 会自动执行心跳检查流程（见 HERMES.MD），无需你再手动调用。
