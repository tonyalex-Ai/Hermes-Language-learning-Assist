# Skills Master Index

该项目拥有的技能清单。

## 技能列表

| 技能名称 | 目录 | 描述 | 状态 |
|---------|------|------|------|
| 示例技能 | `skills/example_skill/` | 示例技能模板 | 模板 |
| 初始化注册 | `skills/init/SKILL.md` | 用户首次使用的画像收集对话流程 | ✓ |
| 日常学习 | `skills/daily_learning/SKILL.md` | 每日三段式学习交互流程 | ✓ |
| 主动复习 | `skills/active_review/SKILL.md` | 用户主动发起复习的交互流程 | ✓ |

## 管理

```bash
# Hermes 会自动发现 skills/ 下的所有 SKILL.md
# 开发调试时将 skills/ 链接到 ~/.hermes/skills/
ln -sf /path/to/project/skills ~/.hermes/skills

# 查看已加载的技能
hermes skills list
```
