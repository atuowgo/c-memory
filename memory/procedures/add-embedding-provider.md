---
confidence: 0.55
evidence_sessions:
- 32bcf8c6-1ce2-4421-8286-1ff5071fb8a8
first_seen: '2026-07-31'
hit_count: 1
id: add-embedding-provider
last_seen: '2026-07-31'
skill_asked: false
status: candidate
task_type: 为项目新增一个 embedding provider 并改造选型机制
---

## 步骤
1. 读取现有 embedding provider 实现
2. 询问用户选择新增哪个 provider 及选型机制
3. 编写设计文档
4. 创建并启动并行子任务（实现、文档、测试）
5. 修改 embedding.py 新增 OpenAIProvider
6. 修改 __init__.py 选型逻辑
7. 更新 .env.example 和 README.md
8. 运行测试验证
9. 同步本地 .env 配置

## 说明
该流程与之前 LLM Provider 改造结构一致，属于可复用的多步骤开发流程