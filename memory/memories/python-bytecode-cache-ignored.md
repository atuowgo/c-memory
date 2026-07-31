---
created: '2026-07-31'
description: Python 字节码缓存目录 __pycache__ 和 *.pyc 文件应被 .gitignore 忽略
id: python-bytecode-cache-ignored
keywords:
- python
- gitignore
- bytecode
type: error
---

由于 hooks/ 和 memory_lib/ 中的 .py 文件会被 Python 导入执行，自动生成 __pycache__ 目录和 .pyc 文件，这些不应被提交，因此 .gitignore 中加入了 __pycache__/ 和 *.pyc。