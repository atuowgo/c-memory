---
confidence: 0.5
deprecated: false
domain: code-style
hit_count: 1
id: consistent-pattern-reuse
last_seen: '2026-07-29'
scope: personal
trigger: 实现类似功能（如 transcript_store.py 与 observation_store.py 的并发模式）
---

## Action
复用已有的设计模式和代码结构，保持一致性

## Evidence
transcript_store.py 的并发模式与 observation_store.py 完全一致