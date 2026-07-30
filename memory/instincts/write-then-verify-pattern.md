---
confidence: 0.5
deprecated: false
domain: testing
hit_count: 1
id: write-then-verify-pattern
last_seen: '2026-07-30'
scope: personal
trigger: 写入新文件后立即进行导入验证
---

## Action
在写入新文件后，应运行导入测试或简单功能测试以确保文件可被正确加载

## Evidence
写入 procedure_store.py 后，立即执行 Bash 命令 'from memory_lib import procedure_store; print("import ok")' 验证导入