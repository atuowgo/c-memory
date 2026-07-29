---
created: '2026-07-29'
description: 修复 macOS bash 3.2 下变量后紧跟全角中文标点导致 unbound variable 的 bug
id: bash-var-brace-fix
keywords:
- bash
- compatibility
type: error
---

在 install.sh 中，将 $VAR 后紧跟全角中文标点的写法改为 ${VAR}，避免 macOS 系统自带 bash 3.2（2007年老版本）解析错误。两轮冒烟测试通过。