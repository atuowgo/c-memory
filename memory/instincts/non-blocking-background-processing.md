---
confidence: 0.5
deprecated: false
domain: workflow
hit_count: 1
id: non-blocking-background-processing
last_seen: '2026-07-29'
scope: personal
trigger: 当检测到需要执行耗时任务（如LLM调用）但当前流程不应等待时
---

## Action
使用subprocess.Popen启动后台进程执行任务，当前流程继续使用已有数据，不阻塞用户操作

## Evidence
用户设计孤儿session补漏时，明确使用后台进程跑总结，不等结果直接注入当前project-summary.md。