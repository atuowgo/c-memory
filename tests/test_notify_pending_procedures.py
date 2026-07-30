"""hooks.notify_pending_procedures 单元测试：pending procedure 提醒 + skill_asked 置位。"""
from __future__ import annotations

import io
import shutil
import sys
import tempfile
from pathlib import Path

import pytest

import hooks.notify_pending_procedures as notify_pending_procedures
from memory_lib import procedure_store


@pytest.fixture()
def isolated_store(monkeypatch):
    tmp_dir = Path(tempfile.mkdtemp())
    monkeypatch.setattr(procedure_store, "MEMORY_DIR", tmp_dir)
    monkeypatch.setattr(procedure_store, "DB_FILE", tmp_dir / ".procedure_progress.sqlite3")
    monkeypatch.setattr(procedure_store, "PROCEDURES_DIR", tmp_dir / "procedures")
    yield tmp_dir
    shutil.rmtree(tmp_dir, ignore_errors=True)


def test_pending_procedure_is_printed_and_marked_asked(isolated_store, monkeypatch, capsys):
    procedure_store.write_procedure(
        "proc-a",
        {"status": "promoted", "task_type": "调试测试失败", "hit_count": 3},
        "body",
    )
    monkeypatch.setattr(sys, "stdin", io.StringIO("{}"))

    notify_pending_procedures.main()

    out = capsys.readouterr().out
    assert "[procedure-pending]" in out
    assert "调试测试失败" in out
    assert "3" in out
    assert "memory/procedures/proc-a.md" in out

    data = procedure_store.read_procedure("proc-a")
    assert data["skill_asked"] is True


def test_no_pending_procedure_produces_empty_output(isolated_store, monkeypatch, capsys):
    procedure_store.write_procedure("proc-a", {"status": "candidate"}, "body")
    monkeypatch.setattr(sys, "stdin", io.StringIO("{}"))

    notify_pending_procedures.main()

    assert capsys.readouterr().out == ""


def test_already_asked_procedure_is_not_reprinted(isolated_store, monkeypatch, capsys):
    procedure_store.write_procedure(
        "proc-a", {"status": "promoted", "skill_asked": True}, "body"
    )
    monkeypatch.setattr(sys, "stdin", io.StringIO("{}"))

    notify_pending_procedures.main()

    assert capsys.readouterr().out == ""


def test_multiple_pending_procedures_are_all_printed_and_marked(isolated_store, monkeypatch, capsys):
    procedure_store.write_procedure(
        "proc-a", {"status": "promoted", "task_type": "任务A", "hit_count": 2}, "a"
    )
    procedure_store.write_procedure(
        "proc-b", {"status": "promoted", "task_type": "任务B", "hit_count": 5}, "b"
    )
    monkeypatch.setattr(sys, "stdin", io.StringIO("{}"))

    notify_pending_procedures.main()

    out = capsys.readouterr().out
    assert "任务A" in out
    assert "任务B" in out
    assert "memory/procedures/proc-a.md" in out
    assert "memory/procedures/proc-b.md" in out

    assert procedure_store.read_procedure("proc-a")["skill_asked"] is True
    assert procedure_store.read_procedure("proc-b")["skill_asked"] is True
