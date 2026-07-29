---
created: '2026-07-29'
description: session_progress表需加transcript_path列用于孤儿session补漏
id: session-progress-table-schema
keywords:
- session_progress
- transcript_path
type: project
---

在session_progress表中增加transcript_path TEXT列，try_claim_session第一次认领session时记录该session对应的transcript文件路径，后续补漏时通过该路径读取transcript内容。