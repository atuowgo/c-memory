---
confidence: 0.7000000000000002
deprecated: false
domain: git
hit_count: 5
id: check-sensitive-files-before-commit
last_seen: '2026-07-31'
scope: personal
trigger: 在 git add 之后、commit 之前，检查暂存区是否包含敏感文件（如 .env、.sqlite3）
---

## Action
执行 git status --short 并 grep 敏感文件模式，确认无敏感文件后再提交

## Evidence
命令：rtk git add -A && rtk git status --short | grep -iE "\.env$|\.sqlite3$"; echo check-done