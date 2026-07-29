---
created: '2026-07-29'
description: 孤儿session补总结使用后台进程，不阻塞当前会话启动
id: non-blocking-background-summarization
keywords:
- background
- summarize
type: workflow
---

在inject.py读取project-summary.md注入前，检测到孤儿session时使用subprocess.Popen启动后台进程运行summarize.py（mode=force），数据源为孤儿session的transcript文件。当前会话直接注入已有的project-summary.md，后台补完的总结写入文件后，下次会话可见。