---
created: '2026-07-31'
description: memory_lib 支持通过 EMBEDDING_PROVIDER 环境变量选择 embedding 提供方
id: llm-provider-config-structure
keywords:
- embedding
- provider
type: project
---

在 memory_lib/providers/__init__.py 中，get_embedding_provider() 根据 EMBEDDING_PROVIDER 显式选型，支持 ark 和 openai 等。OpenAIProvider 在 embedding 侧被重命名为 EmbeddingOpenAIProvider 以避免与 LLM 侧冲突。