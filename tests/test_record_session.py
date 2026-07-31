"""hooks.record_session 单元测试：最近会话记录的新建/更新/裁剪/摘要截断。"""
from __future__ import annotations

import io
import json
import shutil
import sys
import tempfile
from pathlib import Path

import pytest

import hooks.record_session as record_session


@pytest.fixture()
def isolated_store(monkeypatch):
    tmp_dir = Path(tempfile.mkdtemp())
    monkeypatch.setattr(record_session, "MEMORY_DIR", tmp_dir)
    monkeypatch.setattr(record_session, "DATA_FILE", tmp_dir / ".recent-sessions.json")
    monkeypatch.setattr(record_session, "RENDERED_FILE", tmp_dir / "recent-sessions.md")
    monkeypatch.setattr(record_session, "PROJECT_SUMMARY_FILE", tmp_dir / "project-summary.md")
    yield tmp_dir
    shutil.rmtree(tmp_dir, ignore_errors=True)


def _run_main(monkeypatch, session_id):
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps({"session_id": session_id})))
    record_session.main()


def test_new_session_creates_entry(isolated_store, monkeypatch):
    isolated_store.mkdir(parents=True, exist_ok=True)
    record_session.PROJECT_SUMMARY_FILE.write_text("项目摘要内容", encoding="utf-8")

    _run_main(monkeypatch, "session-1")

    data = json.loads(record_session.DATA_FILE.read_text(encoding="utf-8"))
    assert len(data) == 1
    assert data[0]["session_id"] == "session-1"

    rendered = record_session.RENDERED_FILE.read_text(encoding="utf-8")
    assert "session-1" in rendered
    assert "项目摘要内容" in rendered


def test_existing_session_is_updated_not_duplicated(isolated_store, monkeypatch):
    record_session._write_entries(
        [
            {
                "session_id": "session-1",
                "last_exit_ts": "2020-01-01T00:00:00+00:00",
                "summary_excerpt": "旧摘要",
            }
        ]
    )

    _run_main(monkeypatch, "session-1")

    data = json.loads(record_session.DATA_FILE.read_text(encoding="utf-8"))
    matching = [e for e in data if e["session_id"] == "session-1"]
    assert len(matching) == 1
    assert matching[0]["last_exit_ts"] > "2020-01-01T00:00:00+00:00"


def test_entries_capped_at_ten_most_recent(isolated_store, monkeypatch):
    entries = [
        {
            "session_id": f"old-{i}",
            "last_exit_ts": f"2020-01-{i + 1:02d}T00:00:00+00:00",
            "summary_excerpt": "",
        }
        for i in range(12)
    ]
    record_session._write_entries(entries)

    _run_main(monkeypatch, "new-session")

    data = json.loads(record_session.DATA_FILE.read_text(encoding="utf-8"))
    assert len(data) == 10

    session_ids = {e["session_id"] for e in data}
    assert "new-session" in session_ids
    # 最旧的 old-0, old-1, old-2 应被裁掉（12 条旧的 + 1 条新的 = 13，只保留最新 10 条）
    assert "old-0" not in session_ids
    assert "old-1" not in session_ids
    assert "old-2" not in session_ids
    assert "old-3" in session_ids
    assert "old-11" in session_ids


def test_missing_project_summary_file_results_in_empty_excerpt(isolated_store, monkeypatch):
    _run_main(monkeypatch, "session-1")

    data = json.loads(record_session.DATA_FILE.read_text(encoding="utf-8"))
    assert data[0]["summary_excerpt"] == ""


def test_summary_excerpt_is_truncated(isolated_store, monkeypatch):
    isolated_store.mkdir(parents=True, exist_ok=True)
    record_session.PROJECT_SUMMARY_FILE.write_text("x" * 500, encoding="utf-8")

    _run_main(monkeypatch, "session-1")

    data = json.loads(record_session.DATA_FILE.read_text(encoding="utf-8"))
    assert len(data[0]["summary_excerpt"]) <= 200


def test_missing_session_id_is_noop(isolated_store, monkeypatch):
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps({})))

    record_session.main()

    assert not record_session.DATA_FILE.exists()
    assert not record_session.RENDERED_FILE.exists()
