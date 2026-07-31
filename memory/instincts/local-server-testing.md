---
confidence: 0.5
deprecated: false
domain: testing
hit_count: 1
id: local-server-testing
last_seen: '2026-07-31'
scope: personal
trigger: 修改HTML或前端文件后，需要验证渲染效果
---

## Action
启动本地HTTP服务器，使用浏览器工具（如claude-in-chrome）导航到页面，并通过JavaScript检查DOM元素和字符集等

## Evidence
多次使用Bash启动http.server，并用claude-in-chrome的navigate和javascript_tool检查页面，如检查mermaid SVG数量、字符集等