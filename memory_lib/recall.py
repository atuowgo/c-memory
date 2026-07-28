"""会话启动时的记忆召回：构造查询 + 向量化 + 余弦相似度 Top-K。"""
from __future__ import annotations

import logging
import subprocess
from pathlib import Path

from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger(__name__)

_GIT_LOG_TIMEOUT_SECONDS = 5


def build_query(cwd: str) -> str:
    """项目名 + 最近 3 条 git commit 拼成查询文本。git 失败时只返回项目名部分。"""
    project_name = Path(cwd).name
    lines = [f"项目: {project_name}"]

    try:
        result = subprocess.run(
            ["git", "log", "--oneline", "-3"],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=_GIT_LOG_TIMEOUT_SECONDS,
        )
        if result.returncode == 0 and result.stdout.strip():
            lines.append("最近提交:")
            lines.append(result.stdout.strip())
    except (OSError, subprocess.SubprocessError) as exc:
        logger.warning("build_query 获取 git log 失败: %s", exc)

    return "\n".join(lines)


def _cacheable_text(mem: dict) -> str:
    return f"{mem.get('body', '')} {' '.join(mem.get('keywords', []))}"


def recall_top_k(query: str, memories: list[dict], embedding_provider, k: int = 5) -> list[dict]:
    """对 memories 排序，返回原始 memory dict 列表，取前 k 条。

    embedding_provider.SUPPORTS_CACHE 为真（如 ArkProvider，输出维度固定）时，
    走 vector_cache：只有新增/内容变更的 memory 才真正调 embed，检索用 sqlite-vec
    的 SQL 层 KNN。不支持缓存的 provider（如 TfidfProvider，每次现场 fit，向量
    空间不稳定）退回原来的一次性批量 embed + 手算余弦相似度。
    """
    if not memories:
        return []

    if getattr(embedding_provider, "SUPPORTS_CACHE", False):
        return _recall_top_k_cached(query, memories, embedding_provider, k)
    return _recall_top_k_batch(query, memories, embedding_provider, k)


def _recall_top_k_cached(query: str, memories: list[dict], embedding_provider, k: int) -> list[dict]:
    from memory_lib.vector_cache import sync_and_search

    try:
        query_vector = embedding_provider.embed([query])[0]
    except Exception:
        logger.exception("recall_top_k 查询向量计算失败")
        return []

    memory_items = [(mem["id"], _cacheable_text(mem)) for mem in memories if mem.get("id")]

    def embed_one(text: str) -> list[float]:
        return embedding_provider.embed([text])[0]

    try:
        ranked_ids = sync_and_search(query_vector, memory_items, embed_one, embedding_provider.dim, k)
    except Exception:
        logger.exception("recall_top_k 向量缓存检索失败")
        return []

    by_id = {mem["id"]: mem for mem in memories}
    return [by_id[mid] for mid in ranked_ids if mid in by_id]


def _recall_top_k_batch(query: str, memories: list[dict], embedding_provider, k: int) -> list[dict]:
    texts = [_cacheable_text(mem) for mem in memories]

    try:
        vectors = embedding_provider.embed([query] + texts)
    except Exception:
        logger.exception("recall_top_k embedding 调用失败")
        return []

    if not vectors or len(vectors) != len(memories) + 1:
        return []

    query_vector = [vectors[0]]
    memory_vectors = vectors[1:]

    similarities = cosine_similarity(query_vector, memory_vectors)[0]

    ranked = sorted(
        zip(memories, similarities), key=lambda pair: pair[1], reverse=True
    )
    return [mem for mem, _ in ranked[:k]]
