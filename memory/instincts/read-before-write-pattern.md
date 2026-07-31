---
confidence: 0.6500000000000001
deprecated: false
domain: workflow
hit_count: 4
id: read-before-write-pattern
last_seen: '2026-07-31'
scope: personal
trigger: 在修改文件之前，先读取相关文件内容以了解上下文
---

## Action
在编辑文件前，先使用 Read 工具读取目标文件，确保修改基于准确理解

## Evidence
会话中先读取了 build.sh 和 install.sh，然后才进行编辑