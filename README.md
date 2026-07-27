# c-memory

给 Claude Code 装的个人记忆系统：通过「观察 → 提炼 → 注入」三段式闭环，让 Claude Code 自动积累项目知识和个人行为习惯，并在新会话中自动召回。设计思路参考得物技术团队的相关文章（见 `docs/notes/`），完整设计见 `docs/plans/`。

## 目录结构

```
c-memory/
├── .claude/settings.json      # Hook 注册（PostToolUse/Stop/SessionStart）
├── hooks/                     # observe.py / extract.py / inject.py
├── memory_lib/                # providers(llm/embedding) / detectors / confidence / privacy / storage / recall
├── memory/                    # 数据落盘目录（observations / instincts / memories / rules）
├── tests/
├── requirements.txt
└── README.md
```

详细字段和数据模型见 `docs/plans/2026-07-27-claude-code-memory-system-design.md`。

## 安装

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

然后在项目根目录配置 `.env`（可参考同目录下已有的 `.env` 格式）：

```
DEEPSEEK_API_KEY=...
LLM_MODEL=...
ARK_API_KEY=...
ARK_EMBEDDING_BASE_URL=...
ARK_EMBEDDING_MODEL=...
```

以上变量均为**可选**：不配置时系统自动降级为纯规则 + TF-IDF 模式（`NullProvider` + `TfidfProvider`），完整闭环仍能跑通，只是语义分析和召回精度会弱一些。

`.env` 已在 `.gitignore` 中，切勿提交到仓库。

## Hook 已注册，无需额外操作

`.claude/settings.json` 已经注册好 `PostToolUse`(observe.py) / `Stop`(extract.py) / `SessionStart`(inject.py) 三个 Hook，且命令都指向 `.venv/bin/python3`。正常在本仓库用 Claude Code 工作即可自动生效。

## 如何验证闭环生效

多跑几次真实会话，重复做同一类操作（比如「改文件前先 Read」），几天后检查：

- `memory/instincts/*.md`：behavior pattern 是否被识别，confidence 是否随命中次数递增
- `memory/rules/auto-evolved.md`：confidence >= 0.7 的规则是否被写入
- 新会话启动时，如果 `memory/memories/` 里有相关项目记忆，`inject.py` 的输出会通过 `SessionStart` Hook 自动出现在上下文里（可在会话开头看到注入的记忆文本）

## 备注

这是个人单机场景的实现，数据落在项目目录内的 `memory/`，尚未决定是否要提升为 `~/.claude` 全局配置。如果以后想改成全局存储，主要改动点是 `memory_lib/storage.py` 里的 `MEMORY_DIR` 常量。
