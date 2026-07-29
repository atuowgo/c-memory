---
confidence: 0.5
deprecated: false
domain: code-style
hit_count: 1
id: align-to-open-source-format
last_seen: '2026-07-29'
scope: personal
trigger: 发现本地实现与得物开源实现的 prompt 字段结构不一致
---

## Action
全面修改所有相关文件（llm.py, detectors.py, extract.py, dedup.py, storage.py, inject.py 及测试文件）以对齐字段名和格式

## Evidence
本次会话中，根据 curl 得物源码确认字段结构后，修改了 7 个源文件和 3 个测试文件，并运行 pytest 确认全部通过