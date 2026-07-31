---
created: '2026-07-31'
description: 项目采用隐藏JSON文件存真实数据，渲染出人类可读的Markdown文件的模式
id: uses-hidden-json-plus-rendered-md-pattern
keywords:
- pattern
- json
- markdown
type: project
---

项目已有模式：用隐藏JSON文件（如.dedup_state.json）存储真实数据，然后渲染出人类可读的Markdown文件（如rules/auto-evolved.md）。新功能设计也遵循此模式，如memory/.recent-sessions.json存数据，memory/recent-sessions.md供人查看。