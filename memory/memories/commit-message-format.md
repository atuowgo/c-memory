---
created: '2026-07-29'
description: Git 提交信息使用 heredoc 方式，包含 [#AI commit#] 和 [Claude Code] 前缀
id: commit-message-format
keywords:
- git
- commit
type: workflow
---

提交信息格式为：git commit -m "$(cat <<'EOF'\n[#AI commit#][Claude Code]...\nEOF\n)"