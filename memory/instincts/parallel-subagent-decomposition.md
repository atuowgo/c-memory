---
confidence: 0.55
deprecated: false
domain: workflow
hit_count: 2
id: parallel-subagent-decomposition
last_seen: '2026-07-31'
scope: personal
trigger: 当任务包含多个独立模块（如代码实现、文档更新、测试编写）时
---

## Action
将任务拆分为并行子任务，分别委派给 subagent 执行，以提高效率

## Evidence
TaskCreate 创建了三个并行子任务，并分别通过 Agent 调用执行