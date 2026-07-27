"""轻量语义去重：同一 domain 下用字符级 Jaccard 相似度判断两条 pattern 是否描述同一习惯。

不引入分词/embedding 依赖 —— 中文短句用单字符集合的 Jaccard 相似度已经够用，
比逐字比较宽松（能扛住"阅读"vs"读取"这种同义词替换），又不需要额外依赖。
"""
from __future__ import annotations

SIMILARITY_THRESHOLD = 0.45


def char_jaccard(a: str, b: str) -> float:
    """去掉空白后按单字符集合算 Jaccard 相似度。空字符串返回 0。"""
    set_a = set((a or "").replace(" ", ""))
    set_b = set((b or "").replace(" ", ""))
    if not set_a or not set_b:
        return 0.0
    intersection = len(set_a & set_b)
    union = len(set_a | set_b)
    return intersection / union if union else 0.0


def find_similar_instinct(pattern: str, domain: str, candidates: list[dict]) -> dict | None:
    """在 candidates（同 domain 的已有 instinct）里找相似度最高且 >= 阈值的一条。

    domain 不同的一律跳过（domain 是第一道更可靠的门槛，文本相似度只在同 domain 内做细分）；
    双方 domain 都为空时也跳过（信息不足，宁可不合并，避免跨主题误合并）。
    """
    best = None
    best_score = 0.0
    for cand in candidates:
        cand_domain = cand.get("domain") or ""
        if not domain or not cand_domain or domain != cand_domain:
            continue
        score = char_jaccard(pattern, cand.get("pattern", ""))
        if score >= SIMILARITY_THRESHOLD and score > best_score:
            best = cand
            best_score = score
    return best
