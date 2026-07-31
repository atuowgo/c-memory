---
created: '2026-07-31'
description: SessionEnd钩子不保证在crash/kill时触发，因此依赖它的功能可能丢失最后一次会话数据
id: session-end-hook-not-guaranteed
keywords:
- SessionEnd
- crash
- limitation
type: error
---

SessionEnd钩子在正常退出时触发，但在crash或kill时可能不触发。因此，基于SessionEnd的功能（如记录最近会话）可能无法记录最后一次异常退出的会话。这与现有project-summary.md的限制一致，设计时需接受这一限制。