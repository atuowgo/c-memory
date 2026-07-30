"""memory_lib.transcript 单元测试：真伪用户消息过滤、assistant 多记录拼接、游标过滤、截断、异常行容错。"""
from __future__ import annotations

import json

import pytest

from memory_lib import transcript


def _user_record(uuid: str, content, timestamp: str | None = None) -> dict:
    record = {"type": "user", "message": {"role": "user", "content": content}, "uuid": uuid}
    if timestamp is not None:
        record["timestamp"] = timestamp
    return record


def _write_jsonl(tmp_path, records) -> str:
    path = tmp_path / "transcript.jsonl"
    lines = [json.dumps(r, ensure_ascii=False) for r in records]
    path.write_text("\n".join(lines), encoding="utf-8")
    return str(path)


def test_real_user_message_with_string_content_is_recognized(tmp_path):
    records = [
        _user_record("u1", "第一个问题"),
        {"type": "assistant", "message": {"role": "assistant", "content": [{"type": "text", "text": "第一个回复"}]}, "uuid": "a1"},
    ]
    path = _write_jsonl(tmp_path, records)

    turns = transcript.parse_new_turns(path, None)

    assert len(turns) == 1
    assert turns[0] == {"uuid": "u1", "user": "第一个问题", "assistant": "第一个回复", "ts": ""}


def test_tool_result_disguised_as_user_is_filtered_out(tmp_path):
    records = [
        _user_record("u1", "真实提问"),
        {
            "type": "user",
            "message": {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "toolu_1", "content": []}]},
            "uuid": "fake-1",
        },
        {"type": "assistant", "message": {"role": "assistant", "content": [{"type": "text", "text": "回复"}]}, "uuid": "a1"},
    ]
    path = _write_jsonl(tmp_path, records)

    turns = transcript.parse_new_turns(path, None)

    assert len(turns) == 1
    assert turns[0]["uuid"] == "u1"
    assert turns[0]["assistant"] == "回复"


def test_multiple_assistant_records_with_tool_use_are_concatenated(tmp_path):
    records = [
        _user_record("u1", "帮我改一下代码"),
        {"type": "assistant", "message": {"role": "assistant", "content": [{"type": "text", "text": "我先看看文件"}]}, "uuid": "a1"},
        {"type": "assistant", "message": {"role": "assistant", "content": [{"type": "tool_use", "id": "t1", "name": "Read", "input": {}}]}, "uuid": "a2"},
        {
            "type": "user",
            "message": {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "t1", "content": []}]},
            "uuid": "fake-1",
        },
        {"type": "assistant", "message": {"role": "assistant", "content": [{"type": "text", "text": "改好了"}]}, "uuid": "a3"},
    ]
    path = _write_jsonl(tmp_path, records)

    turns = transcript.parse_new_turns(path, None)

    assert len(turns) == 1
    assert turns[0]["assistant"] == "我先看看文件\n改好了"


def test_after_uuid_filters_to_turns_following_cursor(tmp_path):
    records = [
        _user_record("u1", "问题一"),
        {"type": "assistant", "message": {"role": "assistant", "content": [{"type": "text", "text": "回复一"}]}, "uuid": "a1"},
        _user_record("u2", "问题二"),
        {"type": "assistant", "message": {"role": "assistant", "content": [{"type": "text", "text": "回复二"}]}, "uuid": "a2"},
    ]
    path = _write_jsonl(tmp_path, records)

    turns = transcript.parse_new_turns(path, after_uuid="u1")

    assert len(turns) == 1
    assert turns[0]["uuid"] == "u2"


def test_after_uuid_none_returns_all_turns_from_start(tmp_path):
    records = [
        _user_record("u1", "问题一"),
        {"type": "assistant", "message": {"role": "assistant", "content": [{"type": "text", "text": "回复一"}]}, "uuid": "a1"},
        _user_record("u2", "问题二"),
        {"type": "assistant", "message": {"role": "assistant", "content": [{"type": "text", "text": "回复二"}]}, "uuid": "a2"},
    ]
    path = _write_jsonl(tmp_path, records)

    turns = transcript.parse_new_turns(path, None)

    assert [t["uuid"] for t in turns] == ["u1", "u2"]


def test_after_uuid_not_found_falls_back_to_all_turns(tmp_path):
    records = [
        _user_record("u1", "问题一"),
        {"type": "assistant", "message": {"role": "assistant", "content": [{"type": "text", "text": "回复一"}]}, "uuid": "a1"},
    ]
    path = _write_jsonl(tmp_path, records)

    turns = transcript.parse_new_turns(path, after_uuid="does-not-exist")

    assert len(turns) == 1
    assert turns[0]["uuid"] == "u1"


def test_overlong_text_is_truncated(tmp_path):
    long_user_text = "x" * (transcript._TURN_TEXT_MAX_CHARS + 500)
    long_assistant_text = "y" * (transcript._TURN_TEXT_MAX_CHARS + 500)
    records = [
        _user_record("u1", long_user_text),
        {"type": "assistant", "message": {"role": "assistant", "content": [{"type": "text", "text": long_assistant_text}]}, "uuid": "a1"},
    ]
    path = _write_jsonl(tmp_path, records)

    turns = transcript.parse_new_turns(path, None)

    assert len(turns[0]["user"]) <= transcript._TURN_TEXT_MAX_CHARS + len(transcript._TRUNCATION_SUFFIX)
    assert turns[0]["user"].endswith(transcript._TRUNCATION_SUFFIX)
    assert turns[0]["assistant"].endswith(transcript._TRUNCATION_SUFFIX)


def test_malformed_lines_are_skipped_without_raising(tmp_path):
    path = tmp_path / "transcript.jsonl"
    lines = [
        "not a json line at all {{{",
        json.dumps({"type": "user", "message": {"role": "user", "content": "正常问题"}, "uuid": "u1"}, ensure_ascii=False),
        json.dumps({"type": "assistant", "message": {"role": "assistant"}, "uuid": "a1"}),  # 缺 content
        json.dumps({"type": "user", "message": {"role": "user"}, "uuid": "u2"}),  # 缺 content
        json.dumps(
            {"type": "assistant", "message": {"role": "assistant", "content": [{"type": "text", "text": "回复"}]}, "uuid": "a2"}
        ),
        "",
        "[1, 2, 3]",  # 合法 JSON 但不是 dict
    ]
    path.write_text("\n".join(lines), encoding="utf-8")

    turns = transcript.parse_new_turns(str(path), None)

    assert len(turns) == 1
    assert turns[0]["uuid"] == "u1"
    assert turns[0]["assistant"] == "回复"


def test_nonexistent_transcript_path_returns_empty_list():
    assert transcript.parse_new_turns("/no/such/file.jsonl", None) == []


def test_empty_transcript_path_returns_empty_list():
    assert transcript.parse_new_turns("", None) == []


def test_turn_ts_field_reflects_user_record_timestamp(tmp_path):
    records = [
        _user_record("u1", "第一个问题", timestamp="2026-07-30T10:00:00Z"),
        {"type": "assistant", "message": {"role": "assistant", "content": [{"type": "text", "text": "第一个回复"}]}, "uuid": "a1"},
    ]
    path = _write_jsonl(tmp_path, records)

    turns = transcript.parse_new_turns(path, None)

    assert turns[0]["ts"] == "2026-07-30T10:00:00Z"


def test_turn_ts_field_defaults_to_empty_when_timestamp_missing(tmp_path):
    records = [
        _user_record("u1", "第一个问题"),
        {"type": "assistant", "message": {"role": "assistant", "content": [{"type": "text", "text": "第一个回复"}]}, "uuid": "a1"},
    ]
    path = _write_jsonl(tmp_path, records)

    turns = transcript.parse_new_turns(path, None)

    assert turns[0]["ts"] == ""


def test_turn_ts_field_defaults_to_empty_when_timestamp_not_string(tmp_path):
    records = [
        _user_record("u1", "第一个问题", timestamp=1234567890),
        {"type": "assistant", "message": {"role": "assistant", "content": [{"type": "text", "text": "第一个回复"}]}, "uuid": "a1"},
    ]
    path = _write_jsonl(tmp_path, records)

    turns = transcript.parse_new_turns(path, None)

    assert turns[0]["ts"] == ""
