---
confidence: 0.5
deprecated: false
domain: workflow
hit_count: 1
id: ask-before-breaking-change
last_seen: '2026-07-31'
scope: personal
trigger: 当需要修改现有配置或接口的兼容性时
---

## Action
先向用户提问确认是否接受破坏性变更，并给出推荐选项

## Evidence
AskUserQuestion 询问 DeepSeek base_url 是否改为可配置，以及 LLM_PROVIDER 选择机制设计