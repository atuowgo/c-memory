"""memory_lib.providers 多 LLM Provider 单元测试：mock requests.post，覆盖选型逻辑 +
DeepSeek/OpenAI（OpenAI 兼容）/Anthropic（独立实现）三个 Provider 的 URL/header/payload 构造。

依据 docs/plans/2026-07-31-multi-llm-provider-design.md 的设计目标编写，
若 memory_lib/providers/llm.py 与 __init__.py 的多 Provider 改造尚未完成，本文件会失败——
这是预期行为，改造完成后应自然转绿。
"""
from __future__ import annotations

import json

import pytest
import requests

from memory_lib.providers import LLMProviderError, get_llm_provider
from memory_lib.providers.llm import (
    AnthropicProvider,
    DeepSeekProvider,
    NullProvider,
    OpenAIProvider,
)


def _clear_llm_env(monkeypatch):
    for var in (
        "LLM_PROVIDER",
        "DEEPSEEK_API_KEY",
        "DEEPSEEK_BASE_URL",
        "DEEPSEEK_MODEL",
        "OPENAI_API_KEY",
        "OPENAI_BASE_URL",
        "OPENAI_MODEL",
        "ANTHROPIC_API_KEY",
        "ANTHROPIC_BASE_URL",
        "ANTHROPIC_MODEL",
    ):
        monkeypatch.delenv(var, raising=False)


@pytest.fixture()
def clean_env(monkeypatch):
    """每个用例开始前清空所有相关环境变量，避免本机 .env / shell 环境串扰。"""
    _clear_llm_env(monkeypatch)
    yield monkeypatch


# ---------------------------------------------------------------------------
# get_llm_provider() 选型逻辑
# ---------------------------------------------------------------------------


def test_get_llm_provider_unset_falls_back_to_null(clean_env):
    provider = get_llm_provider()
    assert isinstance(provider, NullProvider)


def test_get_llm_provider_unknown_value_falls_back_to_null(clean_env):
    clean_env.setenv("LLM_PROVIDER", "foobar")
    provider = get_llm_provider()
    assert isinstance(provider, NullProvider)


def test_get_llm_provider_openai_without_key_falls_back_to_null(clean_env):
    clean_env.setenv("LLM_PROVIDER", "openai")
    provider = get_llm_provider()
    assert isinstance(provider, NullProvider)


def test_get_llm_provider_openai_with_empty_key_falls_back_to_null(clean_env):
    clean_env.setenv("LLM_PROVIDER", "openai")
    clean_env.setenv("OPENAI_API_KEY", "")
    provider = get_llm_provider()
    assert isinstance(provider, NullProvider)


def test_get_llm_provider_openai_with_key_returns_openai_provider(clean_env):
    clean_env.setenv("LLM_PROVIDER", "openai")
    clean_env.setenv("OPENAI_API_KEY", "sk-test-openai")
    provider = get_llm_provider()
    assert isinstance(provider, OpenAIProvider)


def test_get_llm_provider_deepseek_without_key_falls_back_to_null(clean_env):
    clean_env.setenv("LLM_PROVIDER", "deepseek")
    provider = get_llm_provider()
    assert isinstance(provider, NullProvider)


def test_get_llm_provider_deepseek_with_key_returns_deepseek_provider(clean_env):
    clean_env.setenv("LLM_PROVIDER", "deepseek")
    clean_env.setenv("DEEPSEEK_API_KEY", "sk-test-deepseek")
    provider = get_llm_provider()
    assert isinstance(provider, DeepSeekProvider)


def test_get_llm_provider_anthropic_without_key_falls_back_to_null(clean_env):
    clean_env.setenv("LLM_PROVIDER", "anthropic")
    provider = get_llm_provider()
    assert isinstance(provider, NullProvider)


def test_get_llm_provider_anthropic_with_key_returns_anthropic_provider(clean_env):
    clean_env.setenv("LLM_PROVIDER", "anthropic")
    clean_env.setenv("ANTHROPIC_API_KEY", "sk-test-anthropic")
    provider = get_llm_provider()
    assert isinstance(provider, AnthropicProvider)


def test_get_llm_provider_case_insensitive(clean_env):
    clean_env.setenv("LLM_PROVIDER", "OpenAI")
    clean_env.setenv("OPENAI_API_KEY", "sk-test-openai")
    provider = get_llm_provider()
    assert isinstance(provider, OpenAIProvider)


# ---------------------------------------------------------------------------
# 公共 fake response helper
# ---------------------------------------------------------------------------


class _FakeResponse:
    def __init__(self, json_data: dict, status_code: int = 200):
        self._json_data = json_data
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")

    def json(self):
        return self._json_data


def _openai_style_response(instincts=None, project_facts=None):
    content = json.dumps({"instincts": instincts or [], "project_facts": project_facts or []})
    return _FakeResponse({"choices": [{"message": {"content": content}}]})


def _anthropic_style_response(instincts=None, project_facts=None):
    text = json.dumps({"instincts": instincts or [], "project_facts": project_facts or []})
    return _FakeResponse({"content": [{"text": text}]})


# ---------------------------------------------------------------------------
# OpenAIProvider / DeepSeekProvider（OpenAI 兼容基类）默认值 + 覆盖
# ---------------------------------------------------------------------------


def test_openai_provider_defaults(clean_env):
    clean_env.setenv("OPENAI_API_KEY", "sk-test-openai")
    provider = OpenAIProvider()
    assert provider.base_url == "https://api.openai.com/v1"
    assert provider.model == "gpt-4o-mini"


def test_openai_provider_custom_base_url_and_model(clean_env):
    clean_env.setenv("OPENAI_API_KEY", "sk-test-openai")
    clean_env.setenv("OPENAI_BASE_URL", "https://my-gateway.example.com/v1")
    clean_env.setenv("OPENAI_MODEL", "gpt-4o")
    provider = OpenAIProvider()
    assert provider.base_url == "https://my-gateway.example.com/v1"
    assert provider.model == "gpt-4o"


def test_deepseek_provider_defaults(clean_env):
    clean_env.setenv("DEEPSEEK_API_KEY", "sk-test-deepseek")
    provider = DeepSeekProvider()
    assert provider.base_url == "https://api.deepseek.com"
    assert provider.model == "deepseek-chat"


def test_deepseek_provider_custom_base_url_and_model(clean_env):
    clean_env.setenv("DEEPSEEK_API_KEY", "sk-test-deepseek")
    clean_env.setenv("DEEPSEEK_BASE_URL", "https://my-gateway.example.com")
    clean_env.setenv("DEEPSEEK_MODEL", "deepseek-reasoner")
    provider = DeepSeekProvider()
    assert provider.base_url == "https://my-gateway.example.com"
    assert provider.model == "deepseek-reasoner"


# ---------------------------------------------------------------------------
# OpenAIProvider.analyze() 请求构造 + 成功/失败路径
# ---------------------------------------------------------------------------


def test_openai_provider_analyze_request_and_parse(clean_env):
    clean_env.setenv("OPENAI_API_KEY", "sk-test-openai")
    provider = OpenAIProvider()

    captured = {}

    def fake_post(url, headers=None, json=None, timeout=None):
        captured["url"] = url
        captured["headers"] = headers
        captured["json"] = json
        captured["timeout"] = timeout
        return _openai_style_response()

    clean_env.setattr(requests, "post", fake_post)

    result = provider.analyze("some observations summary", "last assistant message")

    assert captured["url"] == f"{provider.base_url}/chat/completions"
    assert captured["headers"]["Authorization"] == f"Bearer {provider.api_key}"
    assert captured["json"]["model"] == provider.model
    assert captured["json"]["response_format"] == {"type": "json_object"}
    assert result == {"instincts": [], "project_facts": []}


def test_openai_provider_analyze_request_failure_raises(clean_env):
    clean_env.setenv("OPENAI_API_KEY", "sk-test-openai")
    provider = OpenAIProvider()

    def fake_post(*args, **kwargs):
        raise requests.RequestException("boom")

    clean_env.setattr(requests, "post", fake_post)

    with pytest.raises(LLMProviderError):
        provider.analyze("summary")


def test_deepseek_provider_analyze_request_and_parse(clean_env):
    clean_env.setenv("DEEPSEEK_API_KEY", "sk-test-deepseek")
    provider = DeepSeekProvider()

    captured = {}

    def fake_post(url, headers=None, json=None, timeout=None):
        captured["url"] = url
        captured["headers"] = headers
        captured["json"] = json
        return _openai_style_response()

    clean_env.setattr(requests, "post", fake_post)

    result = provider.analyze("some observations summary")

    assert captured["url"] == f"{provider.base_url}/chat/completions"
    assert captured["headers"]["Authorization"] == f"Bearer {provider.api_key}"
    assert captured["json"]["model"] == provider.model
    assert captured["json"]["response_format"] == {"type": "json_object"}
    assert result == {"instincts": [], "project_facts": []}


def test_deepseek_provider_analyze_request_failure_raises(clean_env):
    clean_env.setenv("DEEPSEEK_API_KEY", "sk-test-deepseek")
    provider = DeepSeekProvider()

    def fake_post(*args, **kwargs):
        raise requests.RequestException("boom")

    clean_env.setattr(requests, "post", fake_post)

    with pytest.raises(LLMProviderError):
        provider.analyze("summary")


# ---------------------------------------------------------------------------
# AnthropicProvider 默认值 + 覆盖
# ---------------------------------------------------------------------------


def test_anthropic_provider_defaults(clean_env):
    clean_env.setenv("ANTHROPIC_API_KEY", "sk-test-anthropic")
    provider = AnthropicProvider()
    assert provider.base_url == "https://api.anthropic.com"
    assert provider.model == "claude-haiku-4-5-20251001"


def test_anthropic_provider_custom_base_url_and_model(clean_env):
    clean_env.setenv("ANTHROPIC_API_KEY", "sk-test-anthropic")
    clean_env.setenv("ANTHROPIC_BASE_URL", "https://my-gateway.example.com")
    clean_env.setenv("ANTHROPIC_MODEL", "claude-opus-4")
    provider = AnthropicProvider()
    assert provider.base_url == "https://my-gateway.example.com"
    assert provider.model == "claude-opus-4"


# ---------------------------------------------------------------------------
# AnthropicProvider.analyze() 请求构造 + 成功/失败路径
# ---------------------------------------------------------------------------


def test_anthropic_provider_analyze_request_and_parse(clean_env):
    clean_env.setenv("ANTHROPIC_API_KEY", "sk-test-anthropic")
    provider = AnthropicProvider()

    captured = {}

    def fake_post(url, headers=None, json=None, timeout=None):
        captured["url"] = url
        captured["headers"] = headers
        captured["json"] = json
        return _anthropic_style_response()

    clean_env.setattr(requests, "post", fake_post)

    result = provider.analyze("some observations summary", "last assistant message")

    assert captured["url"] == f"{provider.base_url}/v1/messages"
    assert captured["headers"]["x-api-key"] == provider.api_key
    assert "Authorization" not in captured["headers"]
    assert "anthropic-version" in captured["headers"]
    assert "max_tokens" in captured["json"]
    assert "system" in captured["json"]
    assert "response_format" not in captured["json"]
    messages = captured["json"]["messages"]
    assert len(messages) == 1
    assert messages[0]["role"] == "user"
    assert result == {"instincts": [], "project_facts": []}


def test_anthropic_provider_mine_procedure_parses_content_text(clean_env):
    """确认 mine_procedure 走 data["content"][0]["text"] 解析，不是 OpenAI 的 choices[0].message.content。"""
    clean_env.setenv("ANTHROPIC_API_KEY", "sk-test-anthropic")
    provider = AnthropicProvider()

    payload = {"is_procedure": True, "id": "test-proc", "task_type": "test", "steps": ["a", "b"], "note": "", "is_successful": True}
    payload_text = json.dumps(payload)

    def fake_post(url, headers=None, json=None, timeout=None):
        return _FakeResponse({"content": [{"text": payload_text}]})

    clean_env.setattr(requests, "post", fake_post)

    result = provider.mine_procedure("steps summary", "assistant text")

    assert result is not None
    assert result["id"] == "test-proc"
    assert result["steps"] == ["a", "b"]
    assert result["is_successful"] is True


def test_anthropic_provider_analyze_request_failure_raises(clean_env):
    clean_env.setenv("ANTHROPIC_API_KEY", "sk-test-anthropic")
    provider = AnthropicProvider()

    def fake_post(*args, **kwargs):
        raise requests.RequestException("boom")

    clean_env.setattr(requests, "post", fake_post)

    with pytest.raises(LLMProviderError):
        provider.analyze("summary")
