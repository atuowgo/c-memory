---
created: '2026-07-30'
description: LLM 提供者遵循统一接口，包含 DeepSeekProvider 和 NullProvider
id: llm-provider-interface
keywords:
- llm provider
type: project
---

providers/llm.py 定义了 LLMProvider 基类，DeepSeekProvider 和 NullProvider 继承自该类，NullProvider 用于测试