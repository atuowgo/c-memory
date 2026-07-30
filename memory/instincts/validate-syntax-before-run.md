---
confidence: 0.5
deprecated: false
domain: workflow
hit_count: 1
id: validate-syntax-before-run
last_seen: '2026-07-30'
scope: personal
trigger: 运行Python脚本前
---

## Action
先使用ast.parse检查语法正确性

## Evidence
在运行mine_procedures.py之前，先执行了ast.parse检查。