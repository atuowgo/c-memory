---
confidence: 0.5
deprecated: false
domain: ''
hit_count: 1
id: edit-then-test-pattern
last_seen: '2026-07-29'
scope: personal
trigger: 完成一系列编辑修改后，执行构建和测试验证
---

## Action
编辑完成后立即运行构建脚本和测试，确保修改正确且无回归

## Evidence
在 9 次编辑后，执行了 rm -rf dist && ./build.sh 重新构建，并端到端实测通过