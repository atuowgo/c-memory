---
confidence: 0.5
deprecated: false
domain: testing
hit_count: 1
id: full-test-suite-validation
last_seen: '2026-07-30'
scope: personal
trigger: 完成一组代码变更后，用户会运行全量测试套件验证
---

## Action
在完成多文件修改后，建议运行全量测试套件确认无回归

## Evidence
用户运行了全量 pytest 并报告 103 个测试通过