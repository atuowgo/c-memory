---
confidence: 0.6000000000000001
deprecated: false
domain: workflow
hit_count: 3
id: read-before-write-pattern
last_seen: '2026-07-30'
scope: personal
trigger: 修改代码前先读取相关文件内容
---

## Action
在编辑文件前，先读取文件内容以了解上下文

## Evidence
会话中有5次Read操作，且集中在编辑前读取测试文件和源文件