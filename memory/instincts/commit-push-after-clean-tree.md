---
confidence: 0.6000000000000001
deprecated: false
domain: workflow
hit_count: 3
id: commit-push-after-clean-tree
last_seen: '2026-07-31'
scope: personal
trigger: 完成代码或文档修改后，准备提交前
---

## Action
运行测试套件确认所有测试通过，并检查改动范围是否只涉及预期文件，再决定是否提交

## Evidence
最后一轮对话提到113个测试全绿，改动只涉及docs/c-memory-overview.html，询问是否commit并push，表明有验证后提交的习惯