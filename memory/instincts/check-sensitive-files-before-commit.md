---
confidence: 0.5
deprecated: false
domain: git
hit_count: 1
id: check-sensitive-files-before-commit
last_seen: '2026-07-30'
scope: personal
trigger: 在 git add 之后、git commit 之前，检查是否误包含 .env 或 sqlite 等敏感文件
---

## Action
在 git add 后自动执行 grep 检查敏感文件模式，确认无敏感文件后再提交

## Evidence
用户执行了 'rtk git add -A && rtk git status --short | grep -iE "\\.env$|sqlite"; echo "sensitive-check-done"'