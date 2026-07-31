---
confidence: 0.5
deprecated: false
domain: workflow
hit_count: 1
id: avoid-unnecessary-dependencies
last_seen: '2026-07-31'
scope: personal
trigger: 多个脚本需要协同工作时，考虑执行顺序依赖
---

## Action
尽量让脚本独立运行，不建立执行顺序依赖，以降低耦合和失败风险

## Evidence
用户强调两个脚本各自独立读写不同文件，不建立执行顺序依赖，避免因顺序问题导致功能不可用。