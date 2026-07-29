---
confidence: 0.5
deprecated: false
domain: workflow
hit_count: 1
id: test-after-build-deploy
last_seen: '2026-07-29'
scope: personal
trigger: 修改构建或部署流程后
---

## Action
执行完整的构建、部署到临时目录、验证 hook 命令前缀正确性的三轮测试

## Evidence
三轮实测（构建、部署到已有 .claude/settings.json 的目标项目、hook 命令前缀正确性）全部通过