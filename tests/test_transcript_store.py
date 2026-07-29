"""memory_lib.transcript_store 单元测试：非阻塞并发认领/释放/孤儿 session 扫描。"""
from __future__ import annotations

import shutil
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from memory_lib import transcript_store


@pytest.fixture()
def isolated_db(monkeypatch):
    tmp_dir = Path(tempfile.mkdtemp())
    monkeypatch.setattr(transcript_store, "MEMORY_DIR", tmp_dir)
    monkeypatch.setattr(transcript_store, "DB_FILE", tmp_dir / ".transcript_progress.sqlite3")
    yield tmp_dir
    shutil.rmtree(tmp_dir, ignore_errors=True)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def test_try_claim_session_new_session_returns_none_cursor(isolated_db):
    claimed, cursor = transcript_store.try_claim_session("s1", "/path/to/s1.jsonl")
    assert claimed is True
    assert cursor is None


def test_try_claim_session_records_transcript_path(isolated_db):
    transcript_store.try_claim_session("s1", "/path/to/s1.jsonl")

    conn = transcript_store._connect()
    try:
        row = conn.execute(
            "SELECT transcript_path FROM session_progress WHERE session_id = ?", ("s1",)
        ).fetchone()
    finally:
        conn.close()

    assert row[0] == "/path/to/s1.jsonl"


def test_try_claim_session_blocks_while_another_is_processing(isolated_db):
    transcript_store.try_claim_session("s1", "/path/to/s1.jsonl")  # 第一次拿到锁，status 变 processing

    claimed, cursor = transcript_store.try_claim_session("s1", "/path/to/s1.jsonl")

    assert claimed is False
    assert cursor is None


def test_try_claim_session_reclaims_after_release(isolated_db):
    transcript_store.try_claim_session("s1", "/path/to/s1.jsonl")
    transcript_store.release_session("s1", last_processed_uuid="uuid-5")

    claimed, cursor = transcript_store.try_claim_session("s1", "/path/to/s1.jsonl")

    assert claimed is True
    assert cursor == "uuid-5"


def test_try_claim_session_reclaims_stale_processing(isolated_db):
    transcript_store.try_claim_session("s1", "/path/to/s1.jsonl")  # 卡在 processing，模拟上次处理崩溃未释放

    claimed, cursor = transcript_store.try_claim_session("s1", "/path/to/s1.jsonl", stale_after_seconds=0)

    assert claimed is True  # 视为过期，允许重新认领
    assert cursor is None  # 之前从未真正 release 过，游标仍是 None


def test_release_then_reclaim_uses_updated_cursor(isolated_db):
    transcript_store.try_claim_session("s1", "/path/to/s1.jsonl")
    transcript_store.release_session("s1", last_processed_uuid="uuid-3")

    claimed, cursor = transcript_store.try_claim_session("s1", "/path/to/s1.jsonl")
    assert claimed is True
    assert cursor == "uuid-3"


def test_find_orphan_sessions_finds_stale_processing_other_session(isolated_db):
    transcript_store.try_claim_session("orphan", "/path/to/orphan.jsonl")
    # 手动把 updated_at 拨到很久以前，模拟超时
    conn = transcript_store._connect()
    try:
        stale_ts = (datetime.now(timezone.utc) - timedelta(seconds=1000)).isoformat()
        conn.execute(
            "UPDATE session_progress SET updated_at = ? WHERE session_id = ?", (stale_ts, "orphan")
        )
        conn.commit()
    finally:
        conn.close()

    orphans = transcript_store.find_orphan_sessions("current", stale_after_seconds=600)

    assert len(orphans) == 1
    assert orphans[0]["session_id"] == "orphan"
    assert orphans[0]["transcript_path"] == "/path/to/orphan.jsonl"


def test_find_orphan_sessions_excludes_self(isolated_db):
    transcript_store.try_claim_session("current", "/path/to/current.jsonl")
    conn = transcript_store._connect()
    try:
        stale_ts = (datetime.now(timezone.utc) - timedelta(seconds=1000)).isoformat()
        conn.execute(
            "UPDATE session_progress SET updated_at = ? WHERE session_id = ?", (stale_ts, "current")
        )
        conn.commit()
    finally:
        conn.close()

    orphans = transcript_store.find_orphan_sessions("current", stale_after_seconds=600)

    assert orphans == []


def test_find_orphan_sessions_excludes_non_stale_processing(isolated_db):
    transcript_store.try_claim_session("fresh", "/path/to/fresh.jsonl")  # updated_at 刚刚，未超时

    orphans = transcript_store.find_orphan_sessions("current", stale_after_seconds=600)

    assert orphans == []


def test_find_orphan_sessions_excludes_idle_sessions(isolated_db):
    transcript_store.try_claim_session("idle-one", "/path/to/idle.jsonl")
    transcript_store.release_session("idle-one", last_processed_uuid="uuid-1")
    conn = transcript_store._connect()
    try:
        stale_ts = (datetime.now(timezone.utc) - timedelta(seconds=1000)).isoformat()
        conn.execute(
            "UPDATE session_progress SET updated_at = ? WHERE session_id = ?", (stale_ts, "idle-one")
        )
        conn.commit()
    finally:
        conn.close()

    orphans = transcript_store.find_orphan_sessions("current", stale_after_seconds=600)

    assert orphans == []
