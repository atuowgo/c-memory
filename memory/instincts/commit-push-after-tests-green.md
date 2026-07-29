---
confidence: 0.5
deprecated: false
domain: workflow
hit_count: 1
id: commit-push-after-tests-green
last_seen: '2026-07-29'
scope: personal
trigger: 测试全部通过后
---

## Action
自动执行 git add、commit 和 push，确保代码同步到远端

## Evidence
本次会话中，在测试全绿后立即执行了 git add -A、git commit 和 git push，最终 main 已同步到远端（834ce51..4e4b0cf），工作树干净。