---
confidence: 0.5
deprecated: false
domain: ''
hit_count: 1
id: add-tests-for-new-features
last_seen: '2026-07-31'
scope: personal
trigger: 新增功能或修改关键逻辑时
---

## Action
编写单元测试覆盖新功能，包括关键边界条件和行为断言

## Evidence
新增 tests/test_embedding_providers.py，包含15个测试，并断言批量请求只调1次和按index重排序