---
created: '2026-07-31'
description: DeepSeekProvider 的 base_url 已从硬编码改为可配置，与其他 Provider 保持一致
id: deepseek-base-url-configurable
keywords:
- deepseek
- config
type: feedback
---

用户确认将 DeepSeek 的 base_url 改为可配置，通过环境变量注入，避免硬编码。这提高了配置灵活性，并统一了所有 Provider 的配置方式。