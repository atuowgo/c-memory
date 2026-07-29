---
confidence: 0.5
deprecated: false
domain: testing
hit_count: 1
id: test-after-write-pattern
last_seen: '2026-07-29'
scope: personal
trigger: 编写或修改代码文件后
---

## Action
立即运行相关测试验证变更正确性

## Evidence
每次 Write 或 Edit 后都执行了 pytest 测试（如 test_transcript_store.py、test_transcript.py、全量测试）