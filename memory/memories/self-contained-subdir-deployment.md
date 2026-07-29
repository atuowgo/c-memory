---
created: '2026-07-29'
description: c-memory 采用自包含子目录部署方式
id: self-contained-subdir-deployment
keywords:
- deployment
- subdir
type: project
---

c-memory 部署为一个子目录（默认 c-memory/），包含所有依赖（.venv、memory_lib、hooks 等），.claude/settings.json 写到目标项目根目录，子目录名可自定义。install.sh 自动识别所在子目录，merge_settings.py 通过第三个参数递归改写命令前缀。