---
confidence: 0.5
deprecated: false
domain: workflow
hit_count: 1
id: read-before-write-pattern
last_seen: '2026-07-29'
scope: personal
trigger: 在修改或生成文档前，先读取相关源文件（如代码、现有文档）
---

## Action
先读取关键源文件获取最新状态，再执行写入或生成操作

## Evidence
本次会话中，在生成 artifact 文档前，先读取了 project-summary.md、recall.py、providers/__init__.py 等文件