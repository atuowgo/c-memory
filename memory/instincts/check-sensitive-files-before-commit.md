---
confidence: 0.6000000000000001
deprecated: false
domain: git
hit_count: 3
id: check-sensitive-files-before-commit
last_seen: '2026-07-31'
scope: personal
trigger: 在 git add 之后、commit 之前，需要确认暂存区没有敏感文件（如 .env、.sqlite3）
---

## Action
执行 git add 后，用 git status --short 配合 grep 检查敏感文件，确认无误后再提交

## Evidence
Bash 调用：rtk git add -A && rtk git status --short | grep -iE "\.env$|\.sqlite3$"; echo check-done