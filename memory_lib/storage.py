"""memory/ 目录下所有数据的读写、轮转、frontmatter 文件管理。"""
from __future__ import annotations

import json
import math
from datetime import datetime, timedelta
from pathlib import Path

import frontmatter

from memory_lib.confidence import PROMOTE_THRESHOLD, RULES_LIMIT

MEMORY_DIR = Path(__file__).resolve().parent.parent / "memory"

OBSERVATIONS_FILE = MEMORY_DIR / "observations.jsonl"
OBSERVATIONS_ARCHIVE_DIR = MEMORY_DIR / "observations"
DEDUP_STATE_FILE = MEMORY_DIR / ".dedup_state.json"
INSTINCTS_DIR = MEMORY_DIR / "instincts"
INSTINCTS_ARCHIVE_DIR = INSTINCTS_DIR / "archive"
MEMORIES_DIR = MEMORY_DIR / "memories"
RULES_DIR = MEMORY_DIR / "rules"
RULES_FILE = RULES_DIR / "auto-evolved.md"

ROTATE_MAX_BYTES = 5 * 1024 * 1024
ROTATE_MAX_LINES = 8000
RETENTION_DAYS = 30
NO_TS_KEEP_RATIO = 0.3


def ensure_dirs() -> None:
    for d in (
        MEMORY_DIR,
        OBSERVATIONS_ARCHIVE_DIR,
        INSTINCTS_DIR,
        INSTINCTS_ARCHIVE_DIR,
        MEMORIES_DIR,
        RULES_DIR,
    ):
        d.mkdir(parents=True, exist_ok=True)


def _parse_ts(ts_str: str):
    if not ts_str:
        return None
    try:
        return datetime.fromisoformat(ts_str.replace("Z", "+00:00")).replace(tzinfo=None)
    except (ValueError, AttributeError):
        return None


def rotate_if_needed() -> None:
    """observations.jsonl 超过 5MB 或 8000 行时，整体归档到 observations/{YYYY-MM}.jsonl，
    并从原内容中筛选出最近 30 天的记录重新写回主文件。
    """
    ensure_dirs()
    if not OBSERVATIONS_FILE.exists():
        return

    size = OBSERVATIONS_FILE.stat().st_size
    raw_lines = [
        line for line in OBSERVATIONS_FILE.read_text(encoding="utf-8").splitlines() if line.strip()
    ]
    line_count = len(raw_lines)

    if size <= ROTATE_MAX_BYTES and line_count <= ROTATE_MAX_LINES:
        return

    # 1. 整个文件归档到当月归档文件（追加）
    archive_name = datetime.now().strftime("%Y-%m") + ".jsonl"
    archive_path = OBSERVATIONS_ARCHIVE_DIR / archive_name
    with open(archive_path, "a", encoding="utf-8") as f:
        for line in raw_lines:
            f.write(line + "\n")

    # 2. 解析每一行，区分"有可解析时间字段"与"无时间字段"两类
    parsed = []  # (line, record_or_none, ts_or_none)
    for line in raw_lines:
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            record = None
        ts = _parse_ts(record.get("ts")) if isinstance(record, dict) else None
        parsed.append((line, record, ts))

    no_ts_indices = [i for i, (_, record, ts) in enumerate(parsed) if record is not None and ts is None]
    no_ts_keep_count = math.ceil(len(no_ts_indices) * NO_TS_KEEP_RATIO) if no_ts_indices else 0
    no_ts_keep_set = set(no_ts_indices[-no_ts_keep_count:]) if no_ts_keep_count else set()

    cutoff = datetime.now() - timedelta(days=RETENTION_DAYS)
    kept_lines = []
    for i, (line, record, ts) in enumerate(parsed):
        if record is None:
            continue
        if ts is not None:
            if ts >= cutoff:
                kept_lines.append(line)
        elif i in no_ts_keep_set:
            kept_lines.append(line)

    with open(OBSERVATIONS_FILE, "w", encoding="utf-8") as f:
        for line in kept_lines:
            f.write(line + "\n")


def append_observation(record: dict) -> None:
    ensure_dirs()
    rotate_if_needed()
    with open(OBSERVATIONS_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


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
    with open(_instinct_path(instinct_id), "wb") as f:
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
    with open(_memory_path(memory_id), "wb") as f:
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


def regenerate_rules_file(instincts: list[dict]) -> None:
    """整体重写 rules/auto-evolved.md：confidence>=PROMOTE_THRESHOLD 且未 deprecated，
    按 confidence 降序，最多 RULES_LIMIT 条。
    """
    ensure_dirs()
    candidates = [
        inst
        for inst in instincts
        if not inst.get("deprecated") and inst.get("confidence", 0) >= PROMOTE_THRESHOLD
    ]
    candidates.sort(key=lambda inst: inst.get("confidence", 0), reverse=True)
    candidates = candidates[:RULES_LIMIT]

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
