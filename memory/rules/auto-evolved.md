# 自动演化规则（自动生成，请勿手工编辑）

<!-- 更新时间: 2026-07-31T11:17:59.962401 -->

- **本次会话执行了多次 Bash 调用但从未 commit/push** (confidence: 0.90, domain: git)
- **在编辑文件前先读取相关上下文（如 README、现有代码）** (confidence: 0.90, domain: workflow)
- **编辑文件前先读取文件相关部分** (confidence: 0.75, domain: workflow)
- **在 git add 之后、commit 之前，检查暂存区是否包含敏感文件（如 .env、.sqlite3）** (confidence: 0.70, domain: git)
- **完成代码修改后** (confidence: 0.70, domain: testing)
