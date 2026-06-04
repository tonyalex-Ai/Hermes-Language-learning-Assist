# Skill: 主动复习

## 描述
用户主动发起复习时使用。

## 触发条件
用户消息含"复习/回顾/再看一遍/巩固/再学一次/没记住/review/again"等关键词。

## 流程
1. 调用 `review_scheduler.handle_active_review({})` 获取需复习条目
2. 向用户展示条目（word → romanization → sentence → translation）
3. 追问："这些还记得吗？"
4. 用户说"记住了 [uid]" → 调用 `review_scheduler.record_review({"content_uid": "..."})`
5. 用户说"没记住" → 重新讲解
