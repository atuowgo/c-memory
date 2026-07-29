---
confidence: 0.5
deprecated: false
domain: workflow
hit_count: 1
id: install-script-pattern
last_seen: '2026-07-29'
scope: personal
trigger: 需要为项目提供首次使用安装流程
---

## Action
创建 install.sh 脚本，检测环境兼容性、创建虚拟环境、安装依赖、初始化目录结构、生成配置文件，并提供清晰的错误提示和用法说明

## Evidence
创建了 scripts/install.sh，检测 Python 是否支持 sqlite-vec loadable extension，使用 --copies 创建 venv，安装依赖，创建 memory/ 目录结构，生成 .env，并给出 PYTHON_BIN 用法提示