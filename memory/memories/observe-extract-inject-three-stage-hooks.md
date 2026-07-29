---
created: '2026-07-29'
description: 项目使用observe.py/extract.py/inject.py三段式钩子架构
id: observe-extract-inject-three-stage-hooks
keywords:
- hooks
- architecture
type: project
---

当前项目已经实现了三段式钩子架构：observe.py负责记录工具调用观测，extract.py负责提取，inject.py负责注入。这是已有的基础设施，可以复用。