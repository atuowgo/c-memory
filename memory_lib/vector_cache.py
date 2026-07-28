"""基于 sqlite-vec 的 embedding 缓存 + KNN 检索。

只用于有稳定输出维度的 provider（如 ArkProvider）——TF-IDF 每次都是对当批文本
重新 fit，向量空间本身不稳定，没法跨调用缓存，继续走 recall.py 里原有的
一次性批量 embed + 手算余弦相似度那条路。

缓存策略：按 memory_id 存向量，配一个 content_hash；下次同一个 memory_id 内容没变
（hash 相同）就直接复用缓存的向量，不重新调 embedding API。相似度检索直接用
sqlite-vec 的 MATCH ... k=? 在 SQL 层完成。

已知限制：memory 被删除后缓存里的孤儿行不会自动清理（数据量小，暂不实现淘汰）。
"""
from __future__ import annotations

import hashlib
import sqlite3

import sqlite_vec
from sqlite_vec import serialize_float32

from memory_lib.storage import MEMORY_DIR

CACHE_FILE = MEMORY_DIR / ".vector_cache.sqlite3"


def _connect(dim: int) -> sqlite3.Connection:
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(CACHE_FILE)
    conn.enable_load_extension(True)
    sqlite_vec.load(conn)
    conn.enable_load_extension(False)
    conn.execute(f"CREATE VIRTUAL TABLE IF NOT EXISTS memory_vectors USING vec0(embedding float[{dim}])")
    conn.execute(
        "CREATE TABLE IF NOT EXISTS memory_vector_meta ("
        "memory_id TEXT PRIMARY KEY, content_hash TEXT NOT NULL, rowid_ref INTEGER NOT NULL UNIQUE)"
    )
    return conn


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _next_rowid(conn: sqlite3.Connection) -> int:
    row = conn.execute("SELECT COALESCE(MAX(rowid_ref), 0) + 1 FROM memory_vector_meta").fetchone()
    return row[0]


def sync_and_search(
    query_vector: list[float],
    memory_items: list[tuple[str, str]],
    embed_one,
    dim: int,
    k: int,
) -> list[str]:
    """同步缓存（新增/变更的 memory 才真正调 embed_one），再用 sqlite-vec 做 KNN。

    memory_items: [(memory_id, cacheable_text), ...]
    embed_one: Callable[[str], list[float]]，只在缓存未命中时才调用（一次一条）。
    返回按相似度降序排列的 memory_id 列表，最多 k 个。embed_one 对单条失败时
    跳过该条，不影响其余候选。
    """
    if not memory_items:
        return []

    conn = _connect(dim)
    try:
        cached = {
            memory_id: (content_hash, rowid_ref)
            for memory_id, content_hash, rowid_ref in conn.execute(
                "SELECT memory_id, content_hash, rowid_ref FROM memory_vector_meta"
            ).fetchall()
        }

        for memory_id, text in memory_items:
            new_hash = _hash(text)
            existing = cached.get(memory_id)
            if existing is not None and existing[0] == new_hash:
                continue  # 缓存命中且内容未变，跳过重新 embed

            try:
                vector = embed_one(text)
            except Exception:
                continue  # 单条 embed 失败不影响其他候选，直接跳过

            if existing is not None:
                rowid_ref = existing[1]
                conn.execute(
                    "UPDATE memory_vectors SET embedding = ? WHERE rowid = ?",
                    [serialize_float32(vector), rowid_ref],
                )
                conn.execute(
                    "UPDATE memory_vector_meta SET content_hash = ? WHERE memory_id = ?",
                    [new_hash, memory_id],
                )
            else:
                rowid_ref = _next_rowid(conn)
                conn.execute(
                    "INSERT INTO memory_vectors(rowid, embedding) VALUES (?, ?)",
                    [rowid_ref, serialize_float32(vector)],
                )
                conn.execute(
                    "INSERT INTO memory_vector_meta(memory_id, content_hash, rowid_ref) VALUES (?, ?, ?)",
                    [memory_id, new_hash, rowid_ref],
                )
            cached[memory_id] = (new_hash, rowid_ref)
        conn.commit()

        # 只在本次候选集合对应的 rowid 范围内检索，避免历史孤儿数据混进结果
        valid_rowids = {cached[mid][1] for mid, _ in memory_items if mid in cached}
        if not valid_rowids:
            return []

        limit = min(k, len(valid_rowids))
        rows = conn.execute(
            "SELECT rowid, distance FROM memory_vectors WHERE embedding MATCH ? AND k = ? ORDER BY distance",
            [serialize_float32(query_vector), max(limit, 1) * 4],  # 多取几个再按 valid_rowids 过滤，防止近邻恰好是孤儿行
        ).fetchall()

        id_by_rowid = {rowid_ref: mid for mid, (h, rowid_ref) in cached.items()}
        ranked = [id_by_rowid[r] for r, _ in rows if r in valid_rowids and r in id_by_rowid]
        return ranked[:k]
    finally:
        conn.close()
