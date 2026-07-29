---
created: '2026-07-29'
description: transcript_store.py 中的 try_claim_session 函数用于会话锁定和状态管理
id: transcript-store-claim-session
keywords:
- transcript_store
- claim_session
type: project
---

该函数位于 memory_lib/transcript_store.py，负责尝试声明会话，防止并发处理。函数签名包含 session_id, transcript_path, stale_after_seconds 参数，返回 cursor 或 None。测试文件在 tests/test_transcript_store.py。