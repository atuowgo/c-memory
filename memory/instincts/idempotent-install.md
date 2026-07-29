---
confidence: 0.5
deprecated: false
domain: workflow
hit_count: 1
id: idempotent-install
last_seen: '2026-07-29'
scope: personal
trigger: 设计安装脚本时
---

## Action
确保重复执行不会产生重复条目或破坏已有配置

## Evidence
merge_settings.py 中检查完全相同的组不重复追加，三轮实测验证重复执行无重复条目