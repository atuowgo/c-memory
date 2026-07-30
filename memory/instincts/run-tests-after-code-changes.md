---
confidence: 0.5
deprecated: false
domain: testing
hit_count: 1
id: run-tests-after-code-changes
last_seen: '2026-07-30'
scope: personal
trigger: 修改或新增测试文件后
---

## Action
运行相关测试以验证变更正确性

## Evidence
创建 test_mine_procedures.py 和 test_notify_pending_procedures.py 后，运行了 pytest tests/test_procedure_store.py 和 tests/ 下的全部测试。