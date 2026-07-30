"""hooks.mine_procedures 单元测试：端到端流程挖掘（transcript 真跑解析，SQLite/文件系统/LLM 全部隔离）。"""
from __future__ import annotations

import io
import json
import shutil
import sys
import tempfile
from pathlib import Path

import pytest

import hooks.mine_procedures as mine_procedures
from memory_lib import observation_store, procedure_store
from memory_lib.confidence import INITIAL_CONFIDENCE, MISS_DELTA, update_confidence
from memory_lib.providers import LLMProviderError


@pytest.fixture()
def isolated_env(monkeypatch):
    tmp_dir = Path(tempfile.mkdtemp())
    monkeypatch.setattr(observation_store, "MEMORY_DIR", tmp_dir)
    monkeypatch.setattr(observation_store, "DB_FILE", tmp_dir / ".observations.sqlite3")
    monkeypatch.setattr(procedure_store, "MEMORY_DIR", tmp_dir)
    monkeypatch.setattr(procedure_store, "DB_FILE", tmp_dir / ".procedure_progress.sqlite3")
    monkeypatch.setattr(procedure_store, "PROCEDURES_DIR", tmp_dir / "procedures")
    yield tmp_dir
    shutil.rmtree(tmp_dir, ignore_errors=True)


def _user_record(uuid: str, content, timestamp: str) -> dict:
    return {"type": "user", "message": {"role": "user", "content": content}, "uuid": uuid, "timestamp": timestamp}


def _assistant_record(uuid: str, text: str) -> dict:
    return {
        "type": "assistant",
        "message": {"role": "assistant", "content": [{"type": "text", "text": text}]},
        "uuid": uuid,
    }


def _write_jsonl(tmp_path, records) -> str:
    path = tmp_path / "transcript.jsonl"
    lines = [json.dumps(r, ensure_ascii=False) for r in records]
    path.write_text("\n".join(lines), encoding="utf-8")
    return str(path)


def _obs(session_id: str, ts: str, tool_name: str = "Read", tool_input: dict | None = None) -> None:
    observation_store.append_observation(
        {
            "session_id": session_id,
            "ts": ts,
            "tool_name": tool_name,
            "tool_input": tool_input or {"file_path": "a.py"},
        }
    )


class _FakeProvider:
    """按 assistant_text 分发结果的伪 LLM provider，记录每次调用参数（含下一轮反馈）。"""

    def __init__(self, result=None, results_by_assistant: dict | None = None, raise_error: bool = False):
        self.calls: list[tuple[str, str, str]] = []
        self._result = result
        self._results_by_assistant = results_by_assistant or {}
        self._raise_error = raise_error

    def mine_procedure(self, steps_summary: str, assistant_text: str, next_user_feedback: str = ""):
        self.calls.append((steps_summary, assistant_text, next_user_feedback))
        if self._raise_error:
            raise LLMProviderError("模拟 LLM 调用失败")
        if assistant_text in self._results_by_assistant:
            return self._results_by_assistant[assistant_text]
        return self._result


def _run_main(monkeypatch, session_id: str, transcript_path: str) -> None:
    payload = json.dumps({"session_id": session_id, "transcript_path": transcript_path})
    monkeypatch.setattr(sys, "stdin", io.StringIO(payload))
    mine_procedures.main()


# ---- 场景 1：新建候选（须有下一轮收尾对话，episode 才会被处理） ----


def test_new_candidate_created_with_initial_confidence(isolated_env, monkeypatch):
    session_id = "sess-1"
    records = [
        _user_record("u1", "帮我把md文档转成html", "2026-07-30T10:00:00Z"),
        _assistant_record("a1", "写了一份md文档并转成了html"),
        _user_record("u2", "好的谢谢", "2026-07-30T10:05:00Z"),
        _assistant_record("a2", "不客气"),
    ]
    transcript_path = _write_jsonl(isolated_env, records)
    for i in range(3):
        _obs(session_id, f"2026-07-30T10:00:0{i + 1}Z")

    fake_provider = _FakeProvider(
        result={
            "id": "write-doc-html",
            "task_type": "写文档转html",
            "steps": ["写md", "转html", "检查"],
            "note": "",
            "is_successful": True,
        }
    )
    monkeypatch.setattr(mine_procedures, "get_llm_provider", lambda: fake_provider)

    _run_main(monkeypatch, session_id, transcript_path)

    assert len(fake_provider.calls) == 1
    assert fake_provider.calls[0][2] == "好的谢谢"  # 下一轮用户反馈已传入 provider
    data = procedure_store.read_procedure("write-doc-html")
    assert data is not None
    assert data["status"] == "candidate"
    assert data["hit_count"] == 1
    # 新建候选也统一走 update_confidence（首次即使成功也会有 HIT_DELTA 加成），
    # 不是无条件从 INITIAL_CONFIDENCE 起步——这样首次失败也能立刻扣分，见设计文档第7节。
    assert data["confidence"] == pytest.approx(update_confidence(INITIAL_CONFIDENCE, hit=True))


# ---- 场景 2：命中已有候选，累加 hit_count，复用同一 id ----


def test_hit_existing_candidate_increments_hit_count(isolated_env, monkeypatch):
    session_id = "sess-2"
    procedure_store.write_procedure(
        "task-html-doc",
        {
            "task_type": "写文档转html",
            "hit_count": 1,
            "confidence": 0.5,
            "status": "candidate",
            "skill_asked": False,
            "first_seen": "2026-07-01",
            "last_seen": "2026-07-01",
            "evidence_sessions": ["sess-old"],
        },
        "## 步骤\n1. 写md\n2. 转html",
    )
    records = [
        _user_record("u1", "帮我把md文档转成html", "2026-07-30T10:00:00Z"),
        _assistant_record("a1", "写了一份md文档并转成了html"),
        _user_record("u2", "好的谢谢", "2026-07-30T10:05:00Z"),
        _assistant_record("a2", "不客气"),
    ]
    transcript_path = _write_jsonl(isolated_env, records)
    for i in range(3):
        _obs(session_id, f"2026-07-30T10:00:0{i + 1}Z")

    fake_provider = _FakeProvider(
        result={
            "id": "some-other-id",
            "task_type": "写文档转html",
            "steps": ["写md", "转html"],
            "note": "",
            "is_successful": True,
        }
    )
    monkeypatch.setattr(mine_procedures, "get_llm_provider", lambda: fake_provider)

    _run_main(monkeypatch, session_id, transcript_path)

    data = procedure_store.read_procedure("task-html-doc")
    assert data is not None
    assert data["hit_count"] == 2
    assert data["confidence"] == pytest.approx(0.55)
    assert data["status"] == "candidate"
    assert session_id in data["evidence_sessions"]
    assert procedure_store.read_procedure("some-other-id") is None


# ---- 场景 3：跨过阈值，晋升为 promoted 并输出 systemMessage ----


def test_confidence_crossing_threshold_triggers_system_message(isolated_env, monkeypatch, capsys):
    session_id = "sess-3"
    procedure_store.write_procedure(
        "task-html-doc",
        {
            "task_type": "写文档转html",
            "hit_count": 5,
            "confidence": 0.68,
            "status": "candidate",
            "skill_asked": False,
            "first_seen": "2026-07-01",
            "last_seen": "2026-07-01",
            "evidence_sessions": ["sess-old"],
        },
        "## 步骤\n1. 写md\n2. 转html",
    )
    records = [
        _user_record("u1", "帮我把md文档转成html", "2026-07-30T10:00:00Z"),
        _assistant_record("a1", "写了一份md文档并转成了html"),
        _user_record("u2", "好的谢谢", "2026-07-30T10:05:00Z"),
        _assistant_record("a2", "不客气"),
    ]
    transcript_path = _write_jsonl(isolated_env, records)
    for i in range(3):
        _obs(session_id, f"2026-07-30T10:00:0{i + 1}Z")

    fake_provider = _FakeProvider(
        result={
            "id": "some-other-id",
            "task_type": "写文档转html",
            "steps": ["写md", "转html"],
            "note": "",
            "is_successful": True,
        }
    )
    monkeypatch.setattr(mine_procedures, "get_llm_provider", lambda: fake_provider)

    _run_main(monkeypatch, session_id, transcript_path)

    data = procedure_store.read_procedure("task-html-doc")
    assert data is not None
    assert data["status"] == "promoted"
    assert data["confidence"] == pytest.approx(0.73)

    out = capsys.readouterr().out.strip()
    parsed = json.loads(out)
    assert "systemMessage" in parsed
    assert "写文档转html" in parsed["systemMessage"]


# ---- 场景 4：工具调用数 < 3，不触发 LLM，不产生 procedure ----


def test_episode_with_too_few_tool_calls_is_skipped(isolated_env, monkeypatch):
    session_id = "sess-4"
    records = [
        _user_record("u1", "随便问一下", "2026-07-30T10:00:00Z"),
        _assistant_record("a1", "简单回复"),
        _user_record("u2", "好的", "2026-07-30T10:05:00Z"),
        _assistant_record("a2", "不客气"),
    ]
    transcript_path = _write_jsonl(isolated_env, records)
    for i in range(2):
        _obs(session_id, f"2026-07-30T10:00:0{i + 1}Z")

    fake_provider = _FakeProvider(
        result={"id": "x", "task_type": "y", "steps": ["a"], "note": "", "is_successful": True}
    )
    monkeypatch.setattr(mine_procedures, "get_llm_provider", lambda: fake_provider)

    _run_main(monkeypatch, session_id, transcript_path)

    assert fake_provider.calls == []
    assert procedure_store.list_procedures() == []


# ---- 场景 5：LLM 返回 None 时跳过该 episode，不影响其他 episode ----


def test_llm_returning_none_skips_episode_without_blocking_others(isolated_env, monkeypatch):
    session_id = "sess-5"
    records = [
        _user_record("u1", "先问个不构成流程的问题", "2026-07-30T10:00:00Z"),
        _assistant_record("a1", "随便回复一"),
        _user_record("u2", "再问一个真正的多步骤任务", "2026-07-30T10:05:00Z"),
        _assistant_record("a2", "写文档并转成html"),
        _user_record("u3", "好的谢谢", "2026-07-30T10:10:00Z"),
        _assistant_record("a3", "不客气"),
    ]
    transcript_path = _write_jsonl(isolated_env, records)
    # episode0: [10:00:00, 10:05:00)
    for i in range(3):
        _obs(session_id, f"2026-07-30T10:00:0{i + 1}Z")
    # episode1: [10:05:00, 10:10:00)
    for i in range(3):
        _obs(session_id, f"2026-07-30T10:05:0{i + 1}Z")

    fake_provider = _FakeProvider(
        results_by_assistant={
            "随便回复一": None,
            "写文档并转成html": {
                "id": "write-doc-html",
                "task_type": "写文档转html",
                "steps": ["写md", "转html"],
                "note": "",
                "is_successful": True,
            },
        }
    )
    monkeypatch.setattr(mine_procedures, "get_llm_provider", lambda: fake_provider)

    _run_main(monkeypatch, session_id, transcript_path)

    assert len(fake_provider.calls) == 2
    procedures = procedure_store.list_procedures()
    assert len(procedures) == 1
    assert procedures[0]["id"] == "write-doc-html"


# ---- 场景 6：LLM 抛 LLMProviderError 时跳过该 episode ----


def test_llm_provider_error_skips_episode_and_releases_cursor(isolated_env, monkeypatch):
    session_id = "sess-6"
    records = [
        _user_record("u1", "触发异常的任务", "2026-07-30T10:00:00Z"),
        _assistant_record("a1", "回复"),
        _user_record("u2", "好的", "2026-07-30T10:05:00Z"),
        _assistant_record("a2", "不客气"),
    ]
    transcript_path = _write_jsonl(isolated_env, records)
    for i in range(3):
        _obs(session_id, f"2026-07-30T10:00:0{i + 1}Z")

    fake_provider = _FakeProvider(raise_error=True)
    monkeypatch.setattr(mine_procedures, "get_llm_provider", lambda: fake_provider)

    _run_main(monkeypatch, session_id, transcript_path)

    assert len(fake_provider.calls) == 1
    assert procedure_store.list_procedures() == []

    claimed, cursor = procedure_store.try_claim_session(session_id, transcript_path)
    assert claimed is True
    assert cursor == "u1"


# ---- 场景 7：下一轮反馈是负面纠正，is_successful=False 时 confidence 真的下降 ----


def test_unsuccessful_execution_decreases_confidence(isolated_env, monkeypatch):
    session_id = "sess-7"
    procedure_store.write_procedure(
        "task-html-doc",
        {
            "task_type": "写文档转html",
            "hit_count": 3,
            "confidence": 0.5,
            "status": "candidate",
            "skill_asked": False,
            "first_seen": "2026-07-01",
            "last_seen": "2026-07-01",
            "evidence_sessions": ["sess-old"],
        },
        "## 步骤\n1. 写md\n2. 转html",
    )
    records = [
        _user_record("u1", "帮我把md文档转成html", "2026-07-30T10:00:00Z"),
        _assistant_record("a1", "写了一份md文档并转成了html"),
        _user_record("u2", "不对，这样不行，重新来", "2026-07-30T10:05:00Z"),
        _assistant_record("a2", "好的我重新来"),
    ]
    transcript_path = _write_jsonl(isolated_env, records)
    for i in range(3):
        _obs(session_id, f"2026-07-30T10:00:0{i + 1}Z")

    fake_provider = _FakeProvider(
        result={
            "id": "some-other-id",
            "task_type": "写文档转html",
            "steps": ["写md", "转html"],
            "note": "",
            "is_successful": False,
        }
    )
    monkeypatch.setattr(mine_procedures, "get_llm_provider", lambda: fake_provider)

    _run_main(monkeypatch, session_id, transcript_path)

    assert fake_provider.calls[0][2] == "不对，这样不行，重新来"
    data = procedure_store.read_procedure("task-html-doc")
    assert data is not None
    assert data["status"] == "candidate"
    assert data["hit_count"] == 4  # hit_count 是纯复现次数，不受 is_successful 影响
    assert data["confidence"] == pytest.approx(update_confidence(0.5, hit=False))
    assert data["confidence"] == pytest.approx(0.5 + MISS_DELTA)


# ---- 场景 8：只有 1 轮对话、没有下一轮反馈，episode 完全不处理，游标也不 release ----


def test_only_last_turn_without_lookahead_is_not_processed(isolated_env, monkeypatch):
    session_id = "sess-8"
    records = [
        _user_record("u1", "随便问一下没有下文", "2026-07-30T10:00:00Z"),
        _assistant_record("a1", "简单回复"),
    ]
    transcript_path = _write_jsonl(isolated_env, records)
    for i in range(3):
        _obs(session_id, f"2026-07-30T10:00:0{i + 1}Z")

    fake_provider = _FakeProvider(
        result={"id": "x", "task_type": "y", "steps": ["a"], "note": "", "is_successful": True}
    )
    monkeypatch.setattr(mine_procedures, "get_llm_provider", lambda: fake_provider)

    _run_main(monkeypatch, session_id, transcript_path)

    assert fake_provider.calls == []
    assert procedure_store.list_procedures() == []

    # 游标停在 processing、从未 release：紧接着再次 claim 应该被 stale 超时机制挡住
    claimed, _cursor = procedure_store.try_claim_session(session_id, transcript_path)
    assert claimed is False


# ---- 场景 9：多轮对话时最后一轮被留到下次处理，游标 release 到倒数第二轮 ----


def test_multi_turn_only_last_turn_held_back(isolated_env, monkeypatch):
    session_id = "sess-9"
    records = [
        _user_record("u1", "第一个任务", "2026-07-30T10:00:00Z"),
        _assistant_record("a1", "完成了第一个任务"),
        _user_record("u2", "第二个任务", "2026-07-30T10:05:00Z"),
        _assistant_record("a2", "完成了第二个任务"),
        _user_record("u3", "第三个任务，还没有下文", "2026-07-30T10:10:00Z"),
        _assistant_record("a3", "完成了第三个任务"),
    ]
    transcript_path = _write_jsonl(isolated_env, records)
    # episode0: [10:00:00, 10:05:00)
    for i in range(3):
        _obs(session_id, f"2026-07-30T10:00:0{i + 1}Z")
    # episode1: [10:05:00, 10:10:00)
    for i in range(3):
        _obs(session_id, f"2026-07-30T10:05:0{i + 1}Z")

    fake_provider = _FakeProvider(
        results_by_assistant={
            "完成了第一个任务": {
                "id": "proc-1",
                "task_type": "第一类任务",
                "steps": ["步骤1"],
                "note": "",
                "is_successful": True,
            },
            "完成了第二个任务": {
                "id": "proc-2",
                "task_type": "第二类任务",
                "steps": ["步骤1"],
                "note": "",
                "is_successful": True,
            },
        }
    )
    monkeypatch.setattr(mine_procedures, "get_llm_provider", lambda: fake_provider)

    _run_main(monkeypatch, session_id, transcript_path)

    # episode0(反馈=u2) 和 episode1(反馈=u3) 被处理，episode2(u3，无下文)不处理
    assert len(fake_provider.calls) == 2

    claimed, cursor = procedure_store.try_claim_session(session_id, transcript_path)
    assert claimed is True
    assert cursor == "u2"  # release 到 new_turns[-2]["uuid"]，不是最后一轮 u3


# ---- 场景 10：命中已 deprecated 的 procedure 时复活为 candidate，skill_asked 重置 ----


def test_deprecated_procedure_revives_on_hit(isolated_env, monkeypatch):
    session_id = "sess-10"
    procedure_store.write_procedure(
        "task-html-doc",
        {
            "task_type": "写文档转html",
            "hit_count": 2,
            "confidence": 0.5,
            "status": "deprecated",
            "skill_asked": True,
            "first_seen": "2026-07-01",
            "last_seen": "2026-07-01",
            "evidence_sessions": ["sess-old"],
        },
        "## 步骤\n1. 写md\n2. 转html",
    )
    records = [
        _user_record("u1", "帮我把md文档转成html", "2026-07-30T10:00:00Z"),
        _assistant_record("a1", "写了一份md文档并转成了html"),
        _user_record("u2", "好的谢谢", "2026-07-30T10:05:00Z"),
        _assistant_record("a2", "不客气"),
    ]
    transcript_path = _write_jsonl(isolated_env, records)
    for i in range(3):
        _obs(session_id, f"2026-07-30T10:00:0{i + 1}Z")

    fake_provider = _FakeProvider(
        result={
            "id": "some-other-id",
            "task_type": "写文档转html",
            "steps": ["写md", "转html"],
            "note": "",
            "is_successful": True,
        }
    )
    monkeypatch.setattr(mine_procedures, "get_llm_provider", lambda: fake_provider)

    _run_main(monkeypatch, session_id, transcript_path)

    data = procedure_store.read_procedure("task-html-doc")
    assert data is not None
    assert data["status"] == "candidate"  # 从 deprecated 复活为 candidate
    assert data["skill_asked"] is False  # 情况变了，值得再问一次
    assert data["hit_count"] == 3
    # confidence 起点选在 0.5，命中一次后 0.55 仍低于 PROMOTE_THRESHOLD(0.7)，避免晋升歧义
    assert data["confidence"] == pytest.approx(0.55)
