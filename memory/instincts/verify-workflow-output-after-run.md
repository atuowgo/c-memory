---
confidence: 0.5
deprecated: false
domain: workflow
hit_count: 1
id: verify-workflow-output-after-run
last_seen: '2026-07-30'
scope: personal
trigger: 运行完一个端到端流程后，检查其输出产物（如文件、数据库记录）以确认流程真实执行
---

## Action
在流程执行后，列出相关目录文件或读取产物内容，验证流程是否产生预期结果

## Evidence
用户执行了 'rtk ls -la memory/procedures/ 2>/dev/null && echo --- && rtk read memory/procedures/*.md 2>/dev/null | head -50' 来检查流程挖掘功能产生的候选流程记录