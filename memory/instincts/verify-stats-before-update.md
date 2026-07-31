---
confidence: 0.5
deprecated: false
domain: workflow
hit_count: 1
id: verify-stats-before-update
last_seen: '2026-07-31'
scope: personal
trigger: 更新文档中的统计数字或状态信息时
---

## Action
先运行命令获取真实数据（如 rtk ls、grep 计数），再写入文档，避免使用过时或估算值

## Evidence
会话中多次运行 Bash 命令统计 instincts/memories/procedure 数量、测试数量，并在最终回复中明确使用实测值（77 instincts / 99 memories / 113 单测全绿）