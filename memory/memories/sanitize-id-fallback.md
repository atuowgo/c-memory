---
created: '2026-07-29'
description: extract.py 中新增 _sanitize_id 函数处理 id 合法性
id: sanitize-id-fallback
keywords:
- id-sanitization
- extract
type: project
---

优先信任 LLM/检测器给出的 id，若合法（英文 kebab-case）则直接使用；若不合法则回退到本地 _slugify 生成。这解决了 LLM 未遵守指令时 id 可能为中文的问题。