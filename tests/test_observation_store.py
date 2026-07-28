"""memory_lib.observation_store 单元测试：SQLite 追加、增量查询、按时间保留、处理游标/并发跳过。"""
from __future__ import annotations

import shutil
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from memory_lib import observation_store


@pytest.fixture()
def isolated_db(monkeypatch):
    tmp_dir = Path(tempfile.mkdtemp())
    monkeypatch.setattr(observation_store, "MEMORY_DIR", tmp_dir)
    monkeypatch.setattr(observation_store, "DB_FILE", tmp_dir / ".observations.sqlite3")
    yield tmp_dir
    shutil.rmtree(tmp_dir, ignore_errors=True)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def test_append_then_list_new_by_session(isolated_db):
    observation_store.append_observation(
        {"session_id": "s1", "ts": _now_iso(), "tool_name": "Read", "tool_input": {"file_path": "a.py"}}
    )
    observation_store.append_observation(
        {"session_id": "s2", "ts": _now_iso(), "tool_name": "Read", "tool_input": {"file_path": "b.py"}}
    )
    observation_store.append_observation(
        {"session_id": "s1", "ts": _now_iso(), "tool_name": "Edit", "tool_input": {"file_path": "a.py"}}
    )

    results = observation_store.list_new_session_observations("s1", after_id=0)

    assert len(results) == 2
    assert [r["tool_name"] for r in results] == ["Read", "Edit"]
    assert results[0]["tool_input"] == {"file_path": "a.py"}


def test_tool_response_summary_round_trips(isolated_db):
    observation_store.append_observation(
        {
            "session_id": "s1",
            "ts": _now_iso(),
            "tool_name": "Bash",
            "tool_input": {"command": "echo hi"},
            "tool_response_summary": "hi\n",
        }
    )
    observation_store.append_observation(
        {"session_id": "s1", "ts": _now_iso(), "tool_name": "Read", "tool_input": {"file_path": "a.py"}}
    )

    results = observation_store.list_new_session_observations("s1", after_id=0)

    assert results[0]["tool_response_summary"] == "hi\n"
    assert results[1]["tool_response_summary"] is None


def test_list_new_only_returns_rows_after_cursor(isolated_db):
    observation_store.append_observation(
        {"session_id": "s1", "ts": _now_iso(), "tool_name": "Read", "tool_input": {}}
    )
    first_batch = observation_store.list_new_session_observations("s1", after_id=0)
    cursor = first_batch[-1]["id"]

    observation_store.append_observation(
        {"session_id": "s1", "ts": _now_iso(), "tool_name": "Edit", "tool_input": {}}
    )

    second_batch = observation_store.list_new_session_observations("s1", after_id=cursor)

    assert len(second_batch) == 1
    assert second_batch[0]["tool_name"] == "Edit"


def test_list_unknown_session_returns_empty(isolated_db):
    observation_store.append_observation(
        {"session_id": "s1", "ts": _now_iso(), "tool_name": "Read", "tool_input": {}}
    )

    assert observation_store.list_new_session_observations("does-not-exist", after_id=0) == []


def test_old_records_pruned_on_append(isolated_db):
    old_ts = (datetime.now(timezone.utc) - timedelta(days=observation_store.RETENTION_DAYS + 1)).isoformat()
    observation_store.append_observation(
        {"session_id": "s1", "ts": old_ts, "tool_name": "Read", "tool_input": {}}
    )
    # 触发保留策略清理：新插入一条新记录
    observation_store.append_observation(
        {"session_id": "s1", "ts": _now_iso(), "tool_name": "Edit", "tool_input": {}}
    )

    results = observation_store.list_new_session_observations("s1", after_id=0)

    assert len(results) == 1
    assert results[0]["tool_name"] == "Edit"


def test_try_claim_session_new_session_starts_at_zero(isolated_db):
    after_id = observation_store.try_claim_session("s1")
    assert after_id == 0


def test_try_claim_session_blocks_while_another_is_processing(isolated_db):
    observation_store.try_claim_session("s1")  # 第一次拿到锁，status 变 processing

    second = observation_store.try_claim_session("s1")

    assert second is None


def test_try_claim_session_reclaims_after_release(isolated_db):
    observation_store.try_claim_session("s1")
    observation_store.release_session("s1", last_processed_id=5)

    after_id = observation_store.try_claim_session("s1")

    assert after_id == 5


def test_try_claim_session_reclaims_stale_processing(isolated_db):
    observation_store.try_claim_session("s1")  # 卡在 processing，模拟上次处理崩溃未释放

    after_id = observation_store.try_claim_session("s1", stale_after_seconds=0)

    assert after_id == 0  # 视为过期，允许重新认领


def test_release_then_reclaim_uses_updated_cursor(isolated_db):
    after_id = observation_store.try_claim_session("s1")
    observation_store.release_session("s1", last_processed_id=3)

    assert observation_store.try_claim_session("s1") == 3
