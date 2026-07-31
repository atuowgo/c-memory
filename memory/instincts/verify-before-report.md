---
confidence: 0.55
deprecated: false
domain: testing
hit_count: 2
id: verify-before-report
last_seen: '2026-07-31'
scope: personal
trigger: 完成代码实现后，在向用户汇报前进行验证
---

## Action
运行相关测试并检查关键实现细节，确保所有功能正确无误后再汇报

## Evidence
会话中多次使用 Bash 运行 pytest 和 sed 查看实现代码，确认测试全部通过后才汇报