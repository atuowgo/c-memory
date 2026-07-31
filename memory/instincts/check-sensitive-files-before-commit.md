---
confidence: 0.55
deprecated: false
domain: git
hit_count: 2
id: check-sensitive-files-before-commit
last_seen: '2026-07-30'
scope: personal
trigger: 执行 git add 后、提交前
---

## Action
检查暂存区是否包含 .env 或 .sqlite3 等敏感文件

## Evidence
使用 grep -iE '\.env$|\.sqlite3$' 检查敏感文件