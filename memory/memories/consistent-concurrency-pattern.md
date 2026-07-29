---
created: '2026-07-29'
description: transcript_store.py 与 observation_store.py 使用相同的非阻塞游标+孤儿扫描并发模式
id: consistent-concurrency-pattern
keywords:
- concurrency
- pattern
type: project
---

transcript_store.py 实现了与 observation_store.py 完全一致的并发模式：非阻塞游标认领 + 孤儿 session 补漏扫描。这种一致性有助于维护和扩展。