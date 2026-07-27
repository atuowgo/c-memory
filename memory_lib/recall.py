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


def recall_top_k(query: str, memories: list[dict], embedding_provider, k: int = 5) -> list[dict]:
    """用余弦相似度对 memories 排序，返回原始 memory dict 列表，取前 k 条。"""
    if not memories:
        return []

    texts = [f"{mem.get('body', '')} {' '.join(mem.get('keywords', []))}" for mem in memories]

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
