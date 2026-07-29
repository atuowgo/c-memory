---
created: '2026-07-29'
description: scripts/install.sh 是首次使用安装脚本，打包在 dist/ 内
id: install-script-exists
keywords:
- install
- setup
type: project
---

install.sh 检测 Python 是否支持 sqlite-vec loadable extension（macOS 系统自带 /usr/bin/python3 不支持，会给出清晰报错和 PYTHON_BIN 用法提示），创建 .venv --copies，安装依赖，创建 memory/ 目录结构，生成 .env。