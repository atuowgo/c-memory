---
created: '2026-07-31'
description: Anthropic API 与 OpenAI 兼容 API 在请求头、参数和响应解析上完全不同
id: anthropic-api-differences
keywords:
- anthropic
- api
- differences
type: project
---

Anthropic 使用 x-api-key 和 anthropic-version 请求头，system 作为顶层参数，max_tokens 必填，响应解析 content[0].text。而 OpenAI 兼容 API 使用 Authorization 头，messages 数组，响应解析 choices[0].message.content。