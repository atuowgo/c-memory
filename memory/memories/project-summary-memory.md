---
created: '2026-07-29'
description: 项目通过 hooks/summarize.py 将对话滚动总结注入 memory/project-summary.md
id: project-summary-memory
keywords:
- summarize
- project-summary
type: project
---

在 Stop / PreCompact / SessionEnd 钩子中调用 summarize.py，将新增对话内容总结后追加到 project-summary.md，实现情景记忆的持久化。该文件位于 hooks/summarize.py，由 inject.py 负责孤儿扫描和总结注入。