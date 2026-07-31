---
confidence: 0.5
deprecated: false
domain: workflow
hit_count: 1
id: verify-sensitive-info-not-leaked
last_seen: '2026-07-31'
scope: personal
trigger: 当操作涉及密钥或敏感环境变量时
---

## Action
确保不打印实际密钥值，只验证存在性或键名

## Evidence
Bash 命令中 echo 提示 .env 存在但内容不会打印，且最后确认密钥值全程未打印