---
created: '2026-07-29'
description: 构建产物路径为 dist/.c-memory/
id: build-output-fixed-name
keywords:
- build
- output-path
type: project
---

build.sh 中 PACKAGE_NAME 设置为 .c-memory，产物输出到 dist/.c-memory/。部署命令为 cp -R dist/.c-memory target-project/。