---
confidence: 0.5
deprecated: false
domain: ''
hit_count: 1
id: read-docs-before-edit-pattern
last_seen: '2026-07-29'
scope: personal
trigger: 需要更新文档时，先读取文档相关段落再编辑
---

## Action
在编辑文档前先读取目标段落，确保修改位置准确

## Evidence
在更新 docs/build-and-deploy.md 前，分三次读取了不同偏移量的内容（7,10; 73,30; 118,20）