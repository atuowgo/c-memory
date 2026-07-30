---
confidence: 0.5
deprecated: false
domain: workflow
hit_count: 1
id: edit-then-read-pattern
last_seen: '2026-07-30'
scope: personal
trigger: 编辑文件后立即读取以验证修改
---

## Action
在编辑文件后，应自动读取该文件以确认修改正确，避免后续错误

## Evidence
在编辑 procedure_store.py 和 llm.py 后，立即有 Read 操作读取同一文件