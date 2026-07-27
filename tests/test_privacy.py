"""memory_lib.privacy.filter_sensitive / is_sensitive_file 单元测试。

注意：所有测试用的“密钥”都是明显的假值（重复字符拼接），
不要出现任何看起来像真实凭证的字符串。
"""
from __future__ import annotations

from memory_lib.privacy import filter_sensitive, is_sensitive_file

_FAKE_SK_KEY = "sk-" + "a" * 24
_FAKE_ARK_KEY = "ark-" + "b" * 24


def test_sk_key_redacted():
    record = {"text": f"my key is {_FAKE_SK_KEY} do not share"}
    result = filter_sensitive(record)
    assert _FAKE_SK_KEY not in result["text"]
    assert "***REDACTED***" in result["text"]


def test_ark_key_redacted():
    record = {"text": f"ARK_API_KEY={_FAKE_ARK_KEY}"}
    result = filter_sensitive(record)
    assert _FAKE_ARK_KEY not in result["text"]
    assert "***REDACTED***" in result["text"]


def test_generic_api_key_pattern_redacted():
    record = {"text": "API_KEY=" + "x" * 10}
    result = filter_sensitive(record)
    assert "***REDACTED***" in result["text"]
    assert "x" * 10 not in result["text"]


def test_generic_token_pattern_redacted():
    record = {"text": "token: " + "y" * 10}
    result = filter_sensitive(record)
    assert "***REDACTED***" in result["text"]
    assert "y" * 10 not in result["text"]


def test_generic_password_pattern_redacted():
    record = {"text": "password=" + "z" * 10}
    result = filter_sensitive(record)
    assert "***REDACTED***" in result["text"]
    assert "z" * 10 not in result["text"]


def test_nested_dict_and_list_are_recursively_filtered():
    record = {
        "tool_input": {
            "env": {"SECRET": _FAKE_SK_KEY},
            "args": ["--flag", f"password={'q' * 10}"],
        }
    }
    result = filter_sensitive(record)
    assert result["tool_input"]["env"]["SECRET"] == "***REDACTED***"
    assert "***REDACTED***" in result["tool_input"]["args"][1]
    assert _FAKE_SK_KEY not in str(result)


def test_is_sensitive_file_true_cases():
    assert is_sensitive_file(".env") is True
    assert is_sensitive_file("/path/to/.env") is True
    assert is_sensitive_file("id.pem") is True
    assert is_sensitive_file("aws_credentials.json") is True


def test_is_sensitive_file_false_case():
    assert is_sensitive_file("normal_file.py") is False


def test_is_sensitive_file_empty_path():
    assert is_sensitive_file("") is False


def test_filter_sensitive_replaces_content_but_keeps_other_fields():
    record = {
        "tool_name": "Read",
        "session_id": "session-123",
        "ts": "2026-07-27T00:00:00Z",
        "tool_input": {"file_path": "/repo/.env"},
        "tool_response": {"content": f"SECRET_TOKEN={_FAKE_SK_KEY}"},
    }
    result = filter_sensitive(record)

    # 内容字段被替换成占位符，不含原始敏感内容
    assert result["tool_input"] == "<REDACTED: sensitive file>"
    assert result["tool_response"] == "<REDACTED: sensitive file>"
    assert _FAKE_SK_KEY not in str(result)

    # 非内容字段保留
    assert result["tool_name"] == "Read"
    assert result["session_id"] == "session-123"
    assert result["ts"] == "2026-07-27T00:00:00Z"
