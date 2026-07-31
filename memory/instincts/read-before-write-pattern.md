---
confidence: 0.7500000000000002
deprecated: false
domain: workflow
hit_count: 6
id: read-before-write-pattern
last_seen: '2026-07-31'
scope: personal
trigger: 编辑文件前先读取文件相关部分
---

## Action
在编辑文件之前，先读取该文件的相关部分，以确保修改基于最新内容。

## Evidence
观测记录显示先 Read 了 hooks/inject.py 和 docs/c-memory-overview.html，然后才进行 Edit 操作。