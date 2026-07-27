"""统计路径检测器：从会话内 observation 序列里挖掘候选行为模式。

输出格式与 `memory_lib.providers.llm.LLMProvider.analyze()` 返回的
`instincts` 列表项格式一致：{"pattern": str, "domain": str, "evidence": str}，
方便 extract.py 把两条路径的候选结果合并处理。
"""
from __future__ import annotations

import logging
from typing import Callable

logger = logging.getLogger(__name__)

_LOOKBACK = 3
_EDIT_BEFORE_READ_MIN_RATIO = 0.7
_EDIT_BEFORE_READ_MIN_SAMPLES = 2
_GIT_COMMIT_KEYWORDS = ("git commit", "git push")
_MIN_BASH_CALLS = 3


def _edit_before_read_detector(observations: list[dict]) -> list[dict]:
    """编辑前先读取检测器：Edit/Write 前 3 条内是否有对同一文件的 Read。"""
    ordered = sorted(observations, key=lambda o: o.get("ts") or "")

    total = 0
    hit = 0
    for idx, obs in enumerate(ordered):
        if obs.get("tool_name") not in ("Edit", "Write"):
            continue
        file_path = (obs.get("tool_input") or {}).get("file_path")
        if not file_path:
            continue

        total += 1
        window = ordered[max(0, idx - _LOOKBACK):idx]
        if any(
            w.get("tool_name") == "Read"
            and (w.get("tool_input") or {}).get("file_path") == file_path
            for w in window
        ):
            hit += 1

    if total < _EDIT_BEFORE_READ_MIN_SAMPLES:
        return []
    ratio = hit / total
    if ratio < _EDIT_BEFORE_READ_MIN_RATIO:
        return []

    return [
        {
            "pattern": "编辑文件前先 Read 该文件",
            "domain": "file-editing",
            "evidence": f"{hit}/{total} 次编辑前有先 Read",
        }
    ]


def _avoid_auto_commit_detector(observations: list[dict]) -> list[dict]:
    """避免自动提交检测器：会话内跑了不少 Bash，但从未自动 commit/push。"""
    bash_calls = [obs for obs in observations if obs.get("tool_name") == "Bash"]
    total_bash = len(bash_calls)
    if total_bash < _MIN_BASH_CALLS:
        return []

    commit_count = 0
    for obs in bash_calls:
        command = (obs.get("tool_input") or {}).get("command") or ""
        if any(kw in command for kw in _GIT_COMMIT_KEYWORDS):
            commit_count += 1

    if commit_count != 0:
        return []

    return [
        {
            "pattern": "不主动执行 git commit/push",
            "domain": "git-workflow",
            "evidence": f"本次会话 {total_bash} 次 Bash 调用中无 commit/push",
        }
    ]


_DETECTORS: list[Callable[[list[dict]], list[dict]]] = [
    _edit_before_read_detector,
    _avoid_auto_commit_detector,
]


def detect_patterns(observations: list[dict]) -> list[dict]:
    """跑所有硬编码统计检测器，汇总候选行为模式列表。

    单个检测器抛异常时跳过，不影响其他检测器执行。
    """
    results: list[dict] = []
    for detector in _DETECTORS:
        try:
            results.extend(detector(observations))
        except Exception:
            logger.exception("检测器 %s 执行失败，已跳过", getattr(detector, "__name__", detector))
    return results
