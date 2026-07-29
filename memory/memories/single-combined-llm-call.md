---
created: '2026-07-29'
description: 保留单次组合 LLM 调用，未拆分为两次独立调用
id: single-combined-llm-call
keywords:
- llm-call
- design-decision
type: project
---

与得物原版不同，本地实现将 instincts 和 project_facts 的提取合并为一次 LLM 调用，而非两次独立调用。这是有意保留的设计决策。