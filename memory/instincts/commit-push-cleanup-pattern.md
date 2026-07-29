---
confidence: 0.5
deprecated: false
domain: workflow
hit_count: 1
id: commit-push-cleanup-pattern
last_seen: '2026-07-29'
scope: personal
trigger: 完成一轮功能开发或修复后
---

## Action
执行 git status、git log、git status -sb 检查工作树和远端状态，然后 git add -A、git commit、git push 完成提交同步

## Evidence
会话中连续执行了 git status --short、git log --oneline -3、git status -sb 检查，随后 git add -A、git commit、git push