---
created: '2026-07-31'
description: 本地状态文件（如session_id相关文件）不应提交到git，因为只在本机有意义
id: local-state-files-not-in-git
keywords:
- gitignore
- local-state
type: workflow
---

本地状态文件（如.dedup_state.json、sqlite状态文件、以及新设计的memory/.recent-sessions.json）只在本机有意义，不应提交到git。需要在.gitignore中补充相应条目。