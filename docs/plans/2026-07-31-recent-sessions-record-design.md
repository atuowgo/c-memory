---
标题: 最近会话记录（resume 速查）设计
状态: 已确认，待实现
创建时间: 2026-07-31
---

## 1. 背景与目标

Claude Code 退出时会提示"可以用 `--resume <session_id>` 恢复上次会话"，但用户经常想不起来某次会话的 `session_id`。hook 无法修改/拦截 CLI 自身打印的这句提示，能做的是维护一份本地记录文件，用户想 resume 时自己去查。

目标：`SessionEnd` 时记录本次会话的 `session_id`（即 resume 用的 id）、最后退出时间、内容摘要，最多保留最近 10 条，供用户手动查阅。**不注入 SessionStart 上下文**（用户明确要求不需要，靠自己查文件）。

## 2. 数据模型

沿用项目里已有的"隐藏 JSON 存真实数据 + 渲染人类可读 md"模式（对照 `memory_lib/storage.py` 的 `.dedup_state.json` + `rules/auto-evolved.md`）：

- `memory/.recent-sessions.json`（真正数据源，隐藏文件）：`[{"session_id": "...", "last_exit_ts": "ISO8601", "summary_excerpt": "..."}]`，按 `last_exit_ts` 降序排列，最多保留 10 条；同一 `session_id` 再次退出时更新已有条目（不重复追加），随后重新按时间排序、裁剪到 10 条。
- `memory/recent-sessions.md`（每次全量重新渲染，人类可读）：

```markdown
# 最近会话记录（最多 10 条，`claude --resume <session_id>` 用）

## 2026-07-31T09:40:00Z — 32bcf8c6-1ce2-4421-8286-1ff5071fb8a8

c-memory 项目新增流程挖掘管线，识别可复用的多步骤操作流程...（截断约200字符）

## 2026-07-30T15:20:00Z — a1b2c3d4-...

...
```

`summary_excerpt` 取当前 `memory/project-summary.md` 内容截断到约 200 字符（文件不存在/为空时用空字符串）。

**两个文件都不进 git**：`session_id` 只在本机有意义（resume 依赖本机的 transcript 文件），跟 `.dedup_state.json`/sqlite 状态文件性质一样，`.gitignore` 补两行：`memory/.recent-sessions.json`、`memory/recent-sessions.md`。

## 3. 触发与实现

新增 `hooks/record_session.py`，挂 `SessionEnd`（`.claude/settings.json` 的 `SessionEnd` 追加第 2 条 command，第 1 条已经是 `summarize.py`）。**不挂 Stop**（避免每轮都写，只在真正退出时记一次）。

`main()` 流程：
1. `json.load(sys.stdin)` 解析 payload，拿 `session_id`；缺失则直接 return。
2. 读 `memory/project-summary.md`（不存在则空字符串），截断到约 200 字符作为 `summary_excerpt`。
3. 读 `memory/.recent-sessions.json`（不存在/解析失败则空列表）。
4. 按 `session_id` 找已有条目：存在则更新（`last_exit_ts`/`summary_excerpt` 覆盖），不存在则新增一条 `{"session_id": ..., "last_exit_ts": now_iso, "summary_excerpt": ...}`。
5. 按 `last_exit_ts` 降序排序，裁剪到最多 10 条。
6. 写回 `memory/.recent-sessions.json`；重新渲染整份 `memory/recent-sessions.md`。

**不强依赖 `summarize.py` 的执行顺序**：两个脚本各自独立读写不同文件，`record_session.py` 读到的 `project-summary.md` 可能是这次退出前最新的一版（也可能 `summarize.py` 恰好还没来得及在本次 SessionEnd 里更新完），不强求跟这次会话最后几轮完全对齐，作为"速查摘要"够用即可，不建立跨脚本的执行顺序依赖。

**约束**：脚本永远 exit code 0，不阻塞会话退出；调试/错误信息写 stderr。

**已知限制**：`SessionEnd` 不保证在 crash/kill 时触发（跟 `project-summary.md` 现有的限制一致，未来若要补，参考 `inject.py` 已有的孤儿 session 扫描思路，本轮不做）。

## 4. 改动文件清单

| 文件 | 改动类型 | 说明 |
|---|---|---|
| `hooks/record_session.py` | 新 | SessionEnd hook，记录最近会话 |
| `.claude/settings.json` | 改 | `SessionEnd` 追加第 2 条 command |
| `.gitignore` | 改 | 忽略 `memory/.recent-sessions.json`、`memory/recent-sessions.md` |
| `tests/test_record_session.py` | 新 | 覆盖新建/更新已有条目/裁剪到10条/project-summary缺失 等场景 |

`build.sh` 不需要改动（整目录拷贝自动覆盖）。

## 5. 范围之外（本轮不做）

- SessionStart 注入提醒（用户明确不需要）。
- crash/kill 场景的补录（孤儿扫描），跟 `project-summary.md` 现有限制一致，暂不处理。
