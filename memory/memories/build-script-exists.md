---
created: '2026-07-29'
description: 项目根目录有 build.sh 用于构建发布包到 dist/
id: build-script-exists
keywords:
- build
- dist
type: project
---

build.sh 将 hooks/、memory_lib/、.claude/settings.json、.env.example、requirements.txt、README.md 打包到 dist/，自动清理 __pycache__，排除真实 .env、memory/ 数据、tests/、docs/。dist/ 已加入 .gitignore。