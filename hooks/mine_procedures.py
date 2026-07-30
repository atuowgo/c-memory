#!/usr/bin/env python3
"""Stop Hook 第三条命令：流程挖掘（procedure mining）。

跟 extract.py（提炼 instinct/memory）、summarize.py（滚动总结对话）并列，
是第三条独立的 Stop Hook 管线，负责识别"多步骤可复用流程"（比如"写含 mermaid
图的 md 文档再转 html"这种固定套路）。达到复现阈值（晋升为 status=promoted）
后不注入上下文，而是通过本次 hook 输出的 systemMessage 字段高亮提示用户，
建议其考虑转成 Skill。

输入协议（Claude Code 官方 Hooks 文档，Stop 事件）：
stdin 接收一段 JSON，字段包括 session_id / transcript_path / cwd /
hook_event_name（固定 "Stop"）。

约束：脚本必须永远以 exit code 0 结束，不能阻塞会话结束；调试/错误信息一律写 stderr。
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import date
from pathlib import Path

# 通过 `python3 ${CLAUDE_PROJECT_DIR}/hooks/mine_procedures.py` 这种绝对路径调用时，
# 脚本 CWD 不一定是仓库根目录，需显式把仓库根目录加入 sys.path 才能 import memory_lib。
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from memory_lib import observation_store, procedure_store, transcript  # noqa: E402
from memory_lib.confidence import INITIAL_CONFIDENCE, PROMOTE_THRESHOLD, update_confidence  # noqa: E402
from memory_lib.dedup import find_similar_procedure  # noqa: E402
from memory_lib.providers import LLMProviderError, get_llm_provider  # noqa: E402

_MIN_OBSERVATIONS_PER_EPISODE = 3
_STEP_INPUT_MAX_CHARS = 150


def _slugify(text: str) -> str:
    """把文本转成稳定、可读的文件名 id：非字母数字(含中文)替换成 '-'。

    仅作兜底：正常路径下 id 由 LLM 按提示词要求直接生成英文 kebab-case，
    这里只在 LLM 没给 id、或给出的 id 不是合法 kebab-case 时才用来兜底生成。
    与 extract.py 里的 _slugify 逻辑一致（两个 hook 脚本各自独立，不互相 import）。
    """
    slug = re.sub(r"[^0-9a-zA-Z一-鿿]+", "-", (text or "").strip())
    slug = slug.strip("-").lower()
    if not slug:
        slug = hashlib.md5((text or "").encode("utf-8")).hexdigest()[:8]
    return slug[:80]


_KEBAB_ID_PATTERN = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def _sanitize_id(raw_id: str | None, fallback_text: str) -> str:
    """校验 LLM 给出的 id 是否为合法英文 kebab-case，不合法则退化为本地 slugify。"""
    candidate = (raw_id or "").strip().lower()
    if _KEBAB_ID_PATTERN.match(candidate):
        return candidate[:80]
    return _slugify(fallback_text)


def _build_steps_summary(observations: list[dict]) -> str:
    """把一个 episode 的观测记录按时间顺序格式化成喂给 LLM 的步骤摘要文本。

    跟 extract.py 的 _summarize 不同：流程挖掘要看步骤顺序，不能按 tool_name 分组。
    """
    lines = []
    for index, obs in enumerate(observations, start=1):
        tool_name = obs.get("tool_name") or "unknown"
        tool_input = obs.get("tool_input") or {}
        brief = json.dumps(tool_input, ensure_ascii=False)
        if len(brief) > _STEP_INPUT_MAX_CHARS:
            brief = brief[:_STEP_INPUT_MAX_CHARS] + "..."
        lines.append(f"{index}. {tool_name}: {brief}")
    return "\n".join(lines)


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return
    if not isinstance(payload, dict):
        return

    session_id = payload.get("session_id")
    transcript_path = payload.get("transcript_path")
    if not session_id or not transcript_path:
        return

    claimed, after_uuid = procedure_store.try_claim_session(session_id, transcript_path)
    if not claimed:
        return  # 锁被占用且未超时，跳过本次

    new_turns = transcript.parse_new_turns(transcript_path, after_uuid)
    if not new_turns:
        procedure_store.release_session(session_id, after_uuid)
        return

    promoted_this_run: list[tuple[str, str, int]] = []

    try:
        provider = get_llm_provider()

        for i, turn in enumerate(new_turns):
            ts_start = turn["ts"]
            ts_end = new_turns[i + 1]["ts"] if i + 1 < len(new_turns) else None

            observations = observation_store.list_session_observations_in_range(session_id, ts_start, ts_end)
            if len(observations) < _MIN_OBSERVATIONS_PER_EPISODE:
                continue  # 工具调用太少，不构成流程，不浪费 LLM 调用

            steps_summary = _build_steps_summary(observations)

            try:
                result = provider.mine_procedure(steps_summary, turn["assistant"])
            except LLMProviderError as exc:
                print(f"mine_procedures.py: LLM 流程挖掘失败，跳过该 episode: {exc!r}", file=sys.stderr)
                continue
            except Exception as exc:  # noqa: BLE001 - 单个 episode 的 LLM 失败不能中断整批
                print(f"mine_procedures.py: 流程挖掘异常，跳过该 episode: {exc!r}", file=sys.stderr)
                continue

            if result is None:
                continue  # LLM 判断不构成流程

            task_type = (result.get("task_type") or "").strip()
            if not task_type:
                continue

            today = date.today().isoformat()
            existing = find_similar_procedure(task_type, procedure_store.list_procedures())

            if existing is not None:
                procedure_id = existing["id"]
                hit_count = existing.get("hit_count", 0) + 1
                confidence = update_confidence(existing.get("confidence", INITIAL_CONFIDENCE), hit=True)
                was_candidate = existing.get("status") != "promoted"
                evidence_sessions = list(existing.get("evidence_sessions") or [])
                if session_id not in evidence_sessions:
                    evidence_sessions.append(session_id)
                status = "promoted" if (was_candidate and confidence >= PROMOTE_THRESHOLD) else existing.get(
                    "status", "candidate"
                )
                just_promoted = was_candidate and status == "promoted"
                skill_asked = existing.get("skill_asked", False)
                first_seen = existing.get("first_seen", today)
            else:
                procedure_id = _sanitize_id(result.get("id"), task_type)
                hit_count = 1
                confidence = INITIAL_CONFIDENCE
                status = "candidate"
                just_promoted = False
                skill_asked = False
                evidence_sessions = [session_id]
                first_seen = today

            body = "## 步骤\n" + "\n".join(
                f"{i + 1}. {s}" for i, s in enumerate(result.get("steps") or [])
            )
            if result.get("note"):
                body += f"\n\n## 说明\n{result['note']}"

            frontmatter_dict = {
                "task_type": task_type,
                "hit_count": hit_count,
                "confidence": confidence,
                "status": status,
                "skill_asked": skill_asked,
                "first_seen": first_seen,
                "last_seen": today,
                "evidence_sessions": evidence_sessions,
            }
            procedure_store.write_procedure(procedure_id, frontmatter_dict, body)

            if just_promoted:
                promoted_this_run.append((procedure_id, task_type, hit_count))

        if promoted_this_run:
            lines = [
                f"🎯 检测到可复用流程「{task_type}」已出现 {hit_count} 次，"
                f"已保存到 memory/procedures/{procedure_id}.md，可考虑转成 Skill。"
                for procedure_id, task_type, hit_count in promoted_this_run
            ]
            print(json.dumps({"systemMessage": "\n".join(lines)}, ensure_ascii=False))
    finally:
        # 无条件推进游标：跟 extract.py 一致的哲学——流程模式会反复出现，
        # 单次处理失败也丢得起，不需要像 summarize.py 那样保守地只在成功时才推进。
        procedure_store.release_session(session_id, new_turns[-1]["uuid"])


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001 - Stop Hook 永远不能阻塞会话结束
        print(f"mine_procedures.py error: {exc!r}", file=sys.stderr)
    sys.exit(0)
