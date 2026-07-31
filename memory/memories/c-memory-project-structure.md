---
created: '2026-07-31'
description: c-memory 项目的 hooks/inject.py 现在输出 JSON 格式，包含 systemMessage 和 hookSpecificOutput.additionalContext。
id: c-memory-project-structure
keywords:
- c-memory
- hooks
- JSON
type: project
---

在 SessionStart hook 中，inject.py 输出 JSON，其中 systemMessage 是用户可见的高亮摘要，仅在真正有内容注入时输出；additionalContext 包含给 Claude 的上下文，与之前纯 stdout 内容一致。此改动不影响召回逻辑。