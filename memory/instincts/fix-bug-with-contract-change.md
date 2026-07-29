---
confidence: 0.5
deprecated: false
domain: code-style
hit_count: 1
id: fix-bug-with-contract-change
last_seen: '2026-07-29'
scope: personal
trigger: 发现函数返回值无法区分多种场景时
---

## Action
修改返回值契约为元组或枚举，同步更新所有调用方和测试

## Evidence
发现try_claim_session对两种场景都返回None，改为(claimed, cursor)元组并同步修改transcript_store.py、测试和summarize.py