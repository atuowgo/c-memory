---
created: '2026-07-29'
description: install.sh 通过 basename 自动识别隐藏目录名
id: install-sh-auto-detect
keywords:
- install
- auto-detect
type: project
---

install.sh 使用 basename 命令自动识别出 .c-memory 目录名，并正确写入 .claude/settings.json 的 hook 命令前缀，无需硬编码。