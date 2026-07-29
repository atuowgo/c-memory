---
created: '2026-07-29'
description: instincts 和 project_facts 的字段结构已与得物开源实现对齐
id: memory-field-structure-aligned-to-dewu
keywords:
- field-structure
- dewu
type: project
---

instincts 使用 id/trigger/action/domain/evidence 字段，project_facts 使用 name/description/body/type/keywords 字段。keywords 是本地额外添加用于去重的字段。id/name 由 LLM 直接生成英文 kebab-case，不再依赖本地 _slugify 转换。