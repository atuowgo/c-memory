---
confidence: 0.5
evidence_sessions:
- 32bcf8c6-1ce2-4421-8286-1ff5071fb8a8
first_seen: '2026-07-30'
hit_count: 1
id: add-correctness-signal-to-procedure-mining
last_seen: '2026-07-30'
skill_asked: false
status: candidate
task_type: 为流程挖掘添加正确性信号和弃用机制
---

## 步骤
1. 查看 observe.py 了解现有信号来源
2. 询问用户选择成功信号来源（下一轮用户反馈）
3. 询问用户处理人工拒绝后的流程（标记 deprecated）
4. 读取并更新设计文档，新增正确性信号和弃用机制章节
5. 并行启动两个 subagent：一个改造 llm.py/mine_procedures.py/notify_pending_procedures.py，另一个改造对应测试文件
6. 读取多个相关源码文件（llm.py, mine_procedures.py, notify_pending_procedures.py, confidence.py, summarize.py, extract.py）
7. 编辑 llm.py 添加抽象方法和实现
8. 编辑设计文档确认更新

## 说明
该流程涉及多个文件协同修改，且需要用户决策，未来类似的功能增强任务可复用此模式。