"""memory_lib.storage 单元测试：晋升规则筛选、规则文件重写。"""
from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

import pytest

from memory_lib import storage


@pytest.fixture()
def isolated_memory_dir(monkeypatch):
    tmp_dir = Path(tempfile.mkdtemp())
    monkeypatch.setattr(storage, "MEMORY_DIR", tmp_dir)
    monkeypatch.setattr(storage, "INSTINCTS_DIR", tmp_dir / "instincts")
    monkeypatch.setattr(storage, "INSTINCTS_ARCHIVE_DIR", tmp_dir / "instincts" / "archive")
    monkeypatch.setattr(storage, "MEMORIES_DIR", tmp_dir / "memories")
    monkeypatch.setattr(storage, "RULES_DIR", tmp_dir / "rules")
    monkeypatch.setattr(storage, "RULES_FILE", tmp_dir / "rules" / "auto-evolved.md")
    monkeypatch.setattr(storage, "DEDUP_STATE_FILE", tmp_dir / ".dedup_state.json")
    yield tmp_dir
    shutil.rmtree(tmp_dir, ignore_errors=True)


def test_list_promoted_instincts_filters_by_confidence_and_deprecated(isolated_memory_dir):
    storage.write_instinct(
        "high-confidence", {"domain": "d", "trigger": "p1", "confidence": 0.8, "deprecated": False}, "evidence"
    )
    storage.write_instinct(
        "low-confidence", {"domain": "d", "trigger": "p2", "confidence": 0.5, "deprecated": False}, "evidence"
    )
    storage.write_instinct(
        "deprecated-high", {"domain": "d", "trigger": "p3", "confidence": 0.9, "deprecated": True}, "evidence"
    )

    promoted = storage.list_promoted_instincts()

    assert [inst["id"] for inst in promoted] == ["high-confidence"]


def test_list_promoted_instincts_sorted_by_confidence_desc(isolated_memory_dir):
    storage.write_instinct("a", {"domain": "d", "trigger": "p", "confidence": 0.75, "deprecated": False}, "e")
    storage.write_instinct("b", {"domain": "d", "trigger": "p", "confidence": 0.9, "deprecated": False}, "e")

    promoted = storage.list_promoted_instincts()

    assert [inst["id"] for inst in promoted] == ["b", "a"]


def test_list_promoted_instincts_empty_when_none_qualify(isolated_memory_dir):
    storage.write_instinct("a", {"domain": "d", "trigger": "p", "confidence": 0.3, "deprecated": False}, "e")

    assert storage.list_promoted_instincts() == []
