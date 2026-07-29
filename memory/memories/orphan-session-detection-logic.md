---
created: '2026-07-29'
description: 孤儿session检测通过status和updated_at判断，无需额外标记字段
id: orphan-session-detection-logic
keywords:
- orphan
- session_progress
type: project
---

扫描session_progress表中status='processing'且updated_at早于当前时间减去stale_after_seconds（默认600秒）的行，即为孤儿session。该设计利用第三节中未达阈值不release的机制，天然识别出卡在processing超过10分钟的session。