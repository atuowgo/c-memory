---
created: '2026-07-29'
description: c-memory 使用 merge_settings.py 按事件维度合并 hooks 配置到目标项目
id: merge-settings-script
keywords:
- merge_settings
- hooks
- install
type: project
---

scripts/merge_settings.py 将 c-memory 的 5 个 hook 配置（PostToolUse, Stop×2, PreCompact, SessionEnd, SessionStart）追加到目标项目 .claude/settings.json 的对应事件列表末尾，保留目标项目已有的其他 hooks 和配置（如 permissions），并避免重复追加完全相同的组。install.sh 最后调用此脚本完成安装。