---
confidence: 0.5
deprecated: false
domain: workflow
hit_count: 1
id: clean-before-rebuild
last_seen: '2026-07-29'
scope: personal
trigger: 在修改核心数据存储结构或字段映射前，先清理旧数据文件
---

## Action
先执行 rm 清理旧 memory 文件（instincts/*.md, memories/*.md, .observations.sqlite3, .vector_cache.sqlite3, .dedup_state.json），再开始代码修改

## Evidence
本次会话中，在修改字段对齐前先执行了 rm 清理命令，然后才进行代码修改