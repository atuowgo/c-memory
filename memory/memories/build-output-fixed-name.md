---
created: '2026-07-29'
description: 构建产出目录固定为 dist/c-memory/
id: build-output-fixed-name
keywords:
- build
- deploy
type: project
---

build.sh 直接产出 dist/c-memory/（包名固定，构建即定名），部署命令简化为 cp -R dist/c-memory target-project/，不再需要用户手动加子目录或改名。