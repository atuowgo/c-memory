#!/usr/bin/env python3
"""UserPromptSubmit Hook: 检测已晋升但还没问过用户的流程，提醒 Claude 主动询问是否转 Skill。

输入协议（Claude Code 官方 Hooks 文档，UserPromptSubmit 事件）：
stdin 接收一段 JSON，字段包括 session_id / prompt / cwd /
hook_event_name（固定 "UserPromptSubmit"）等。本脚本不依赖 payload 里的
任何字段——待提醒的 procedure 数据是项目级的，不是会话级的。

约束：stdout 内容会被直接注入下一轮上下文（UserPromptSubmit 与
SessionStart、UserPromptExpansion 是仅有的三个"stdout 直接注入上下文"
的 Hook 事件，跟 Stop 必须走 JSON 的 systemMessage 字段不同），因此
stdout 只能输出格式化后的提示文本，任何调试/错误信息一律写 stderr；
脚本必须永远以 exit code 0 结束，不能阻塞用户输入被处理。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

# 通过 `python3 ${CLAUDE_PROJECT_DIR}/hooks/notify_pending_procedures.py` 这种绝对路径
# 调用时，脚本 CWD 不一定是仓库根目录，需显式把仓库根目录加入 sys.path 才能 import memory_lib。
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from memory_lib import procedure_store  # noqa: E402


def _format_prompt(proc: dict) -> str:
    task_type = proc.get("task_type", "")
    hit_count = proc.get("hit_count", "")
    procedure_id = proc.get("id", "")
    return (
        "[procedure-pending]\n"
        f"检测到流程「{task_type}」已稳定复现 {hit_count} 次"
        f"（memory/procedures/{procedure_id}.md），\n"
        "请先询问用户：1) 这个流程实际上是否正确/有效；2) 是否要转换为 Skill。\n"
        "若用户反馈流程不正确，请把该 procedure 文件的 status 改为 deprecated（不要转成 Skill）；\n"
        "用户确认流程正确且要转换，再执行转换；不要自作主张直接转。"
    )


def main() -> None:
    try:
        json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        pass

    pending = procedure_store.list_pending_skill_prompts()
    if not pending:
        return

    sections = [_format_prompt(proc) for proc in pending]
    print("\n\n".join(sections))

    # 先输出再标记：保证"至少提醒一次"——如果标记写在前面、print 因为某种意外
    # 没真正送达，这条提醒就会永久丢失；反过来最坏情况只是极小概率重复提醒一次。
    for proc in pending:
        procedure_store.mark_skill_asked(proc["id"])


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001 - UserPromptSubmit Hook 永远不能阻塞
        print(f"notify_pending_procedures.py error: {exc!r}", file=sys.stderr)
    sys.exit(0)
