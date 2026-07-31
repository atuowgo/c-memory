---
created: '2026-07-31'
description: c-memory 项目的 hooks/inject.py 中预览截断长度由 24 字符改为其他值，并同步更新了文档。
id: c-memory-hooks-inject-preview-limit
keywords:
- c-memory
- inject.py
- preview
type: project
---

在本次会话中，修改了 hooks/inject.py 中的 _PREVIEW_MAX_CHARS 常量（原为 24），并更新了 docs/c-memory-overview.html 中关于截断预览的措辞。项目使用 Python 虚拟环境（.venv）运行测试，测试数量为 113 个。