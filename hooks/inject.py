#!/usr/bin/env python3
"""SessionStart Hook: 召回相关记忆并格式化注入到会话上下文。

输入协议（Claude Code 官方 Hooks 文档，SessionStart 事件）：
stdin 接收一段 JSON，字段包括 session_id / cwd /
hook_event_name（固定 "SessionStart"）等。

约束：stdout 内容会被直接注入 Claude 的上下文，因此 stdout 只能输出
格式化后的记忆文本，任何调试/错误信息一律写 stderr；脚本必须永远以
exit code 0 结束，不能阻塞会话启动。
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# 通过 `python3 ${CLAUDE_PROJECT_DIR}/hooks/inject.py` 这种绝对路径调用时，
# 脚本 CWD 不一定是仓库根目录，需显式把仓库根目录加入 sys.path 才能 import memory_lib。
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from memory_lib.providers import get_embedding_provider  # noqa: E402
from memory_lib.recall import build_query, recall_top_k  # noqa: E402
from memory_lib.storage import list_memories  # noqa: E402


def _format_memories(top_memories: list[dict]) -> str:
    lines = []
    for mem in top_memories:
        label = "[project]" if mem.get("type") == "project" else "[user]"
        lines.append(f"{label} {mem.get('body', '').strip()}")
    return "\n".join(lines)


def main() -> None:
    try:
        payload = json.load(sys.stdin)
        cwd = payload.get("cwd") or os.getcwd()
    except (json.JSONDecodeError, ValueError):
        cwd = os.getcwd()

    memories = list_memories()
    if not memories:
        return

    query = build_query(cwd)
    provider = get_embedding_provider()
    top_memories = recall_top_k(query, memories, provider, k=5)

    if not top_memories:
        return

    print(_format_memories(top_memories))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001 - SessionStart Hook 永远不能阻塞
        print(f"inject.py error: {exc!r}", file=sys.stderr)
    sys.exit(0)
