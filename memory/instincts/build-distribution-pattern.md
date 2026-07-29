---
confidence: 0.5
deprecated: false
domain: workflow
hit_count: 1
id: build-distribution-pattern
last_seen: '2026-07-29'
scope: personal
trigger: 需要为项目创建可分发的构建产物
---

## Action
创建 build.sh 脚本，将运行所需文件打包到 dist/，排除敏感数据和开发文件，并确保 .gitignore 忽略 dist/

## Evidence
创建了 build.sh，打包 hooks/、memory_lib/、.claude/settings.json、.env.example、requirements.txt、README.md 到 dist/，自动清理 __pycache__，排除 .env、memory/、tests/、docs/，并将 dist/ 加入 .gitignore