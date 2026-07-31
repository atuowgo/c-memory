#!/usr/bin/env python3
"""SessionEnd Hook（第 2 条 command，第 1 条已经是 summarize.py）：记录最近 10 次
会话的 session_id / 最后退出时间 / 内容摘要，供用户手动 `claude --resume <session_id>`
时查阅。

不挂 Stop（避免每轮都写，只在真正退出时记一次）；不注入 SessionStart 上下文（用户
明确要求不需要，靠自己查 memory/recent-sessions.md）。

约束：脚本永远以 exit code 0 结束，不阻塞会话退出；调试/错误信息一律写 stderr。
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# 通过 `python3 ${CLAUDE_PROJECT_DIR}/hooks/record_session.py` 这种绝对路径调用时，
# 脚本 CWD 不一定是仓库根目录，需显式把仓库根目录加入 sys.path 才能 import memory_lib。
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from memory_lib.storage import MEMORY_DIR  # noqa: E402

_MAX_ENTRIES = 10
_SUMMARY_EXCERPT_MAX_CHARS = 200

DATA_FILE = MEMORY_DIR / ".recent-sessions.json"
RENDERED_FILE = MEMORY_DIR / "recent-sessions.md"
PROJECT_SUMMARY_FILE = MEMORY_DIR / "project-summary.md"


def _read_entries() -> list[dict]:
    if not DATA_FILE.exists():
        return []
    try:
        data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    if not isinstance(data, list):
        return []
    return data


def _write_entries(entries: list[dict]) -> None:
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    DATA_FILE.write_text(
        json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _read_summary_excerpt() -> str:
    if not PROJECT_SUMMARY_FILE.exists():
        return ""
    try:
        text = PROJECT_SUMMARY_FILE.read_text(encoding="utf-8")
    except OSError:
        return ""
    return text.strip()[:_SUMMARY_EXCERPT_MAX_CHARS]


def _render_markdown(entries: list[dict]) -> str:
    lines = ["# 最近会话记录（最多 10 条，`claude --resume <session_id>` 用）", ""]
    for entry in entries:
        lines.append(f"## {entry.get('last_exit_ts', '')} — {entry.get('session_id', '')}")
        lines.append("")
        lines.append(entry.get("summary_excerpt", ""))
        lines.append("")
    return "\n".join(lines)


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return
    if not isinstance(payload, dict):
        return

    session_id = payload.get("session_id")
    if not session_id:
        return

    entries = _read_entries()

    now_iso = datetime.now(timezone.utc).isoformat()
    summary_excerpt = _read_summary_excerpt()

    existing = next((e for e in entries if e.get("session_id") == session_id), None)
    if existing is not None:
        existing["last_exit_ts"] = now_iso
        existing["summary_excerpt"] = summary_excerpt
    else:
        entries.append(
            {
                "session_id": session_id,
                "last_exit_ts": now_iso,
                "summary_excerpt": summary_excerpt,
            }
        )

    entries.sort(key=lambda e: e["last_exit_ts"], reverse=True)
    entries = entries[:_MAX_ENTRIES]

    _write_entries(entries)
    RENDERED_FILE.write_text(_render_markdown(entries), encoding="utf-8")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001 - SessionEnd Hook 永远不能阻塞退出
        print(f"record_session.py error: {exc!r}", file=sys.stderr)
    sys.exit(0)
