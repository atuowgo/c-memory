---
confidence: 0.6500000000000001
deprecated: false
domain: workflow
hit_count: 4
id: check-sensitive-files-before-commit
last_seen: '2026-07-31'
scope: personal
trigger: 在提交前暂存文件时，检查是否存在敏感文件（如.env、.sqlite3）或应忽略的文件
---

## Action
在git add之后，使用git status检查敏感文件，确保它们不会被提交

## Evidence
执行了`rtk git add -A && rtk git status --short | grep -iE "\.env$|\.sqlite3$|recent-sessions"; echo check-done`