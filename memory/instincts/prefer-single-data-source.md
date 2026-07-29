---
confidence: 0.5
deprecated: false
domain: workflow
hit_count: 1
id: prefer-single-data-source
last_seen: '2026-07-29'
scope: personal
trigger: 当需要从多个数据源中做选择时，倾向于选择单一数据源方案，即使该方案存在兼容性风险
---

## Action
优先评估单一数据源方案的可行性和风险，如果风险可控则推荐采用，同时建议增加格式变化时的兜底机制

## Evidence
用户分析了transcript_path解析和双钩子两种方案后，明确表示'单一数据源就能拿到完整对话+工具细节'，并倾向于方案1，同时主动提出'出问题算实现阶段的风险，到时候再兜底'