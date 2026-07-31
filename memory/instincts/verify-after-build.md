---
confidence: 0.5
deprecated: false
domain: testing
hit_count: 1
id: verify-after-build
last_seen: '2026-07-31'
scope: personal
trigger: 执行构建或生成命令后，检查产物是否符合预期
---

## Action
构建后使用 Bash 命令检查生成的文件内容，如 .gitignore，确保正确性

## Evidence
构建后运行 rm -rf dist && ./build.sh 并检查 .gitignore 内容