---
confidence: 0.5
deprecated: false
domain: workflow
hit_count: 1
id: read-config-before-edit
last_seen: '2026-07-31'
scope: personal
trigger: 在修改配置文件或环境变量示例前
---

## Action
先读取现有配置文件（如 .env.example）以核对内容

## Evidence
使用 rtk read 读取 .env.example 以核对更新后的内容