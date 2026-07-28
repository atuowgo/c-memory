"""memory/ 目录下 instincts/memories/rules 的读写与 frontmatter 文件管理。

观测记录（observations）改用 SQLite 存储，见 memory_lib/observation_store.py——
这类数据不需要 git 追踪，用 SQLite 换掉手写的 jsonl 轮转逻辑更省心。
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import frontmatter

from memory_lib.confidence import PROMOTE_THRESHOLD, RULES_LIMIT

MEMORY_DIR = Path(__file__).resolve().parent.parent / "memory"

DEDUP_STATE_FILE = MEMORY_DIR / ".dedup_state.json"
INSTINCTS_DIR = MEMORY_DIR / "instincts"
INSTINCTS_ARCHIVE_DIR = INSTINCTS_DIR / "archive"
MEMORIES_DIR = MEMORY_DIR / "memories"
RULES_DIR = MEMORY_DIR / "rules"
RULES_FILE = RULES_DIR / "auto-evolved.md"


def ensure_dirs() -> None:
    for d in (
        MEMORY_DIR,
        INSTINCTS_DIR,
        INSTINCTS_ARCHIVE_DIR,
        MEMORIES_DIR,
        RULES_DIR,
    ):
        d.mkdir(parents=True, exist_ok=True)


def read_dedup_state() -> dict:
    if not DEDUP_STATE_FILE.exists():
        return {}
    try:
        return json.loads(DEDUP_STATE_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def write_dedup_state(state: dict) -> None:
    ensure_dirs()
    DEDUP_STATE_FILE.write_text(
        json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _instinct_path(instinct_id: str) -> Path:
    return INSTINCTS_DIR / f"{instinct_id}.md"


def read_instinct(instinct_id: str) -> dict | None:
    path = _instinct_path(instinct_id)
    if not path.exists():
        return None
    post = frontmatter.load(path)
    data = dict(post.metadata)
    data.setdefault("id", instinct_id)
    data["body"] = post.content
    return data


def write_instinct(instinct_id: str, frontmatter_dict: dict, body: str) -> None:
    ensure_dirs()
    metadata = dict(frontmatter_dict)
    metadata.setdefault("id", instinct_id)
    post = frontmatter.Post(body, **metadata)
    with open(_instinct_path(instinct_id), "w", encoding="utf-8") as f:
        frontmatter.dump(post, f)


def list_instincts(include_deprecated: bool = True) -> list[dict]:
    ensure_dirs()
    results = []
    for path in sorted(INSTINCTS_DIR.glob("*.md")):
        post = frontmatter.load(path)
        data = dict(post.metadata)
        data.setdefault("id", path.stem)
        data["body"] = post.content
        if not include_deprecated and data.get("deprecated"):
            continue
        results.append(data)
    return results


def _memory_path(memory_id: str) -> Path:
    return MEMORIES_DIR / f"{memory_id}.md"


def write_memory(memory_id: str, frontmatter_dict: dict, body: str) -> None:
    ensure_dirs()
    metadata = dict(frontmatter_dict)
    metadata.setdefault("id", memory_id)
    post = frontmatter.Post(body, **metadata)
    with open(_memory_path(memory_id), "w", encoding="utf-8") as f:
        frontmatter.dump(post, f)


def list_memories() -> list[dict]:
    ensure_dirs()
    results = []
    for path in sorted(MEMORIES_DIR.glob("*.md")):
        post = frontmatter.load(path)
        data = dict(post.metadata)
        data.setdefault("id", path.stem)
        data["body"] = post.content
        results.append(data)
    return results


def _filter_promoted(instincts: list[dict]) -> list[dict]:
    """confidence>=PROMOTE_THRESHOLD 且未 deprecated 的活跃 instinct，按 confidence 降序，最多 RULES_LIMIT 条。"""
    candidates = [
        inst
        for inst in instincts
        if not inst.get("deprecated") and inst.get("confidence", 0) >= PROMOTE_THRESHOLD
    ]
    candidates.sort(key=lambda inst: inst.get("confidence", 0), reverse=True)
    return candidates[:RULES_LIMIT]


def list_promoted_instincts() -> list[dict]:
    """供 SessionStart 注入使用：已晋升为规则的活跃 instinct 列表。"""
    return _filter_promoted(list_instincts(include_deprecated=False))


def regenerate_rules_file(instincts: list[dict]) -> None:
    """整体重写 rules/auto-evolved.md：confidence>=PROMOTE_THRESHOLD 且未 deprecated，
    按 confidence 降序，最多 RULES_LIMIT 条。
    """
    ensure_dirs()
    candidates = _filter_promoted(instincts)

    lines = [
        "# 自动演化规则（自动生成，请勿手工编辑）",
        "",
        f"<!-- 更新时间: {datetime.now().isoformat()} -->",
        "",
    ]
    for inst in candidates:
        pattern = inst.get("pattern", inst.get("id", ""))
        confidence = inst.get("confidence", 0)
        domain = inst.get("domain", "")
        lines.append(f"- **{pattern}** (confidence: {confidence:.2f}, domain: {domain})")

    RULES_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
