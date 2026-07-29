#!/usr/bin/env python3
"""Stop Hook: 会话结束时把本次会话的观测记录提炼为 instinct/memory，并重写规则文件。

输入协议（Claude Code 官方 Hooks 文档，Stop 事件）：
stdin 接收一段 JSON，字段包括 session_id / transcript_path / cwd /
hook_event_name（固定 "Stop"）/ last_assistant_message（本轮最终 assistant 文本，
官方文档建议 Stop/SubagentStop 场景用这个字段而不是读 transcript_path，因为
transcript 文件是异步写入的，触发时可能还没落盘最新一轮）。

约束：脚本必须永远以 exit code 0 结束，不能阻塞会话结束；调试/错误信息一律写 stderr。
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

# 通过 `python3 ${CLAUDE_PROJECT_DIR}/hooks/extract.py` 这种绝对路径调用时，
# 脚本 CWD 不一定是仓库根目录，需显式把仓库根目录加入 sys.path 才能 import memory_lib。
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from memory_lib import observation_store, storage  # noqa: E402
from memory_lib.confidence import INITIAL_CONFIDENCE, update_confidence  # noqa: E402
from memory_lib.dedup import find_similar_instinct, find_similar_memory  # noqa: E402
from memory_lib.detectors import detect_patterns  # noqa: E402
from memory_lib.providers import get_llm_provider  # noqa: E402

_SUMMARY_MAX_CHARS = 4000
_SUMMARY_EXAMPLES_PER_TOOL = 3


def _slugify(text: str) -> str:
    """把 trigger/description 文本转成稳定、可读的文件名 id：非字母数字(含中文)替换成 '-'。

    仅作兜底：正常路径下 id/name 由 LLM 按提示词要求直接生成英文 kebab-case
    （对齐得物 analyze_instincts.py / extract_memories.py 的 prompt 约定），
    这里只在 LLM 没给 id、或给出的 id 不是合法 kebab-case 时才用来兜底生成。
    """
    slug = re.sub(r"[^0-9a-zA-Z一-鿿]+", "-", (text or "").strip())
    slug = slug.strip("-").lower()
    if not slug:
        slug = hashlib.md5((text or "").encode("utf-8")).hexdigest()[:8]
    return slug[:80]


_KEBAB_ID_PATTERN = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def _sanitize_id(raw_id: str | None, fallback_text: str) -> str:
    """校验 LLM/检测器给出的 id 是否为合法英文 kebab-case，不合法则退化为本地 slugify。"""
    candidate = (raw_id or "").strip().lower()
    if _KEBAB_ID_PATTERN.match(candidate):
        return candidate[:80]
    return _slugify(fallback_text)


def _summarize(observations: list[dict]) -> str:
    """把本次会话观测压缩成几千字符以内的摘要文本，供 LLM 语义分析用。

    不塞全部原始 json，只按 tool_name 分组统计次数 + 每种取前几条示例。
    """
    by_tool: dict[str, list[dict]] = defaultdict(list)
    for obs in observations:
        by_tool[obs.get("tool_name") or "unknown"].append(obs)

    lines = [f"本次会话共 {len(observations)} 条观测记录，按工具类型汇总："]
    for tool_name, obs_list in by_tool.items():
        lines.append(f"- {tool_name}: 共 {len(obs_list)} 次")
        for obs in obs_list[:_SUMMARY_EXAMPLES_PER_TOOL]:
            tool_input = obs.get("tool_input") or {}
            brief = json.dumps(tool_input, ensure_ascii=False)
            if len(brief) > 200:
                brief = brief[:200] + "..."
            lines.append(f"  例: {brief}")

    summary = "\n".join(lines)
    if len(summary) > _SUMMARY_MAX_CHARS:
        summary = summary[:_SUMMARY_MAX_CHARS] + "...(截断)"
    return summary


def _run_llm_analysis(summary: str, last_message: str) -> dict:
    """跑 LLM 语义分析路径；任何异常（含 LLMProviderError）都降级为空结果，不影响统计路径。

    last_message 对齐得物 extract_memories.py 的数据源优先级：Stop Hook 官方提供的
    last_assistant_message（避免读 transcript_path，文档明确说明该文件写入是异步的，
    触发时可能还没写进本轮最新内容）。
    """
    try:
        provider = get_llm_provider()
        result = provider.analyze(summary, last_message)
        return {
            "instincts": result.get("instincts") or [],
            "project_facts": result.get("project_facts") or [],
        }
    except Exception as exc:  # noqa: BLE001 - LLM 路径失败不能影响整体提炼流程
        print(f"extract.py: LLM 分析失败，降级为空结果: {exc!r}", file=sys.stderr)
        return {"instincts": [], "project_facts": []}


def _update_hit_instincts(candidates: list[dict], today: str) -> set[str]:
    """处理本次会话命中的 instinct 候选：新建或更新 confidence，返回命中的 id 集合。

    同一 domain 下先尝试用 char_jaccard 找语义相似的已有 instinct 合并命中，
    避免 LLM 每次措辞不同（"编辑前先阅读"/"编辑前先读取"）把同一习惯拆成多条、
    永远凑不够置信度晋升阈值。找不到相似的才使用候选自带的 id（LLM/检测器直接
    产出的英文 kebab-case，见 _sanitize_id），id 不合法时才退化为本地 slugify。
    """
    hit_ids: set[str] = set()
    known_instincts = storage.list_instincts(include_deprecated=True)

    for cand in candidates:
        trigger = (cand.get("trigger") or "").strip()
        if not trigger:
            continue
        domain = cand.get("domain", "")
        action = (cand.get("action") or "").strip()
        evidence = (cand.get("evidence") or "").strip()

        similar = find_similar_instinct(trigger, domain, known_instincts)
        if similar is not None:
            instinct_id = similar["id"]
            existing = similar
        else:
            instinct_id = _sanitize_id(cand.get("id"), trigger)
            existing = storage.read_instinct(instinct_id)

        if existing is None:
            frontmatter_dict = {
                "domain": domain,
                "trigger": trigger,
                "confidence": INITIAL_CONFIDENCE,
                "hit_count": 1,
                "deprecated": False,
                "last_seen": today,
                "scope": "personal",
            }
        else:
            frontmatter_dict = dict(existing)
            frontmatter_dict.pop("body", None)
            frontmatter_dict["domain"] = domain or existing.get("domain", "")
            frontmatter_dict["trigger"] = trigger
            frontmatter_dict["confidence"] = update_confidence(
                existing.get("confidence", INITIAL_CONFIDENCE), hit=True
            )
            frontmatter_dict["hit_count"] = existing.get("hit_count", 0) + 1
            frontmatter_dict["deprecated"] = False
            frontmatter_dict["last_seen"] = today

        body = f"## Action\n{action}\n\n## Evidence\n{evidence}" if (action or evidence) else trigger
        storage.write_instinct(instinct_id, frontmatter_dict, body)
        hit_ids.add(instinct_id)

        # 更新本轮内存快照，让同一次运行里后续候选也能对这条刚写入/更新的记录做合并
        known_instincts = [inst for inst in known_instincts if inst.get("id") != instinct_id]
        known_instincts.append({**frontmatter_dict, "id": instinct_id, "body": body})

    return hit_ids


def _write_project_facts(facts: list[dict], today: str) -> None:
    """同一事实即使 LLM 每次措辞不同，也应合并到同一条 memory 而不是各自新建文件。

    project_facts 没有 domain 字段，find_similar_memory 改用 keywords 交集做分组门槛，
    命中的话覆盖已有 memory_id（文本更新为最新措辞），逻辑与 instincts 的语义去重对称。
    找不到相似的才使用候选自带的 name（LLM 直接产出的英文 kebab-case），不合法时退化为
    本地 slugify。
    """
    known_memories = storage.list_memories()

    for fact in facts:
        description = (fact.get("description") or "").strip()
        if not description:
            continue
        body = (fact.get("body") or "").strip() or description
        keywords = fact.get("keywords", [])
        fact_type = fact.get("type") or "project"

        similar = find_similar_memory(description, keywords, known_memories)
        memory_id = similar["id"] if similar is not None else _sanitize_id(fact.get("name"), description)

        storage.write_memory(
            memory_id,
            {"type": fact_type, "keywords": keywords, "description": description, "created": today},
            body,
        )

        known_memories = [m for m in known_memories if m.get("id") != memory_id]
        known_memories.append(
            {
                "id": memory_id,
                "keywords": keywords,
                "description": description,
                "body": body,
                "type": fact_type,
                "created": today,
            }
        )


def main() -> None:
    payload = json.load(sys.stdin)
    session_id = payload.get("session_id")
    last_message = payload.get("last_assistant_message", "")
    if not session_id:
        return

    after_id = observation_store.try_claim_session(session_id)
    if after_id is None:
        return  # 同一 session 已有一次处理在跑（且未超时），本次跳过，不同步等待

    session_observations = observation_store.list_new_session_observations(session_id, after_id)
    if not session_observations:
        observation_store.release_session(session_id, after_id)
        return  # 上次处理之后没有新观测，没什么可提炼的

    max_id = max(obs["id"] for obs in session_observations)
    try:
        stat_candidates = detect_patterns(session_observations)
        summary = _summarize(session_observations)
        llm_result = _run_llm_analysis(summary, last_message)

        all_instinct_candidates = stat_candidates + llm_result["instincts"]
        project_facts = llm_result["project_facts"]

        today = date.today().isoformat()

        _update_hit_instincts(all_instinct_candidates, today)
        _write_project_facts(project_facts, today)

        storage.regenerate_rules_file(storage.list_instincts(include_deprecated=False))
    finally:
        # 无论本次分析是否抛异常都要推进游标+释放，避免卡在 processing 状态导致
        # 这个 session 之后每次 Stop 都被当成"仍在处理"而永久跳过。
        observation_store.release_session(session_id, max_id)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001 - Stop Hook 永远不能阻塞会话结束
        print(f"extract.py error: {exc!r}", file=sys.stderr)
    sys.exit(0)
