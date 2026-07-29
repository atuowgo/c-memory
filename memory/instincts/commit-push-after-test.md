---
confidence: 0.5
deprecated: false
domain: workflow
hit_count: 1
id: commit-push-after-test
last_seen: '2026-07-29'
scope: personal
trigger: 运行测试通过后，执行 git add -A 并提交推送
---

## Action
在测试通过后自动执行 git add -A、git commit 和 git push，保持工作树干净

## Evidence
观测记录显示：运行 pytest 后立即执行 git add -A 和 git status --short，且最终提交推送完成，工作树干净