---
created: '2026-07-29'
description: observation_store.py是现有模块，新模块应参考其模式
id: existing-module-pattern
keywords:
- pattern
- observation_store
type: project
---

observation_store.py实现了非阻塞并发模式，transcript_store.py应镜像其try_claim_session/release_session/find_orphan_sessions等模式。