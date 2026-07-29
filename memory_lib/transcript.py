"""解析 Claude Code transcript JSONL，把真实用户输入与 assistant 回复配对成"轮次"列表。"""
from __future__ import annotations

import json
from pathlib import Path

_TURN_TEXT_MAX_CHARS = 4000
_TRUNCATION_SUFFIX = "...(截断)"


def _truncate(text: str) -> str:
    if len(text) <= _TURN_TEXT_MAX_CHARS:
        return text
    return text[:_TURN_TEXT_MAX_CHARS] + _TRUNCATION_SUFFIX


def _is_real_user_message(record: dict) -> bool:
    """真实用户输入的判定：type=="user" 且 message.content 是字符串。

    content 是数组的场景（工具结果伪装成 user 角色、isMeta 系统注入文本等）一律不算。
    """
    if record.get("type") != "user":
        return False
    message = record.get("message")
    if not isinstance(message, dict):
        return False
    return isinstance(message.get("content"), str)


def _extract_assistant_text(record: dict) -> str:
    """从一条 assistant 记录里拼出纯文本块（跳过 thinking/tool_use 等非文本块）。"""
    message = record.get("message")
    if not isinstance(message, dict):
        return ""
    content = message.get("content")
    if not isinstance(content, list):
        return ""
    text_pieces = []
    for block in content:
        if isinstance(block, dict) and block.get("type") == "text" and isinstance(block.get("text"), str):
            text_pieces.append(block["text"])
    return "\n".join(text_pieces)


def parse_new_turns(transcript_path: str, after_uuid: str | None) -> list[dict]:
    """返回 [{"uuid": "...", "user": "...", "assistant": "..."}]，按 transcript 顺序。

    uuid 取该轮里"真实用户输入那条记录"的 uuid（用作下次调用的游标）。
    after_uuid=None 表示从头开始；非 None 表示只返回该 uuid 之后的轮次（不含该 uuid
    本身对应的轮次）。找不到 after_uuid（比如文件被截断过）时保守地从头返回全部。
    """
    if not transcript_path:
        return []

    path = Path(transcript_path)
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []

    turns: list[dict] = []
    current_uuid: str | None = None
    current_user_text: str | None = None
    current_assistant_parts: list[str] = []

    def _flush_current_turn() -> None:
        if current_uuid is None:
            return
        turns.append(
            {
                "uuid": current_uuid,
                "user": _truncate(current_user_text or ""),
                "assistant": _truncate("\n".join(current_assistant_parts)),
            }
        )

    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(record, dict):
            continue

        record_type = record.get("type")
        if record_type == "user":
            if not _is_real_user_message(record):
                continue  # 工具结果等伪用户消息，丢弃
            uuid = record.get("uuid")
            if not isinstance(uuid, str) or not uuid:
                continue
            _flush_current_turn()
            current_uuid = uuid
            current_user_text = record["message"]["content"]
            current_assistant_parts = []
        elif record_type == "assistant":
            if current_uuid is None:
                continue  # 还没见过真实用户输入，这条 assistant 文本无处挂靠
            text = _extract_assistant_text(record)
            if text:
                current_assistant_parts.append(text)

    _flush_current_turn()

    if after_uuid is None:
        return turns

    for index, turn in enumerate(turns):
        if turn["uuid"] == after_uuid:
            return turns[index + 1 :]
    return turns  # after_uuid 在文件里找不到（如被截断过），保守地从头全部返回
