---
created: '2026-07-29'
description: 每次代码变更后立即运行测试，确保无回归
id: test-driven-development
keywords:
- testing
- pytest
type: workflow
---

开发流程中，每次 Write 或 Edit 操作后都会运行 pytest 测试（包括单个模块测试和全量测试），以保证代码正确性和避免回归。测试命令如 `pytest tests/test_transcript_store.py -q` 和 `pytest tests/ -q`。