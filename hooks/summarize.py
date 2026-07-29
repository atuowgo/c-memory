#!/usr/bin/env python3
"""Stop / PreCompact / SessionEnd Hook 共用脚本：把新增对话滚动总结进
memory/project-summary.md（情景记忆，"上次聊到哪了"）。

输入协议（Claude Code 官方 Hooks 文档）：
stdin 接收一段 JSON，字段包括 session_id / transcript_path / cwd /
hook_event_name（"Stop" / "PreCompact" / "SessionEnd" 之一）。三种事件的
payload 字段名理论上一致，但本脚本不假设 transcript_path 一定存在
（尤其 SessionEnd 场景没有 100% 把握），缺失时直接优雅跳过。

行为：
- Stop：常规触发，累计新增轮次数 >= _TURN_THRESHOLD 才真正总结一次，
  没达到阈值时不 release，游标保持 processing，留到下次累积。
- PreCompact / SessionEnd：force 模式，跳过阈值判断，只要有新增轮次就总结。

约束：脚本必须永远以 exit code 0 结束，不能阻塞会话结束/压缩；调试/错误信息
一律写 stderr。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

# 通过 `python3 ${CLAUDE_PROJECT_DIR}/hooks/summarize.py` 这种绝对路径调用时，
# 脚本 CWD 不一定是仓库根目录，需显式把仓库根目录加入 sys.path 才能 import memory_lib。
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from memory_lib import transcript, transcript_store  # noqa: E402
from memory_lib.providers import get_llm_provider  # noqa: E402
from memory_lib.storage import MEMORY_DIR  # noqa: E402

_TURN_THRESHOLD = 100
_FORCE_EVENTS = ("PreCompact", "SessionEnd")
_SUMMARY_FILE = MEMORY_DIR / "project-summary.md"


def _read_existing_summary() -> str:
    if not _SUMMARY_FILE.exists():
        return ""
    try:
        return _SUMMARY_FILE.read_text(encoding="utf-8")
    except OSError:
        return ""


def _write_summary(text: str) -> None:
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    _SUMMARY_FILE.write_text(text or "", encoding="utf-8")


def _format_turns(new_turns: list[dict]) -> str:
    """把 parse_new_turns 的输出格式化成喂给 LLM 的文本，每轮用户/assistant 分块标出。"""
    blocks = []
    for index, turn in enumerate(new_turns, start=1):
        blocks.append(
            f"### 轮次 {index} (uuid: {turn.get('uuid', '')})\n"
            f"[用户]\n{turn.get('user', '')}\n"
            f"[assistant]\n{turn.get('assistant', '')}"
        )
    return "\n\n".join(blocks)


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return
    if not isinstance(payload, dict):
        return

    session_id = payload.get("session_id")
    transcript_path = payload.get("transcript_path")
    if not session_id or not transcript_path:
        return  # 缺字段（比如 SessionEnd 万一没带 transcript_path）就没法处理，优雅跳过

    force = payload.get("hook_event_name") in _FORCE_EVENTS

    claimed, after_uuid = transcript_store.try_claim_session(session_id, transcript_path)
    if not claimed:
        return  # 锁被占用且未超时，跳过本次

    new_turns = transcript.parse_new_turns(transcript_path, after_uuid)
    if not new_turns:
        transcript_store.release_session(session_id, after_uuid)
        return

    if not force and len(new_turns) < _TURN_THRESHOLD:
        return  # 不 release，留到下次累积（cursor 保持 processing 状态不变）

    try:
        provider = get_llm_provider()
        previous_summary = _read_existing_summary()
        new_summary = provider.summarize_conversation(previous_summary, _format_turns(new_turns))
    except Exception:  # noqa: BLE001 - LLM 路径失败不能推进游标，下次要重试同一批
        transcript_store.release_session(session_id, after_uuid)
        return

    _write_summary(new_summary)
    transcript_store.release_session(session_id, new_turns[-1]["uuid"])  # 只在写入成功后才推进


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001 - Stop/PreCompact/SessionEnd Hook 永远不能阻塞退出
        print(f"summarize.py error: {exc!r}", file=sys.stderr)
    sys.exit(0)
