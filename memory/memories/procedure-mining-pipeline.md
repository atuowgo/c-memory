---
created: '2026-07-30'
description: 新增第三条独立管线——流程挖掘（procedure mining），与习惯提炼、对话总结并列
id: procedure-mining-pipeline
keywords:
- procedure
- mining
type: project
---

在 Stop hook 上新增 mine_procedures.py，每次触发时：1) 用 transcript.py（补时间戳）取自上次游标以来新增的用户轮次；2) 对每个 episode 按时间区间从 observations 表捞工具调用序列；3) 序列+文本喂给 LLM 输出任务类型+步骤列表；4) 用 dedup.py 相似度比对，命中则 hit_count++，否则新建候选；5) 跨过阈值后通过 systemMessage 提示用户。