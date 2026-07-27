"""隐私过滤：写入 observations.jsonl 前对记录做脱敏处理。"""
from __future__ import annotations

import re

_REDACTED = "***REDACTED***"

_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9]{20,}"),
    re.compile(r"ark-[A-Za-z0-9-]{20,}"),
    re.compile(r"(?i)(api[_-]?key|token|password)\s*[:=]\s*\S+"),
]

_SENSITIVE_FILE_KEYWORDS = (".env", ".pem", ".key", "id_rsa", ".npmrc", ".aws", "credentials", "secrets")

# 可能携带文件路径的字段名（tool_input 内常见 key + 顶层可能出现的字段）
_PATH_FIELD_CANDIDATES = ("file_path", "path", "notebook_path", "filename")

# 每种工具只保留“行为信号”字段（路径/命令），不保留内容字段
# （如 Write 的 content、Edit 的 old_string/new_string），也不保留 tool_response。
# 未知工具 fallback 到 _PATH_FIELD_CANDIDATES：只留看起来像路径的字段，其余一律丢弃。
_BEHAVIORAL_FIELDS = {
    "Read": ("file_path",),
    "Edit": ("file_path",),
    "Write": ("file_path",),
    "MultiEdit": ("file_path",),
    "NotebookEdit": ("notebook_path",),
    "Bash": ("command",),
    "Grep": ("pattern", "path"),
    "Glob": ("pattern", "path"),
}


def extract_behavioral_signal(tool_name: str, tool_input) -> dict:
    """只保留检测行为模式所需的结构化字段，不保留任何文件/命令输出内容。

    已知工具（Read/Edit/Write/Bash 等）只留路径或命令本身；未知工具只留看起来
    像路径的字段。其余字段（如 Write 的 content、Edit 的 old_string/new_string）
    一律丢弃 —— 这些字段本来就不被任何检测器使用，却是内容泄漏风险最大的部分。
    """
    if not isinstance(tool_input, dict):
        return {}
    fields = _BEHAVIORAL_FIELDS.get(tool_name, _PATH_FIELD_CANDIDATES)
    return {k: tool_input[k] for k in fields if k in tool_input}


def is_sensitive_file(path: str) -> bool:
    """路径包含 .env / .pem / credentials 关键字返回 True。"""
    if not path:
        return False
    lowered = path.lower()
    return any(keyword in lowered for keyword in _SENSITIVE_FILE_KEYWORDS)


def _redact_string(value: str) -> str:
    for pattern in _PATTERNS:
        value = pattern.sub(_REDACTED, value)
    return value


def _redact_value(value):
    if isinstance(value, str):
        return _redact_string(value)
    if isinstance(value, dict):
        return {k: _redact_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_redact_value(v) for v in value]
    return value


def _extract_path(value) -> str | None:
    """从 dict/字符串中递归找出第一个可能的文件路径字段。"""
    if isinstance(value, dict):
        for key in _PATH_FIELD_CANDIDATES:
            if key in value and isinstance(value[key], str):
                return value[key]
        for v in value.values():
            found = _extract_path(v)
            if found:
                return found
    return None


def _find_sensitive_path(record: dict) -> str | None:
    for field in ("tool_input", "tool_response"):
        if field in record:
            path = _extract_path(record[field])
            if path and is_sensitive_file(path):
                return path
    return None


def filter_sensitive(record: dict) -> dict:
    """对 record 做隐私过滤，返回过滤后的新 dict（不修改原对象）。"""
    sensitive_path = _find_sensitive_path(record)
    if sensitive_path:
        filtered = {"tool_name": record.get("tool_name")}
        filtered["file"] = sensitive_path
        for field in ("tool_input", "tool_response"):
            if field in record:
                filtered[field] = "<REDACTED: sensitive file>"
        # 保留其余非内容字段（如 session_id/ts）
        for key, value in record.items():
            if key not in filtered and key not in ("tool_input", "tool_response"):
                filtered[key] = value
        return filtered

    return {key: _redact_value(value) for key, value in record.items()}
