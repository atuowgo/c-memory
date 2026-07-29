---
created: '2026-07-29'
description: 运行时数据文件（.sqlite3, .json）被 .gitignore 忽略
id: runtime-files-in-gitignore
keywords:
- gitignore
- runtime
type: project
---

项目 .gitignore 中配置了 memory/.observations.sqlite3, memory/.dedup_state.json, memory/.vector_cache.sqlite3, memory/.transcript_progress.sqlite3 等运行时文件，避免提交。