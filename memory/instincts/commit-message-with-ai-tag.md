---
confidence: 0.5
deprecated: false
domain: git
hit_count: 1
id: commit-message-with-ai-tag
last_seen: '2026-07-31'
scope: personal
trigger: 使用 AI 辅助生成提交信息时，在 commit message 中包含 AI 标识和详细描述
---

## Action
使用 heredoc 格式的 commit message，包含 [#AI commit#] 和工具名称，并详细描述改动内容

## Evidence
命令：rtk git commit -m "$(cat <<'EOF'\n[#AI commit#][Claude Code]feat(memory): SessionStart注入改为JSON输出，用户可见完整高亮摘要\n..."