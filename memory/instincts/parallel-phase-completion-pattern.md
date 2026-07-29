---
confidence: 0.5
deprecated: false
domain: workflow
hit_count: 1
id: parallel-phase-completion-pattern
last_seen: '2026-07-29'
scope: personal
trigger: 多个并行子任务（如 Phase 1A/1B/1C）完成后，等待所有子任务完成再启动下一阶段
---

## Action
在启动下一阶段前，检查所有并行子任务的状态，确保全部完成

## Evidence
Phase 1B 完成后，明确等待 Phase 1A 和 Phase 1C 完成通知后再启动 Phase 2