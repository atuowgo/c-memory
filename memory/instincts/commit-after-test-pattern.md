---
confidence: 0.5
deprecated: false
domain: workflow
hit_count: 1
id: commit-after-test-pattern
last_seen: '2026-07-29'
scope: personal
trigger: 完成测试验证后
---

## Action
执行 git add -A 和 git commit，确保工作树干净

## Evidence
工具调用显示：运行 pytest 后立即执行 git add -A 和 git status，最终提交并保持工作树干净