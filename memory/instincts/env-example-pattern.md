---
confidence: 0.5
deprecated: false
domain: project-context
hit_count: 1
id: env-example-pattern
last_seen: '2026-07-29'
scope: personal
trigger: 项目需要配置环境变量
---

## Action
创建 .env.example 文件，列出所有可选环境变量及其说明，避免将真实 .env 纳入版本控制

## Evidence
新建了 .env.example，包含 DEEPSEEK_API_KEY、LLM_MODEL、ARK_API_KEY、ARK_EMBEDDING_BASE_URL、ARK_EMBEDDING_MODEL、ARK_EMBEDDING_DIM 等变量