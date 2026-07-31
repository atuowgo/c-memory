---
confidence: 0.5
deprecated: false
domain: workflow
hit_count: 1
id: search-docs-before-edit
last_seen: '2026-07-31'
scope: personal
trigger: 修改文档中涉及具体描述或措辞时
---

## Action
先用 grep 等工具搜索相关关键词，定位需要修改的位置，再进行编辑

## Evidence
工具调用摘要中有一条 Bash 命令：rtk grep -n "截断到 24 字符\|每条截断" docs/c-memory-overview.html，用于定位文档中旧措辞，随后进行了 Edit 操作。