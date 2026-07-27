#!/usr/bin/env python3
"""Stop Hook: 会话结束时把本次会话的观测记录提炼为 instinct/memory，并重写规则文件。

输入协议（Claude Code 官方 Hooks 文档，Stop 事件）：
stdin 接收一段 JSON，字段包括 session_id / transcript_path / cwd /
hook_event_name（固定 "Stop"）。Stop Hook 是会话级别的，不含具体工具调用信息。

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

from memory_lib import storage  # noqa: E402
from memory_lib.confidence import (  # noqa: E402
    DEPRECATE_THRESHOLD,
    INITIAL_CONFIDENCE,
    update_confidence,
)
from memory_lib.detectors import detect_patterns  # noqa: E402
from memory_lib.providers import get_llm_provider  # noqa: E402

_SUMMARY_MAX_CHARS = 4000
_SUMMARY_EXAMPLES_PER_TOOL = 3


def _slugify(text: str) -> str:
    """把 pattern/fact 文本转成稳定、可读的文件名 id：非字母数字(含中文)替换成 '-'。"""
    slug = re.sub(r"[^0-9a-zA-Z一-鿿]+", "-", (text or "").strip())
    slug = slug.strip("-").lower()
    if not slug:
        slug = hashlib.md5((text or "").encode("utf-8")).hexdigest()[:8]
    return slug[:80]


def _load_session_observations(session_id: str) -> list[dict]:
    if not storage.OBSERVATIONS_FILE.exists():
        return []
    results = []
    with open(storage.OBSERVATIONS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if record.get("session_id") == session_id:
                results.append(record)
    return results


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


def _run_llm_analysis(summary: str) -> dict:
    """跑 LLM 语义分析路径；任何异常（含 LLMProviderError）都降级为空结果，不影响统计路径。"""
    try:
        provider = get_llm_provider()
        result = provider.analyze(summary)
        return {
            "instincts": result.get("instincts") or [],
            "project_facts": result.get("project_facts") or [],
        }
    except Exception as exc:  # noqa: BLE001 - LLM 路径失败不能影响整体提炼流程
        print(f"extract.py: LLM 分析失败，降级为空结果: {exc!r}", file=sys.stderr)
        return {"instincts": [], "project_facts": []}


def _update_hit_instincts(candidates: list[dict], today: str) -> set[str]:
    """处理本次会话命中的 instinct 候选：新建或更新 confidence，返回命中的 id 集合。"""
    hit_ids: set[str] = set()
    for cand in candidates:
        pattern = (cand.get("pattern") or "").strip()
        if not pattern:
            continue
        instinct_id = _slugify(pattern)
        existing = storage.read_instinct(instinct_id)

        if existing is None:
            frontmatter_dict = {
                "domain": cand.get("domain", ""),
                "pattern": pattern,
                "confidence": INITIAL_CONFIDENCE,
                "hit_count": 1,
                "deprecated": False,
                "last_seen": today,
                "scope": "personal",
            }
        else:
            frontmatter_dict = dict(existing)
            frontmatter_dict.pop("body", None)
            frontmatter_dict["domain"] = cand.get("domain", existing.get("domain", ""))
            frontmatter_dict["pattern"] = pattern
            frontmatter_dict["confidence"] = update_confidence(
                existing.get("confidence", INITIAL_CONFIDENCE), hit=True
            )
            frontmatter_dict["hit_count"] = existing.get("hit_count", 0) + 1
            frontmatter_dict["deprecated"] = False
            frontmatter_dict["last_seen"] = today

        body = cand.get("evidence") or pattern
        storage.write_instinct(instinct_id, frontmatter_dict, body)
        hit_ids.add(instinct_id)

    return hit_ids


def _decay_missed_instincts(hit_ids: set[str]) -> None:
    """本次会话未观测到的已有活跃 instinct：confidence 衰减，跌破阈值则标记 deprecated。

    只更新 confidence/deprecated，last_seen 及其余字段保持不动（本次没有被观测到）。
    """
    for inst in storage.list_instincts(include_deprecated=False):
        instinct_id = inst.get("id")
        if instinct_id in hit_ids:
            continue

        frontmatter_dict = dict(inst)
        body = frontmatter_dict.pop("body", "")
        new_confidence = update_confidence(
            frontmatter_dict.get("confidence", INITIAL_CONFIDENCE), hit=False
        )
        frontmatter_dict["confidence"] = new_confidence
        if new_confidence < DEPRECATE_THRESHOLD:
            frontmatter_dict["deprecated"] = True

        storage.write_instinct(instinct_id, frontmatter_dict, body)


def _write_project_facts(facts: list[dict], today: str) -> None:
    for fact in facts:
        fact_text = (fact.get("fact") or "").strip()
        if not fact_text:
            continue
        memory_id = _slugify(fact_text)
        storage.write_memory(
            memory_id,
            {"type": "project", "keywords": fact.get("keywords", []), "created": today},
            fact_text,
        )


def main() -> None:
    payload = json.load(sys.stdin)
    session_id = payload.get("session_id")

    storage.rotate_if_needed()

    session_observations = _load_session_observations(session_id) if session_id else []
    if not session_observations:
        return  # 本次会话没有观测记录，没什么可提炼的

    stat_candidates = detect_patterns(session_observations)
    summary = _summarize(session_observations)
    llm_result = _run_llm_analysis(summary)

    all_instinct_candidates = stat_candidates + llm_result["instincts"]
    project_facts = llm_result["project_facts"]

    today = date.today().isoformat()

    hit_ids = _update_hit_instincts(all_instinct_candidates, today)
    _decay_missed_instincts(hit_ids)
    _write_project_facts(project_facts, today)

    storage.regenerate_rules_file(storage.list_instincts(include_deprecated=False))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001 - Stop Hook 永远不能阻塞会话结束
        print(f"extract.py error: {exc!r}", file=sys.stderr)
    sys.exit(0)
