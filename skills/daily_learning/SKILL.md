# Skill: 日常学习

## 描述
每日学习交互。推送由代码自动执行，LLM 不参与。LLM 只在以下时机参与：

## 时机 1：晚间打卡
用户晚间收到复习推送后，你询问："今天的内容学完了吗？"
- "学完" → `init.handle_checkin({"status": "completed"})`
- "未学完 [content_uid列表]" → `init.handle_checkin({"status": "unmastered", "unmastered_content_uids": [...]})`

## 时机 2：回答学习问题
用户问翻译、发音等 → 直接回答，不操作文件。
