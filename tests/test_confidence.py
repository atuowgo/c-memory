"""memory_lib.confidence.update_confidence 单元测试。"""
from __future__ import annotations

import pytest

from memory_lib.confidence import (
    CONFIDENCE_CAP,
    DEPRECATE_THRESHOLD,
    HIT_DELTA,
    MISS_DELTA,
    PROMOTE_THRESHOLD,
    update_confidence,
)


def test_hit_increments_normally():
    assert update_confidence(0.5, True) == pytest.approx(0.55)


def test_hit_capped_below_cap_still_capped_when_exceeding():
    # 0.88 + 0.05 = 0.93 > CONFIDENCE_CAP(0.9)，应被封顶到 0.9
    assert update_confidence(0.88, True) == pytest.approx(0.9)


def test_hit_at_cap_stays_at_cap():
    assert update_confidence(CONFIDENCE_CAP, True) == pytest.approx(0.9)


def test_miss_decrements_normally():
    assert update_confidence(0.5, False) == pytest.approx(0.45)


def test_promote_threshold_boundary_hit_and_miss():
    # 从刚好等于 PROMOTE_THRESHOLD 的值出发验证升降数值
    assert update_confidence(PROMOTE_THRESHOLD, True) == pytest.approx(
        PROMOTE_THRESHOLD + HIT_DELTA
    )
    assert update_confidence(PROMOTE_THRESHOLD, False) == pytest.approx(
        PROMOTE_THRESHOLD + MISS_DELTA
    )


def test_deprecate_threshold_can_fall_below_via_repeated_miss():
    # 函数本身不做下限 clamp，多次未命中应能持续跌破 DEPRECATE_THRESHOLD 甚至为负
    value = DEPRECATE_THRESHOLD
    for _ in range(20):
        value = update_confidence(value, False)
    assert value < DEPRECATE_THRESHOLD
    assert value < 0
