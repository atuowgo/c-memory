---
created: '2026-07-30'
description: Claude Code hook 支持 systemMessage 字段向用户推送提示
id: system-message-field-in-hook
keywords:
- hook
- systemMessage
type: project
---

在 Stop hook 的 JSON 输出中，顶层 systemMessage 字段的内容会显示在聊天界面中，用于给用户推送提示。普通 stdout 在 Stop 场景下用户看不到。