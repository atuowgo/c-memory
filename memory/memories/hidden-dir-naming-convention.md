---
created: '2026-07-29'
description: 项目使用隐藏目录命名约定（.venv, .serena, .c-memory）
id: hidden-dir-naming-convention
keywords:
- hidden-dir
- naming-convention
type: project
---

构建产物输出到 dist/.c-memory/ 隐藏目录，与项目中的 .venv、.serena 等隐藏目录命名风格一致。部署时使用 cp -R dist/.c-memory target-project/。