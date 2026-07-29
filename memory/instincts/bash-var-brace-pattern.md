---
confidence: 0.5
deprecated: false
domain: code-style
hit_count: 1
id: bash-var-brace-pattern
last_seen: '2026-07-29'
scope: personal
trigger: 在 bash 脚本中使用变量后紧跟全角中文标点
---

## Action
使用 ${VAR} 大括号写法代替 $VAR，避免 macOS 系统自带 bash 3.2 解析错误

## Evidence
修复了 macOS bash 3.2 下 $VAR 后紧跟全角中文标点导致 unbound variable 的 bug，改用 ${VAR} 写法