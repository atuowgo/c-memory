---
created: '2026-07-29'
description: 用户倾向于使用单一数据源（transcript_path解析）而非双钩子方案，并接受格式变化风险
id: user-preference-single-source
keywords:
- data-source
- preference
type: feedback
---

在对比transcript_path解析和UserPromptSubmit+last_assistant_message双钩子方案后，用户更推荐transcript_path解析方案，因为单一数据源能获取完整对话和工具调用细节，尽管格式无官方文档保证。用户表示'出问题算实现阶段的风险，到时候再兜底'。