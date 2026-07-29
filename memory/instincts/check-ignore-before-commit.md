---
confidence: 0.5
deprecated: false
domain: git
hit_count: 1
id: check-ignore-before-commit
last_seen: '2026-07-29'
scope: personal
trigger: 提交前检查 .gitignore 是否覆盖了运行时文件
---

## Action
使用 git check-ignore -v 验证文件是否被忽略

## Evidence
工具调用中使用了 for 循环和 git check-ignore -v 检查多个 .sqlite3 和 .json 文件