---
created: '2026-07-29'
description: try_claim_session返回(claimed, cursor)元组以区分不同场景
id: try-claim-session-return-tuple
keywords:
- try-claim-session
- bug-fix
type: error
---

修复了try_claim_session对全新session和锁被占用都返回None的bug，改为返回(claimed: bool, cursor: str | None)元组，调用方据此判断是处理还是跳过。