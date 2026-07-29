"""memory_lib.detectors.detect_patterns 单元测试。"""
from __future__ import annotations

from memory_lib.detectors import detect_patterns


def _domains(candidates: list[dict]) -> set[str]:
    return {c.get("domain") for c in candidates}


# ---------------------------------------------------------------------------
# workflow 检测器（read-before-edit）
# ---------------------------------------------------------------------------


def test_edit_before_read_detected_with_sufficient_coverage():
    observations = [
        {"ts": "1", "tool_name": "Read", "tool_input": {"file_path": "a.py"}},
        {"ts": "2", "tool_name": "Edit", "tool_input": {"file_path": "a.py"}},
        {"ts": "3", "tool_name": "Read", "tool_input": {"file_path": "b.py"}},
        {"ts": "4", "tool_name": "Write", "tool_input": {"file_path": "b.py"}},
    ]
    candidates = detect_patterns(observations)
    assert "workflow" in _domains(candidates)


def test_edit_before_read_not_detected_with_single_sample():
    # 只有 1 次编辑，样本数不足 _EDIT_BEFORE_READ_MIN_SAMPLES(2)
    observations = [
        {"ts": "1", "tool_name": "Read", "tool_input": {"file_path": "a.py"}},
        {"ts": "2", "tool_name": "Edit", "tool_input": {"file_path": "a.py"}},
    ]
    candidates = detect_patterns(observations)
    assert "workflow" not in _domains(candidates)


def test_edit_before_read_not_detected_when_never_read_first():
    observations = [
        {"ts": "1", "tool_name": "Edit", "tool_input": {"file_path": "a.py"}},
        {"ts": "2", "tool_name": "Write", "tool_input": {"file_path": "b.py"}},
        {"ts": "3", "tool_name": "Edit", "tool_input": {"file_path": "c.py"}},
    ]
    candidates = detect_patterns(observations)
    assert "workflow" not in _domains(candidates)


# ---------------------------------------------------------------------------
# git 检测器（no-auto-commit）
# ---------------------------------------------------------------------------


def test_git_workflow_detected_with_enough_bash_calls_and_no_commit():
    observations = [
        {"ts": "1", "tool_name": "Bash", "tool_input": {"command": "ls -la"}},
        {"ts": "2", "tool_name": "Bash", "tool_input": {"command": "pytest tests/"}},
        {"ts": "3", "tool_name": "Bash", "tool_input": {"command": "echo hi"}},
    ]
    candidates = detect_patterns(observations)
    assert "git" in _domains(candidates)


def test_git_workflow_not_detected_when_commit_present():
    observations = [
        {"ts": "1", "tool_name": "Bash", "tool_input": {"command": "ls -la"}},
        {"ts": "2", "tool_name": "Bash", "tool_input": {"command": "pytest tests/"}},
        {"ts": "3", "tool_name": "Bash", "tool_input": {"command": "echo hi"}},
        {"ts": "4", "tool_name": "Bash", "tool_input": {"command": "git commit -m x"}},
        {"ts": "5", "tool_name": "Bash", "tool_input": {"command": "echo bye"}},
    ]
    candidates = detect_patterns(observations)
    assert "git" not in _domains(candidates)


def test_git_workflow_not_detected_with_too_few_bash_calls():
    observations = [
        {"ts": "1", "tool_name": "Bash", "tool_input": {"command": "ls -la"}},
        {"ts": "2", "tool_name": "Bash", "tool_input": {"command": "echo hi"}},
    ]
    candidates = detect_patterns(observations)
    assert "git" not in _domains(candidates)


# ---------------------------------------------------------------------------
# 异常/畸形数据健壮性
# ---------------------------------------------------------------------------


def test_detect_patterns_survives_none_tool_input():
    observations = [
        {"ts": "1", "tool_name": "Edit", "tool_input": None},
        {"ts": "2", "tool_name": "Bash", "tool_input": None},
        {"tool_name": "Read"},  # 缺失 ts 字段
    ]
    candidates = detect_patterns(observations)
    assert isinstance(candidates, list)


def test_detect_patterns_survives_non_dict_tool_input_without_raising():
    # tool_input 是字符串而非 dict，会在检测器内部触发 AttributeError，
    # 应被 detect_patterns 内的 try/except 吞掉，不向外抛出。
    observations = [
        {"ts": "1", "tool_name": "Edit", "tool_input": "not-a-dict"},
        {"ts": "2", "tool_name": "Bash", "tool_input": "not-a-dict-either"},
        {"ts": "3", "tool_name": "Bash", "tool_input": {"command": "ls -la"}},
    ]
    candidates = detect_patterns(observations)
    assert isinstance(candidates, list)


def test_detect_patterns_one_broken_detector_does_not_block_the_other():
    # edit 相关数据畸形（触发内部异常被吞掉），git-workflow 数据正常，
    # 应仍能拿到 git-workflow 候选。
    observations = [
        {"ts": "1", "tool_name": "Edit", "tool_input": "broken"},
        {"ts": "2", "tool_name": "Bash", "tool_input": {"command": "ls -la"}},
        {"ts": "3", "tool_name": "Bash", "tool_input": {"command": "pytest tests/"}},
        {"ts": "4", "tool_name": "Bash", "tool_input": {"command": "echo hi"}},
    ]
    candidates = detect_patterns(observations)
    assert "git" in _domains(candidates)


def test_detect_patterns_empty_input_returns_empty_list():
    assert detect_patterns([]) == []
