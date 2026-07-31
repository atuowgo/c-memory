---
confidence: 0.9
deprecated: false
domain: workflow
hit_count: 17
id: read-before-edit-pattern
last_seen: '2026-07-31'
scope: personal
trigger: 在编辑文件前先读取相关上下文（如 README、现有代码）
---

## Action
先读取目标文件或相关文档，再执行编辑

## Evidence
多次 Read 操作（llm.py、__init__.py、设计文档）和 Bash 查看 README 上下文后才进行 Edit