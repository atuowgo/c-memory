---
confidence: 0.5
deprecated: false
domain: testing
hit_count: 1
id: write-tests-before-verification
last_seen: '2026-07-31'
scope: personal
trigger: 当需要验证代码逻辑或修改功能时
---

## Action
先编写或更新单元测试，再运行测试验证

## Evidence
会话中先 Write 了 test_llm_providers.py，随后运行 pytest 进行验证