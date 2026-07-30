---
confidence: 0.5
deprecated: false
domain: testing
hit_count: 1
id: test-with-stdin-input
last_seen: '2026-07-30'
scope: personal
trigger: 测试处理stdin输入的脚本
---

## Action
使用echo管道模拟stdin输入并检查退出码

## Evidence
使用echo和管道测试mine_procedures.py的stdin输入处理，并检查exit code。