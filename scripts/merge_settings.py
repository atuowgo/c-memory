#!/usr/bin/env python3
"""把 c-memory 的 hooks 配置合并进目标项目的 .claude/settings.json，不覆盖已有的其他配置。

合并粒度是"每个 hook 事件（PostToolUse/Stop/...）下的 hook 组对象列表"：目标项目已有的
事件/组原样保留，c-memory 的组追加进对应事件的列表末尾；组内容完全相同（同一个 matcher +
同一批 command）时不重复追加，保证脚本可重复执行。除 hooks 外的其他顶层配置项一律不动。

c-memory 作为自包含子目录部署在目标项目里时（见 install.sh），hook 命令里的
${CLAUDE_PROJECT_DIR}/ 需要额外带上子目录名前缀（比如 ${CLAUDE_PROJECT_DIR}/c-memory/），
才能正确指向子目录里的 .venv/hooks，用第三个参数传入子目录名。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

_PROJECT_DIR_MARKER = "${CLAUDE_PROJECT_DIR}/"


def _prefix_commands(node, subdir: str):
    """递归遍历 hooks 结构，把所有字符串值里的 ${CLAUDE_PROJECT_DIR}/ 替换成带子目录前缀的版本。"""
    if isinstance(node, str):
        return node.replace(_PROJECT_DIR_MARKER, f"{_PROJECT_DIR_MARKER}{subdir}/")
    if isinstance(node, list):
        return [_prefix_commands(item, subdir) for item in node]
    if isinstance(node, dict):
        return {key: _prefix_commands(value, subdir) for key, value in node.items()}
    return node


def main() -> None:
    if len(sys.argv) not in (3, 4):
        print(
            "用法: merge_settings.py <template settings.json> <目标 .claude/settings.json> [子目录名]",
            file=sys.stderr,
        )
        sys.exit(1)

    template_path = Path(sys.argv[1])
    target_path = Path(sys.argv[2])
    subdir = sys.argv[3] if len(sys.argv) == 4 else ""

    template = json.loads(template_path.read_text(encoding="utf-8"))
    template_hooks = template.get("hooks", {})
    if subdir:
        template_hooks = _prefix_commands(template_hooks, subdir)

    if target_path.exists():
        target = json.loads(target_path.read_text(encoding="utf-8"))
    else:
        target = {}

    target_hooks = target.setdefault("hooks", {})

    for event, groups in template_hooks.items():
        existing_groups = target_hooks.setdefault(event, [])
        for group in groups:
            if group not in existing_groups:
                existing_groups.append(group)

    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(json.dumps(target, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"已合并 c-memory hooks 配置到 {target_path}")


if __name__ == "__main__":
    main()
