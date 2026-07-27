"""置信度演化参数与更新逻辑。"""
from __future__ import annotations

INITIAL_CONFIDENCE = 0.5
HIT_DELTA = 0.05
MISS_DELTA = -0.05
CONFIDENCE_CAP = 0.9
PROMOTE_THRESHOLD = 0.7
DEPRECATE_THRESHOLD = 0.55
RULES_LIMIT = 30


def update_confidence(current: float, hit: bool) -> float:
    """命中: min(current + HIT_DELTA, CONFIDENCE_CAP)；未命中: current + MISS_DELTA。

    不在此处 clamp 下限，是否 deprecate 由调用方根据 DEPRECATE_THRESHOLD 判断。
    """
    if hit:
        return min(current + HIT_DELTA, CONFIDENCE_CAP)
    return current + MISS_DELTA
