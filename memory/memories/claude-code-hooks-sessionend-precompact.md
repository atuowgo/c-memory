---
created: '2026-07-29'
description: Claude Code的SessionEnd钩子不保证异常退出时触发，PreCompact钩子是内容丢弃的天然触发点
id: claude-code-hooks-sessionend-precompact
keywords:
- hooks
- sessionend
- precompact
type: project
---

SessionEnd钩子有clear/resume/logout/prompt_input_exit/bypass_permissions_disabled/other几种matcher，但官方文档未承诺在异常退出（crash/kill -9）时触发，只覆盖正常终止路径。PreCompact钩子在/compact手动触发或上下文超限自动触发前触发，是内容即将被丢弃的另一个天然触发点。Stop钩子自带last_assistant_message（每轮最终回复文本），但不含用户消息文本，要拿到完整对话内容需解析transcript_path。