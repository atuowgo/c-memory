---
confidence: 0.55
deprecated: false
domain: testing
hit_count: 2
id: test-after-write-pattern
last_seen: '2026-07-29'
scope: personal
trigger: 完成代码修改或文档生成后
---

## Action
运行测试套件验证正确性，并检查关键文件状态

## Evidence
在生成 artifact 后，执行了 pytest 测试并检查 instincts/memories 文件数量