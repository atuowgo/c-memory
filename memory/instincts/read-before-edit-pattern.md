---
confidence: 0.6500000000000001
deprecated: false
domain: workflow
hit_count: 4
id: read-before-edit-pattern
last_seen: '2026-07-29'
scope: personal
trigger: 编辑文件前
---

## Action
先读取文件内容或使用grep搜索相关代码，确保理解上下文后再修改

## Evidence
多次使用rtk read和rtk grep命令查看文件内容后再执行Edit操作