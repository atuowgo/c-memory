---
created: '2026-07-31'
description: 项目需要忽略运行时数据文件，避免误提交
id: project-ignores-runtime-data
keywords:
- .gitignore
- runtime-data
type: project
---

在 .gitignore 中忽略了 .venv/、memory/、.env、__pycache__ 等运行时数据。提交信息中提到'打包产物加 .gitignore，避免目标项目误提交运行时数据'，说明项目有明确的运行时数据管理策略。