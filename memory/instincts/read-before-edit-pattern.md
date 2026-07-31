---
confidence: 0.9
deprecated: false
domain: workflow
hit_count: 13
id: read-before-edit-pattern
last_seen: '2026-07-31'
scope: personal
trigger: 修改配置文件或代码前
---

## Action
先读取相关文件内容，再进行编辑

## Evidence
在编辑 settings.json 和 .gitignore 前，先读取了相关文件（如 summarize.py、storage.py）