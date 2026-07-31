---
confidence: 0.55
deprecated: false
domain: workflow
hit_count: 2
id: commit-push-after-clean-tree
last_seen: '2026-07-31'
scope: personal
trigger: 完成代码修改后，准备提交前
---

## Action
运行相关测试并检查文件状态，确保所有测试通过且无意外文件污染，再询问是否提交

## Evidence
会话中多次运行测试（pytest tests/test_record_session.py -q 和 pytest tests/ -q），检查 git status 和 memory/ 目录，最后确认 113 个测试全绿后才询问是否 commit