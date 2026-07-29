---
confidence: 0.5
deprecated: false
domain: workflow
hit_count: 1
id: grep-before-edit-pattern
last_seen: '2026-07-29'
scope: personal
trigger: 需要修改某个字符串或路径时，先使用 grep 搜索所有出现位置
---

## Action
在编辑前先用 grep 搜索目标字符串，确保全面了解所有引用点，避免遗漏

## Evidence
在修改 build.sh 中 'c-memory' 为 '.c-memory' 前，执行了两次 rtk grep 搜索 PACKAGE_NAME 和 c-memory