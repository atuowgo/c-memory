---
created: '2026-07-31'
description: 本地测试HTTP服务器常用端口8791
id: local-http-server-port-8791
keywords:
- http-server
- port
- testing
type: workflow
---

在验证HTML文档时，使用python3 -m http.server 8791启动本地服务器，并通过http://127.0.0.1:8791/访问。测试后需停止服务器（pkill）。