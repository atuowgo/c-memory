"""隐私过滤：写入 observations 前对记录做脱敏处理。

捕获范围对齐得物开源实现（agent-memory-system 的 observe.py）：保留完整
tool_input + tool_response 摘要，不再做字段白名单裁剪，只靠下面的正则脱敏
+ 敏感文件名整条丢弃兜底。正则集合是我们原有的 sk-/ark-/api_key= 系列
（ark- 是本项目实际在用的 Ark embedding key 格式，得物没有）叠加得物那边
额外覆盖的 ghp_/AKIA/Bearer 三种。
"""
from __future__ import annotations

import re

_REDACTED = "***REDACTED***"

_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9]{20,}"),
    re.compile(r"ark-[A-Za-z0-9-]{20,}"),
    re.compile(r"(?i)(api[_-]?key|token|password)\s*[:=]\s*\S+"),
    re.compile(r"ghp_[A-Za-z0-9]{36,}"),  # GitHub token
    re.compile(r"AKIA[A-Z0-9]{16}"),  # AWS access key
    re.compile(r"(?i)Bearer\s+[A-Za-z0-9\-_.]+"),
]

_SENSITIVE_FILE_KEYWORDS = (".env", ".pem", ".key", "id_rsa", ".npmrc", ".aws", "credentials", "secrets")

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


_CONTENT_FIELDS = ("tool_input", "tool_response", "tool_response_summary")


def _find_sensitive_path(record: dict) -> str | None:
    for field in _CONTENT_FIELDS:
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
        for field in _CONTENT_FIELDS:
            if field in record:
                filtered[field] = "<REDACTED: sensitive file>"
        # 保留其余非内容字段（如 session_id/ts）
        for key, value in record.items():
            if key not in filtered and key not in _CONTENT_FIELDS:
                filtered[key] = value
        return filtered

    return {key: _redact_value(value) for key, value in record.items()}
