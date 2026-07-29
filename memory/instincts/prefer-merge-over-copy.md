---
confidence: 0.5
deprecated: false
domain: workflow
hit_count: 1
id: prefer-merge-over-copy
last_seen: '2026-07-29'
scope: personal
trigger: 需要将模板配置安装到目标项目时
---

## Action
编写合并脚本而非直接覆盖，保留目标项目已有配置，按事件维度追加而非替换

## Evidence
将 .claude/settings.json 改为 dist/settings.template.json，新增 merge_settings.py 做事件级合并，install.sh 最后调用合并脚本