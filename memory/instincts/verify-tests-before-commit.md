---
confidence: 0.5
deprecated: false
domain: testing
hit_count: 1
id: verify-tests-before-commit
last_seen: '2026-07-31'
scope: personal
trigger: 在提交代码前，用户会先运行测试套件确认无回归
---

## Action
在建议提交前，先运行测试并检查 git status，确保所有测试通过且改动符合预期

## Evidence
用户运行了 `pytest tests/ -q` 并检查了 `git status --short`，然后询问是否提交