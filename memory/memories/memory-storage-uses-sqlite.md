---
created: '2026-07-31'
description: 记忆存储使用 SQLite 数据库，并有去重状态文件
id: memory-storage-uses-sqlite
keywords:
- sqlite
- memory
- dedup
type: project
---

从 .gitignore 中看到 memory/.*.sqlite3 和 memory/.dedup_state.json，说明记忆数据存储在 SQLite 中，并使用 .dedup_state.json 进行去重状态管理。