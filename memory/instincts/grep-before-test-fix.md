---
confidence: 0.5
deprecated: false
domain: testing
hit_count: 1
id: grep-before-test-fix
last_seen: '2026-07-30'
scope: personal
trigger: 修复测试失败时
---

## Action
先用 grep 查看失败测试的上下文和辅助函数定义，再修改

## Evidence
使用 rtk grep 查看失败测试内容及辅助函数定义，然后编辑 test_transcript.py