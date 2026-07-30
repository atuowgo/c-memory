---
confidence: 0.5
evidence_sessions:
- 32bcf8c6-1ce2-4421-8286-1ff5071fb8a8
first_seen: '2026-07-30'
hit_count: 1
id: merge-claude-settings-without-overwrite
last_seen: '2026-07-30'
skill_asked: false
status: candidate
task_type: 修复 .claude/settings.json 被覆盖的问题，改为合并而非覆盖
---

## 步骤
1. 创建 merge_settings.py 脚本，实现按 hook 事件维度合并配置，保留目标项目已有内容，追加 c-memory 的 5 个 hook 且不重复
2. 修改 build.sh，将 .claude/settings.json 改为 dist/settings.template.json，避免 cp -R 覆盖
3. 修改 install.sh，最后一步调用 merge_settings.py 进行合并，而非打印警告
4. 验证：新建目录安装，确保合并正确保留已有配置
5. 验证：重复安装，确保幂等性（不产生重复条目）
6. 运行全量测试，确保无回归

## 说明
核心思路是将 settings.json 改为独立模板文件名，并在安装时通过 Python 脚本做真正的 JSON 合并，避免 cp -R 覆盖时机早于脚本执行。