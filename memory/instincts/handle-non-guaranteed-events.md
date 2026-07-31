---
confidence: 0.5
deprecated: false
domain: workflow
hit_count: 1
id: handle-non-guaranteed-events
last_seen: '2026-07-31'
scope: personal
trigger: 依赖的事件（如SessionEnd）可能不触发（如crash/kill）
---

## Action
明确记录已知限制，并接受数据可能不是最新的事实，保证功能在大多数情况下可用即可

## Evidence
用户指出SessionEnd不保证在crash/kill时触发，并认为与现有project-summary.md的限制一致，接受这一限制。