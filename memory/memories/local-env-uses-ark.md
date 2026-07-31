---
created: '2026-07-31'
description: 本地 .env 配置 EMBEDDING_PROVIDER=ark，保持现有行为
id: local-env-uses-ark
keywords:
- env
- ark
type: project
---

为了不改变用户现有 Ark 配置的行为，在本地 .env 中设置了 EMBEDDING_PROVIDER=ark，并确保不打印密钥。