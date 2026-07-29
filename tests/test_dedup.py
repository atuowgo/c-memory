"""memory_lib.dedup 单元测试。"""
from __future__ import annotations

from memory_lib.dedup import char_jaccard, find_similar_instinct, find_similar_memory


def test_char_jaccard_identical_strings_is_one():
    assert char_jaccard("编辑文件前先阅读该文件", "编辑文件前先阅读该文件") == 1.0


def test_char_jaccard_unrelated_strings_is_low():
    assert char_jaccard("编辑文件前先阅读该文件", "使用git进行版本控制") < 0.3


def test_char_jaccard_empty_string_is_zero():
    assert char_jaccard("", "任意文本") == 0.0
    assert char_jaccard("任意文本", "") == 0.0


def test_find_similar_instinct_merges_same_domain_reworded_trigger():
    candidates = [
        {"id": "a", "domain": "代码编辑", "trigger": "编辑文件前先阅读该文件"},
    ]
    match = find_similar_instinct("编辑文件前先读取文件内容", "代码编辑", candidates)
    assert match is not None
    assert match["id"] == "a"


def test_find_similar_instinct_rejects_cross_domain():
    candidates = [
        {"id": "a", "domain": "版本控制", "trigger": "使用rtk工具封装git命令"},
    ]
    match = find_similar_instinct("使用rtk作为git命令前缀", "工具使用", candidates)
    assert match is None


def test_find_similar_instinct_no_match_returns_none():
    candidates = [
        {"id": "a", "domain": "代码编辑", "trigger": "编辑文件前先阅读该文件"},
    ]
    match = find_similar_instinct("完全不相关的另一个习惯描述", "代码编辑", candidates)
    assert match is None


def test_find_similar_memory_merges_reworded_fact_sharing_keyword():
    candidates = [
        {"id": "a", "keywords": ["gitignore"], "description": "项目使用 gitignore 忽略 env 和 pycache"},
    ]
    match = find_similar_memory(
        "项目用 gitignore 忽略 env pycache 等文件", ["gitignore"], candidates
    )
    assert match is not None
    assert match["id"] == "a"


def test_find_similar_memory_rejects_no_shared_keyword():
    candidates = [
        {"id": "a", "keywords": ["pytest"], "description": "项目使用 pytest 作为测试框架"},
    ]
    match = find_similar_memory("项目使用 pnpm 管理依赖", ["pnpm"], candidates)
    assert match is None


def test_find_similar_memory_no_keywords_returns_none():
    candidates = [
        {"id": "a", "keywords": [], "description": "项目使用 pytest 作为测试框架"},
    ]
    match = find_similar_memory("项目使用 pytest 作为测试框架", [], candidates)
    assert match is None
