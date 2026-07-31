---
confidence: 0.7000000000000002
deprecated: false
domain: testing
hit_count: 5
id: test-after-write-pattern
last_seen: '2026-07-31'
scope: personal
trigger: 完成代码修改后
---

## Action
运行测试套件（如 pytest）以验证修改无回归，并可能进行冒烟测试。

## Evidence
编辑后执行了 Bash 命令运行 pytest 全量测试，并进行了冒烟测试。