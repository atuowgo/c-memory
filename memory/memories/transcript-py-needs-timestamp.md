---
created: '2026-07-30'
description: transcript.py 的轮次解析目前不带时间戳，需要小改动补上
id: transcript-py-needs-timestamp
keywords:
- transcript
- timestamp
type: project
---

为了按时间区间从 observations 表捞取工具调用序列，需要 transcript.py 在解析用户轮次时附带时间戳字段。