---
confidence: 0.9
deprecated: false
domain: workflow
hit_count: 10
id: read-before-edit-pattern
last_seen: '2026-07-30'
scope: personal
trigger: 用户在执行代码变更前，先通过 Read 工具核实代码内容，而不是仅依赖子代理报告
---

## Action
在建议修改代码前，先主动读取相关文件内容，确保理解当前状态

## Evidence
用户明确说'每一步都经过我本人 Read 实际代码核实（不只看子代理报告）'，且会话中有 Read 操作记录