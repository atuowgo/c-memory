# 项目工作记忆维护

## 当前项目总结

本项目 `c-memory` 是一个为 Claude Code 设计的个人记忆系统，位于 `/Users/doubao/workspace/vibe/c-memory`。系统通过三个 Hook 实现闭环：`observe.py`（PostToolUse）记录工具调用观测到 SQLite，`extract.py`（Stop）增量处理观测并提炼为行为习惯（instincts）和项目事实（memories），`inject.py`（SessionStart）将高置信度习惯和语义相关记忆注入新会话上下文。

**最近完成的工作**：

1. **新增「项目工作记忆」功能**：设计并实现了完整的对话总结管线，包括 `memory_lib/transcript.py`（解析 transcript JSONL 提取用户/assistant 对话轮次）、`memory_lib/transcript_store.py`（非阻塞游标管理+孤儿 session 扫描）、`hooks/summarize.py`（Stop/PreCompact/SessionEnd 三钩子共用，增量总结对话内容）。`inject.py` 新增孤儿 session 后台补总结和 `[project-recap]` 区块注入（排在 habit/memory 之前）。`.claude/settings.json` 注册了 PreCompact/SessionEnd 钩子，Stop 追加第二个 command。

2. **修复设计缺陷**：`try_claim_session` 返回值从单一 `None` 改为 `(claimed: bool, cursor: str | None)` 元组，消除"全新 session"与"锁被占用"的歧义。

3. **与得物实现对齐**：提示词改为 id/trigger/action/domain/evidence + name/description/body/type/keywords 字段结构，domain 收窄为固定枚举（workflow/testing/git/code-style/project-context），project_facts 增加排除清单。监听范围对齐为完整 `tool_input` + `tool_response` 前 500 字符，正则脱敏叠加 `ghp_`/`AKIA`/`Bearer` 模式。

4. **数据清理**：清空本地 instinct/memory/rules 数据，重置为干净状态。新生成的 instinct/memory 已使用英文 kebab-case id。

**当前状态**：77 个测试全部通过。系统已在本次会话中真实运行，生成了若干英文 id 的行为习惯和项目事实。设计文档 `docs/plans/2026-07-29-project-summary-memory-design.md` 已落盘。

**待办事项**：
- 真实使用中验证"连续对话超过100轮自动更新"和"手动 `/compact` 触发强制刷新"两个场景
- 考虑是否将 `.serena/project.yml` 纳入版本控制（当前整体忽略）
- 考虑是否将 instinct 提升为全局（跨项目共享），当前为项目级隔离