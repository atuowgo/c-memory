---
created: '2026-07-29'
description: merge_settings.py 不覆盖已有 .claude/settings.json
id: settings-template-filename
keywords:
- settings
- merge
type: project
---

merge_settings.py 合并 hooks 配置时，不覆盖目标项目已有的 .claude/settings.json 中的其他 hooks/permissions 配置，仅添加或更新 c-memory 相关的部分。