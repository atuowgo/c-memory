---
confidence: 0.5
deprecated: false
domain: workflow
hit_count: 1
id: verify-file-existence-before-updating
last_seen: '2026-07-31'
scope: personal
trigger: 当用户要求更新或创建文档时，先检查目标文件是否存在及其格式
---

## Action
在修改或创建文档前，先列出目录内容确认文件是否存在、格式（如 .md 或 .html），再决定是更新现有文件还是新建文件

## Evidence
用户询问更新 html 概览文档还是新建 .md 版本，assistant 先执行了 `rtk ls -la docs/ | grep -i overview` 来确认文件存在性