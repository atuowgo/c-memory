---
confidence: 0.5
deprecated: false
domain: workflow
hit_count: 1
id: parallel-subagent-launch
last_seen: '2026-07-29'
scope: personal
trigger: 需要实现多个独立模块时
---

## Action
并行启动多个子agent，每个负责一个模块的实现，并等待所有完成后再进行依赖检查

## Evidence
Phase 1的三个subagent（transcript.py、transcript_store.py、llm.py）被并行启动，且用户明确表示跑完核对结果再启动依赖的Phase 2