---
created: '2026-07-31'
description: 项目正在扩展 embedding provider 支持，新增 OpenAI 兼容 provider，并采用显式 EMBEDDING_PROVIDER
  选型机制
id: multi-llm-provider-design
keywords:
- embedding
- provider
- design
type: project
---

设计文档位于 docs/plans/2026-07-31-multi-embedding-provider-design.md，状态已确认待实现。实现涉及 embedding.py 新增 OpenAIProvider，选型机制与 LLM_PROVIDER 保持一致，显式指定 provider。