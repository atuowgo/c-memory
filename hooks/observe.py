#!/usr/bin/env python3
"""PostToolUse Hook: 采集每次工具调用为一条观测记录，写入 observations.jsonl。

输入协议（Claude Code 官方 Hooks 文档，PostToolUse 事件）：
stdin 接收一段 JSON，字段包括 session_id / transcript_path / cwd /
hook_event_name（固定 "PostToolUse"）/ tool_name / tool_input / tool_response。

约束：脚本必须永远以 exit code 0 结束，不能阻塞正常工具调用；调试/错误信息一律写 stderr。
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# 通过 `python3 ${CLAUDE_PROJECT_DIR}/hooks/observe.py` 这种绝对路径调用时，
# 脚本 CWD 不一定是仓库根目录，需显式把仓库根目录加入 sys.path 才能 import memory_lib。
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from memory_lib.privacy import extract_behavioral_signal, filter_sensitive  # noqa: E402
from memory_lib.storage import (  # noqa: E402
    append_observation,
    read_dedup_state,
    write_dedup_state,
)

DEDUP_WINDOW_SECONDS = 300
DEDUP_STATE_TTL_SECONDS = 3600


def _dedup_key(tool_name: str, tool_input: dict) -> str:
    digest_input = json.dumps(tool_input, sort_keys=True, ensure_ascii=False)
    raw = f"{tool_name}:{digest_input}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _parse_iso(ts_str: str):
    try:
        return datetime.fromisoformat(ts_str)
    except (ValueError, TypeError):
        return None


def main() -> None:
    payload = json.load(sys.stdin)

    session_id = payload.get("session_id")
    tool_name = payload.get("tool_name")
    tool_input = payload.get("tool_input") or {}
    # tool_response（文件内容/命令输出等）不落盘：detectors 只需要 tool_name +
    # 路径/命令这类结构信号就能识别行为模式，没有必要、也不应该保留实际内容。
    signal = extract_behavioral_signal(tool_name, tool_input)

    now = datetime.now(timezone.utc)
    record = {
        "session_id": session_id,
        "ts": now.isoformat(),
        "tool_name": tool_name,
        "tool_input": signal,
    }
    filtered_record = filter_sensitive(record)

    # 去重 key 用原始 tool_input 算（不落盘，只在内存里参与哈希），
    # 保证同一文件的不同编辑内容仍被视为不同调用，不会被误判为重复。
    key = _dedup_key(tool_name, tool_input)
    state = read_dedup_state()

    last_ts_str = state.get(key)
    last_ts = _parse_iso(last_ts_str) if last_ts_str else None
    if last_ts is not None and (now - last_ts).total_seconds() < DEDUP_WINDOW_SECONDS:
        return  # 5 分钟内重复，跳过写入

    append_observation(filtered_record)

    state[key] = now.isoformat()
    # 清理超过 1 小时的旧 key，避免去重状态文件无限膨胀
    cutoff = now - timedelta(seconds=DEDUP_STATE_TTL_SECONDS)
    cleaned_state = {}
    for k, v in state.items():
        parsed = _parse_iso(v)
        if parsed is not None and parsed < cutoff:
            continue
        cleaned_state[k] = v
    write_dedup_state(cleaned_state)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001 - PostToolUse Hook 永远不能阻塞
        print(f"observe.py error: {exc!r}", file=sys.stderr)
    sys.exit(0)
