---
created: '2026-07-29'
description: Claude Code会话transcript文件格式：JSONL，每条记录包含type和message字段，用户输入和工具结果均标记为type:user，通过message.content类型区分
id: transcript-jsonl-format
keywords:
- transcript
- jsonl
- format
type: project
---

transcript文件位于~/.claude/projects/<project-path>/<session-id>.jsonl，格式为JSONL。每条记录有type和message字段。用户原始输入：message.content为纯字符串；工具调用结果：message.content为数组，第一个元素type为tool_result。此格式无官方文档保证，可能随Claude Code升级变化。