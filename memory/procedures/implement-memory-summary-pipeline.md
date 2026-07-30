---
confidence: 0.5
evidence_sessions:
- 32bcf8c6-1ce2-4421-8286-1ff5071fb8a8
first_seen: '2026-07-30'
hit_count: 1
id: implement-memory-summary-pipeline
last_seen: '2026-07-30'
skill_asked: false
status: candidate
task_type: 实现记忆系统的多阶段总结管道（解析、游标、LLM总结、钩子注册）
---

## 步骤
1. 创建 transcript.py 解析模块，实现 parse_new_turns 及单轮截断逻辑
2. 创建 transcript_store.py 游标模块，实现非阻塞会话认领/释放/孤儿扫描
3. 在 llm.py 中新增 summarize_conversation 抽象方法及 DeepSeek/Null 实现
4. 创建 hooks/summarize.py 钩子脚本，依赖 Phase 1 完成
5. 创建 hooks/inject.py 孤儿扫描与总结注入钩子
6. 更新 settings.json 注册钩子
7. 运行全量 pytest 验证无回归

## 说明
该流程按设计文档分阶段并行实现，未来类似功能扩展可复用此模式