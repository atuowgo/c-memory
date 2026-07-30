"""memory_lib.procedure_store 单元测试：procedure CRUD + 独立处理游标 + skill 询问辅助。"""
from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

import pytest

from memory_lib import procedure_store


@pytest.fixture()
def isolated_store(monkeypatch):
    tmp_dir = Path(tempfile.mkdtemp())
    monkeypatch.setattr(procedure_store, "MEMORY_DIR", tmp_dir)
    monkeypatch.setattr(procedure_store, "DB_FILE", tmp_dir / ".procedure_progress.sqlite3")
    monkeypatch.setattr(procedure_store, "PROCEDURES_DIR", tmp_dir / "procedures")
    yield tmp_dir
    shutil.rmtree(tmp_dir, ignore_errors=True)


# ---- 游标 claim/release 契约 ----


def test_try_claim_session_new_session_returns_none_cursor(isolated_store):
    claimed, cursor = procedure_store.try_claim_session("s1", "/path/to/s1.jsonl")
    assert claimed is True
    assert cursor is None


def test_try_claim_session_blocks_while_another_is_processing(isolated_store):
    procedure_store.try_claim_session("s1", "/path/to/s1.jsonl")  # 第一次拿到锁，status 变 processing

    claimed, cursor = procedure_store.try_claim_session("s1", "/path/to/s1.jsonl")

    assert claimed is False
    assert cursor is None


def test_release_then_reclaim_uses_updated_cursor(isolated_store):
    procedure_store.try_claim_session("s1", "/path/to/s1.jsonl")
    procedure_store.release_session("s1", last_processed_uuid="uuid-3")

    claimed, cursor = procedure_store.try_claim_session("s1", "/path/to/s1.jsonl")

    assert claimed is True
    assert cursor == "uuid-3"


# ---- procedure CRUD ----


def test_write_and_read_procedure_roundtrip(isolated_store):
    body = "Step 1: do something\nStep 2: do another thing"
    procedure_store.write_procedure(
        "proc-a", {"title": "Test Procedure", "status": "candidate"}, body
    )

    data = procedure_store.read_procedure("proc-a")

    assert data is not None
    assert data["id"] == "proc-a"
    assert data["title"] == "Test Procedure"
    assert data["status"] == "candidate"
    assert data["body"].strip() == body.strip()


def test_read_procedure_returns_none_for_missing_id(isolated_store):
    assert procedure_store.read_procedure("does-not-exist") is None


def test_list_procedures_returns_multiple(isolated_store):
    procedure_store.write_procedure("proc-a", {"title": "A"}, "body a")
    procedure_store.write_procedure("proc-b", {"title": "B"}, "body b")

    procedures = procedure_store.list_procedures()

    ids = {p["id"] for p in procedures}
    assert ids == {"proc-a", "proc-b"}


# ---- skill 询问辅助 ----


def test_list_pending_skill_prompts_filters_correctly(isolated_store):
    procedure_store.write_procedure("proc-a", {"status": "promoted"}, "a")  # 应被选中
    procedure_store.write_procedure(
        "proc-b", {"status": "promoted", "skill_asked": True}, "b"
    )  # 已问过，不选
    procedure_store.write_procedure("proc-c", {"status": "candidate"}, "c")  # 未晋升，不选

    pending = procedure_store.list_pending_skill_prompts()

    assert [p["id"] for p in pending] == ["proc-a"]


def test_mark_skill_asked_updates_flag_and_removes_from_pending(isolated_store):
    procedure_store.write_procedure("proc-a", {"status": "promoted"}, "a")

    procedure_store.mark_skill_asked("proc-a")

    data = procedure_store.read_procedure("proc-a")
    assert data["skill_asked"] is True
    assert procedure_store.list_pending_skill_prompts() == []


def test_mark_skill_asked_on_missing_id_is_noop(isolated_store):
    procedure_store.mark_skill_asked("does-not-exist")  # 不应抛异常
