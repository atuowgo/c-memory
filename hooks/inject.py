#!/usr/bin/env python3
"""SessionStart Hook: 召回相关记忆并格式化注入到会话上下文，同时给用户一条可见的高亮提示。

输入协议（Claude Code 官方 Hooks 文档，SessionStart 事件）：
stdin 接收一段 JSON，字段包括 session_id / cwd /
hook_event_name（固定 "SessionStart"）等。

输出协议：不再是纯文本 stdout（那样用户在界面上完全看不到注入了什么），改成 JSON：
{"systemMessage": "<用户可见的高亮摘要>",
 "hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": "<真正喂给 Claude 的完整内容，跟原来纯文本版一致>"}}
systemMessage 是 Claude Code hooks 的通用字段，所有事件都会展示给用户；additionalContext 才是
真正被"插入对话最前面"给 Claude 看的内容，两者内容不同——systemMessage 只是简短高亮，
additionalContext 是完整原文。任何调试/错误信息一律写 stderr；脚本必须永远以
exit code 0 结束，不能阻塞会话启动。
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

# 通过 `python3 ${CLAUDE_PROJECT_DIR}/hooks/inject.py` 这种绝对路径调用时，
# 脚本 CWD 不一定是仓库根目录，需显式把仓库根目录加入 sys.path 才能 import memory_lib。
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from memory_lib import transcript_store  # noqa: E402
from memory_lib.providers import get_embedding_provider  # noqa: E402
from memory_lib.recall import build_query, recall_top_k  # noqa: E402
from memory_lib.storage import MEMORY_DIR, list_memories, list_promoted_instincts  # noqa: E402

# 仓库统一用 .venv 里的 python3 调用 hook 脚本（见 .claude/settings.json），
# 后台补总结子进程也要用同一个解释器，不能用 sys.executable（那是 Claude Code 自身的解释器）。
_VENV_PYTHON = _REPO_ROOT / ".venv" / "bin" / "python3"
_SUMMARIZE_SCRIPT = _REPO_ROOT / "hooks" / "summarize.py"


# type 取值对齐得物 extract_memories.py 的枚举（project/feedback/error/workflow），
# 未知/缺失类型退化为 [user]，跟之前保持一致。
_TYPE_LABELS = {
    "project": "[project]",
    "feedback": "[feedback]",
    "error": "[error]",
    "workflow": "[workflow]",
}


def _format_memories(top_memories: list[dict]) -> str:
    lines = []
    for mem in top_memories:
        label = _TYPE_LABELS.get(mem.get("type"), "[user]")
        text = mem.get("description") or mem.get("body", "")
        lines.append(f"{label} {text.strip()}")
    return "\n".join(lines)


def _format_instincts(instincts: list[dict]) -> str:
    lines = []
    for inst in instincts:
        domain = inst.get("domain", "")
        trigger = inst.get("trigger", "")
        lines.append(f"[habit][{domain}] {trigger}")
    return "\n".join(lines)


def _build_highlight(has_recap: bool, instincts: list[dict], top_memories: list[dict]) -> str:
    """给用户看的高亮摘要：本次 SessionStart 具体注入了哪些内容，完整列出、不做截断/省略。

    多条内容按列表逐行展示（每条单独一行），不堆到一行里用顿号拼接。
    """
    lines = ["🧠 c-memory 本次注入："]
    if has_recap:
        lines.append("· [project-recap] 项目总结 1 段")
    if instincts:
        lines.append(f"· [habit] {len(instincts)} 条：")
        for inst in instincts:
            lines.append(f"  - {inst.get('trigger', '')}")
    if top_memories:
        lines.append(f"· [memory] {len(top_memories)} 条：")
        for mem in top_memories:
            lines.append(f"  - {mem.get('description') or mem.get('body', '')}")
    return "\n".join(lines)


def _read_project_summary() -> str:
    summary_path = MEMORY_DIR / "project-summary.md"
    if not summary_path.exists():
        return ""
    try:
        return summary_path.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def _spawn_orphan_catchup(orphan: dict) -> None:
    """后台起一个独立进程跑 summarize.py 的 force 模式补总结，不等待其结束（fire-and-forget）。

    不能用"Popen(stdin=PIPE) 再 write" 的写法：写完不 close/wait 就返回的话，管道另一端
    的读取行为和父进程提前退出后的资源回收顺序没有保证；用 communicate() 又会阻塞等待
    子进程结束，跟"不等待结果"矛盾。这里改用临时文件承载 payload 作为子进程的 stdin：
    Popen() 内部 fork+exec 是同步完成的，调用一返回子进程就已经拿到了独立的 fd 副本，
    父进程随即可以关闭并 unlink 临时文件（POSIX 语义下，只要子进程的 fd 还开着，inode
    数据就不会被真正回收）——全程没有 write()/communicate()/wait() 等任何会阻塞或等待
    子进程的调用，是真正的"发起后立刻返回"。
    """
    payload = json.dumps(
        {
            "session_id": orphan["session_id"],
            "transcript_path": orphan["transcript_path"],
            "hook_event_name": "SessionEnd",  # 借用 force 语义触发强制总结，跳过阈值判断
        }
    )
    fd, tmp_path = tempfile.mkstemp(prefix="orphan-catchup-", suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(payload)
        with open(tmp_path, "r", encoding="utf-8") as stdin_file:
            subprocess.Popen(
                [str(_VENV_PYTHON), str(_SUMMARIZE_SCRIPT)],
                stdin=stdin_file,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,  # 脱离父进程的 session，真正独立运行
            )
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


def main() -> None:
    try:
        payload = json.load(sys.stdin)
        cwd = payload.get("cwd") or os.getcwd()
        session_id = payload.get("session_id")
    except (json.JSONDecodeError, ValueError):
        cwd = os.getcwd()
        session_id = None

    if session_id:
        try:
            for orphan in transcript_store.find_orphan_sessions(exclude_session_id=session_id):
                _spawn_orphan_catchup(orphan)
        except Exception:  # noqa: BLE001 - 孤儿扫描/补总结失败不能影响本次会话正常启动
            pass

    sections = []
    has_recap = False
    top_memories: list[dict] = []

    project_summary = _read_project_summary()
    if project_summary:
        sections.append(f"[project-recap]\n{project_summary}")
        has_recap = True

    instincts = list_promoted_instincts()
    if instincts:
        sections.append(_format_instincts(instincts))

    memories = list_memories()
    if memories:
        query = build_query(cwd)
        provider = get_embedding_provider()
        top_memories = recall_top_k(query, memories, provider, k=5)
        if top_memories:
            sections.append(_format_memories(top_memories))

    if not sections:
        return

    output = {
        "systemMessage": _build_highlight(has_recap, instincts, top_memories),
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": "\n".join(sections),
        },
    }
    print(json.dumps(output, ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001 - SessionStart Hook 永远不能阻塞
        print(f"inject.py error: {exc!r}", file=sys.stderr)
    sys.exit(0)
