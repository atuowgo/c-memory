---
confidence: 0.5
evidence_sessions:
- 32bcf8c6-1ce2-4421-8286-1ff5071fb8a8
first_seen: '2026-07-30'
hit_count: 1
id: build-and-install-script-for-c-memory
last_seen: '2026-07-30'
skill_asked: false
status: candidate
task_type: 构建c-memory项目的发布包和首次安装脚本
---

## 步骤
1. 检查现有项目结构和配置
2. 创建build.sh脚本，将hooks/、memory_lib/、.claude/settings.json等打包到dist/
3. 创建install.sh脚本，检测Python、建venv、装依赖、建目录、生成.env
4. 修复install.sh中macOS bash 3.2兼容性问题（$VAR后跟中文标点）
5. 运行build.sh生成dist/
6. 在临时目录中冒烟测试install.sh
7. 将dist/加入.gitignore

## 说明
构建流程包含两个核心脚本：build.sh（打包）和install.sh（首次安装），并修复了macOS旧版bash的兼容性bug。