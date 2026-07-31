---
created: '2026-07-31'
description: c-memory 项目使用 build.sh 构建，生成 dist 目录，并包含 .gitignore 等文件
id: c-memory-build-script
keywords:
- build
- dist
- .gitignore
type: project
---

项目根目录有 build.sh 和 scripts/install.sh，构建时执行 ./build.sh 生成 dist/.c-memory 目录，其中包含 .gitignore 文件，忽略 .venv/、memory/、.env、__pycache__/、*.pyc 等。构建产物清单记录在 docs/build-and-deploy.md 中。