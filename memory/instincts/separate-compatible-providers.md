---
confidence: 0.5
deprecated: false
domain: code-style
hit_count: 1
id: separate-compatible-providers
last_seen: '2026-07-31'
scope: personal
trigger: 当多个提供商共享相似 API 但存在差异时
---

## Action
提取公共基类，让具体提供商继承并覆盖差异部分，保持代码简洁

## Evidence
新增 _OpenAICompatibleProvider 基类，DeepSeekProvider 瘦身为薄子类，AnthropicProvider 独立实现