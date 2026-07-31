---
created: '2026-07-31'
description: 项目使用 SessionEnd hook，其中第 1 条命令是 summarize.py，第 2 条是 record_session.py
id: session-hook-architecture
keywords:
- hook
- session
type: project
---

hooks/record_session.py 被挂到 SessionEnd 的第 2 条命令，第 1 条是 summarize.py。该 hook 用于记录最近 10 次会话的 session_id 等信息。