"""memory_lib.vector_cache 单元测试：验证内容不变就不重复 embed，KNN 排序正确。"""
from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

import pytest

from memory_lib import vector_cache


@pytest.fixture()
def isolated_cache(monkeypatch):
    tmp_dir = Path(tempfile.mkdtemp())
    cache_file = tmp_dir / ".vector_cache.sqlite3"
    monkeypatch.setattr(vector_cache, "MEMORY_DIR", tmp_dir)
    monkeypatch.setattr(vector_cache, "CACHE_FILE", cache_file)
    yield tmp_dir
    shutil.rmtree(tmp_dir, ignore_errors=True)


def _counting_embedder(vectors_by_text):
    calls = []

    def embed_one(text):
        calls.append(text)
        return vectors_by_text[text]

    return embed_one, calls


def test_knn_returns_nearest_first(isolated_cache):
    vectors = {
        "near the query": [0.1, 0.1, 0.1, 0.1],
        "also near": [0.15, 0.12, 0.09, 0.11],
        "far away": [0.9, 0.9, 0.9, 0.9],
    }
    embed_one, calls = _counting_embedder(vectors)
    items = [("mem-a", "near the query"), ("mem-b", "far away"), ("mem-c", "also near")]

    result = vector_cache.sync_and_search([0.12, 0.11, 0.10, 0.10], items, embed_one, dim=4, k=2)

    assert result == ["mem-a", "mem-c"]
    assert len(calls) == 3


def test_unchanged_content_is_not_reembedded(isolated_cache):
    vectors = {"stable text": [0.2, 0.2, 0.2, 0.2]}
    embed_one, calls = _counting_embedder(vectors)
    items = [("mem-a", "stable text")]

    vector_cache.sync_and_search([0.2, 0.2, 0.2, 0.2], items, embed_one, dim=4, k=5)
    assert len(calls) == 1

    # 第二次调用，内容没变，不应该再触发 embed_one
    vector_cache.sync_and_search([0.2, 0.2, 0.2, 0.2], items, embed_one, dim=4, k=5)
    assert len(calls) == 1


def test_changed_content_triggers_reembed(isolated_cache):
    vectors = {"version 1": [0.1, 0.1, 0.1, 0.1], "version 2": [0.8, 0.8, 0.8, 0.8]}
    embed_one, calls = _counting_embedder(vectors)

    vector_cache.sync_and_search([0.1, 0.1, 0.1, 0.1], [("mem-a", "version 1")], embed_one, dim=4, k=5)
    assert calls == ["version 1"]

    vector_cache.sync_and_search([0.8, 0.8, 0.8, 0.8], [("mem-a", "version 2")], embed_one, dim=4, k=5)
    assert calls == ["version 1", "version 2"]


def test_single_item_embed_failure_is_skipped(isolated_cache):
    def flaky_embed_one(text):
        if text == "broken":
            raise RuntimeError("boom")
        return [0.3, 0.3, 0.3, 0.3]

    items = [("mem-a", "broken"), ("mem-b", "fine")]
    result = vector_cache.sync_and_search([0.3, 0.3, 0.3, 0.3], items, flaky_embed_one, dim=4, k=5)

    assert result == ["mem-b"]


def test_empty_memory_items_returns_empty(isolated_cache):
    assert vector_cache.sync_and_search([0.1, 0.1], [], lambda t: [0.1, 0.1], dim=2, k=5) == []
