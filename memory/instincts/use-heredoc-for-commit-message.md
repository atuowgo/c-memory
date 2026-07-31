---
confidence: 0.5
deprecated: false
domain: git
hit_count: 1
id: use-heredoc-for-commit-message
last_seen: '2026-07-31'
scope: personal
trigger: 提交信息较长或包含多行内容时
---

## Action
使用 cat <<'EOF' 的 heredoc 方式构造多行 commit message，确保格式正确

## Evidence
Bash 调用：rtk git commit -m "$(cat <<'EOF' ... EOF)"