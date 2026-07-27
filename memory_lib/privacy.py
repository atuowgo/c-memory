"""隐私过滤：写入 observations.jsonl 前对记录做脱敏处理。"""
from __future__ import annotations

import re

_REDACTED = "***REDACTED***"

_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9]{20,}"),
    re.compile(r"ark-[A-Za-z0-9-]{20,}"),
    re.compile(r"(?i)(api[_-]?key|token|password)\s*[:=]\s*\S+"),
]

_SENSITIVE_FILE_KEYWORDS = (".env", ".pem", "credentials")

# 可能携带文件路径的字段名（tool_input 内常见 key + 顶层可能出现的字段）
_PATH_FIELD_CANDIDATES = ("file_path", "path", "notebook_path", "filename")


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
