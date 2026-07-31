---
confidence: 0.5
deprecated: false
domain: workflow
hit_count: 1
id: explicit-provider-selection
last_seen: '2026-07-31'
scope: personal
trigger: 当存在多个 LLM 提供商时，需要选择使用哪个
---

## Action
通过环境变量显式指定提供商，并在未设置或无效时降级到 NullProvider，避免隐式默认

## Evidence
修改 get_llm_provider() 为按 LLM_PROVIDER 显式选型，并处理降级