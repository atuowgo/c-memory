---
created: '2026-07-31'
description: .env 环境变量已从旧的 DeepSeek 专属配置迁移为多 Provider 通用配置
id: env-config-migration
keywords:
- env
- migration
type: workflow
---

迁移后 .env 键名已更新，支持 LLM_PROVIDER、各 Provider 的 model/base_url/api_key 等变量。迁移过程中确保密钥值不打印，只验证键名存在。README 和 .env.example 已同步更新。