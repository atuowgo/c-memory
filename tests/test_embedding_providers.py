"""memory_lib.providers 多 Embedding Provider 单元测试：mock requests.post，覆盖选型逻辑 +
OpenAIProvider（embedding 版）的请求构造/批量输入/排序/错误路径。

依据 docs/plans/2026-07-31-multi-embedding-provider-design.md 的设计目标编写。
"""
from __future__ import annotations

import pytest
import requests

from memory_lib.providers import EmbeddingProviderError, get_embedding_provider
from memory_lib.providers.embedding import (
    ArkProvider,
    OpenAIProvider,
    TfidfProvider,
)


def _clear_embedding_env(monkeypatch):
    for var in (
        "EMBEDDING_PROVIDER",
        "ARK_API_KEY",
        "ARK_EMBEDDING_BASE_URL",
        "ARK_EMBEDDING_MODEL",
        "ARK_EMBEDDING_DIM",
        "OPENAI_EMBEDDING_API_KEY",
        "OPENAI_EMBEDDING_BASE_URL",
        "OPENAI_EMBEDDING_MODEL",
    ):
        monkeypatch.delenv(var, raising=False)


@pytest.fixture()
def clean_env(monkeypatch):
    """每个用例开始前清空所有相关环境变量，避免本机 .env / shell 环境串扰。"""
    _clear_embedding_env(monkeypatch)
    yield monkeypatch


class _FakeResponse:
    def __init__(self, json_data: dict, status_code: int = 200):
        self._json_data = json_data
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")

    def json(self):
        return self._json_data


def _ark_style_response():
    return _FakeResponse({"data": {"embedding": [0.1, 0.2, 0.3]}})


# ---------------------------------------------------------------------------
# get_embedding_provider() 选型逻辑
# ---------------------------------------------------------------------------


def test_get_embedding_provider_unset_falls_back_to_tfidf(clean_env):
    provider = get_embedding_provider()
    assert isinstance(provider, TfidfProvider)


def test_get_embedding_provider_unknown_value_falls_back_to_tfidf(clean_env):
    clean_env.setenv("EMBEDDING_PROVIDER", "foobar")
    provider = get_embedding_provider()
    assert isinstance(provider, TfidfProvider)


def test_get_embedding_provider_openai_without_key_falls_back_to_tfidf(clean_env):
    clean_env.setenv("EMBEDDING_PROVIDER", "openai")
    provider = get_embedding_provider()
    assert isinstance(provider, TfidfProvider)


def test_get_embedding_provider_openai_with_empty_key_falls_back_to_tfidf(clean_env):
    clean_env.setenv("EMBEDDING_PROVIDER", "openai")
    clean_env.setenv("OPENAI_EMBEDDING_API_KEY", "")
    provider = get_embedding_provider()
    assert isinstance(provider, TfidfProvider)


def test_get_embedding_provider_openai_with_key_returns_openai_provider_no_network(clean_env):
    clean_env.setenv("EMBEDDING_PROVIDER", "openai")
    clean_env.setenv("OPENAI_EMBEDDING_API_KEY", "sk-test-openai")

    calls = []

    def fake_post(*args, **kwargs):
        calls.append((args, kwargs))
        raise AssertionError("openai 分支不应该探活发请求")

    clean_env.setattr(requests, "post", fake_post)

    provider = get_embedding_provider()

    assert isinstance(provider, OpenAIProvider)
    assert calls == []


def test_get_embedding_provider_ark_without_key_falls_back_to_tfidf(clean_env):
    clean_env.setenv("EMBEDDING_PROVIDER", "ark")

    calls = []

    def fake_post(*args, **kwargs):
        calls.append((args, kwargs))
        raise AssertionError("ARK_API_KEY 为空不应该触发探活请求")

    clean_env.setattr(requests, "post", fake_post)

    provider = get_embedding_provider()

    assert isinstance(provider, TfidfProvider)
    assert calls == []


def test_get_embedding_provider_ark_with_key_probe_success_returns_ark_provider(clean_env):
    clean_env.setenv("EMBEDDING_PROVIDER", "ark")
    clean_env.setenv("ARK_API_KEY", "ark-test-key")

    def fake_post(url, headers=None, json=None, timeout=None):
        return _ark_style_response()

    clean_env.setattr(requests, "post", fake_post)

    provider = get_embedding_provider()
    assert isinstance(provider, ArkProvider)


def test_get_embedding_provider_ark_with_key_probe_failure_falls_back_to_tfidf(clean_env):
    clean_env.setenv("EMBEDDING_PROVIDER", "ark")
    clean_env.setenv("ARK_API_KEY", "ark-test-key")

    def fake_post(*args, **kwargs):
        raise requests.RequestException("boom")

    clean_env.setattr(requests, "post", fake_post)

    provider = get_embedding_provider()
    assert isinstance(provider, TfidfProvider)


def test_get_embedding_provider_case_insensitive(clean_env):
    clean_env.setenv("EMBEDDING_PROVIDER", "OpenAI")
    clean_env.setenv("OPENAI_EMBEDDING_API_KEY", "sk-test-openai")

    def fake_post(*args, **kwargs):
        raise AssertionError("openai 分支不应该探活发请求")

    clean_env.setattr(requests, "post", fake_post)

    provider = get_embedding_provider()
    assert isinstance(provider, OpenAIProvider)


# ---------------------------------------------------------------------------
# OpenAIProvider（embedding 版）默认值 + 覆盖
# ---------------------------------------------------------------------------


def test_openai_embedding_provider_defaults(clean_env):
    clean_env.setenv("OPENAI_EMBEDDING_API_KEY", "sk-test-openai")
    provider = OpenAIProvider()
    assert provider.base_url == "https://api.openai.com/v1"
    assert provider.model == "text-embedding-3-small"


def test_openai_embedding_provider_custom_base_url_and_model(clean_env):
    clean_env.setenv("OPENAI_EMBEDDING_API_KEY", "sk-test-openai")
    clean_env.setenv("OPENAI_EMBEDDING_BASE_URL", "https://my-gateway.example.com/v1")
    clean_env.setenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-large")
    provider = OpenAIProvider()
    assert provider.base_url == "https://my-gateway.example.com/v1"
    assert provider.model == "text-embedding-3-large"


# ---------------------------------------------------------------------------
# OpenAIProvider.embed() 请求构造 + 批量输入 + 排序 + 错误路径
# ---------------------------------------------------------------------------


def test_openai_embedding_provider_embed_request_and_batch(clean_env):
    clean_env.setenv("OPENAI_EMBEDDING_API_KEY", "sk-test-openai")
    provider = OpenAIProvider()

    captured = {}
    call_count = []

    def fake_post(url, headers=None, json=None, timeout=None):
        call_count.append(1)
        captured["url"] = url
        captured["headers"] = headers
        captured["json"] = json
        return _FakeResponse(
            {
                "data": [
                    {"embedding": [0.1, 0.2], "index": 0},
                    {"embedding": [0.3, 0.4], "index": 1},
                ]
            }
        )

    clean_env.setattr(requests, "post", fake_post)

    result = provider.embed(["文本A", "文本B"])

    assert len(call_count) == 1
    assert captured["url"] == f"{provider.base_url}/embeddings"
    assert captured["headers"]["Authorization"] == f"Bearer {provider.api_key}"
    assert captured["json"]["input"] == ["文本A", "文本B"]
    assert result == [[0.1, 0.2], [0.3, 0.4]]


def test_openai_embedding_provider_embed_sorts_by_index(clean_env):
    clean_env.setenv("OPENAI_EMBEDDING_API_KEY", "sk-test-openai")
    provider = OpenAIProvider()

    def fake_post(url, headers=None, json=None, timeout=None):
        return _FakeResponse(
            {
                "data": [
                    {"embedding": [0.3, 0.4], "index": 1},
                    {"embedding": [0.1, 0.2], "index": 0},
                ]
            }
        )

    clean_env.setattr(requests, "post", fake_post)

    result = provider.embed(["文本A", "文本B"])

    assert result == [[0.1, 0.2], [0.3, 0.4]]


def test_openai_embedding_provider_embed_empty_list_no_network(clean_env):
    clean_env.setenv("OPENAI_EMBEDDING_API_KEY", "sk-test-openai")
    provider = OpenAIProvider()

    calls = []

    def fake_post(*args, **kwargs):
        calls.append((args, kwargs))
        raise AssertionError("空列表不应该发起网络请求")

    clean_env.setattr(requests, "post", fake_post)

    result = provider.embed([])

    assert result == []
    assert calls == []


def test_openai_embedding_provider_embed_request_failure_raises(clean_env):
    clean_env.setenv("OPENAI_EMBEDDING_API_KEY", "sk-test-openai")
    provider = OpenAIProvider()

    def fake_post(*args, **kwargs):
        raise requests.RequestException("boom")

    clean_env.setattr(requests, "post", fake_post)

    with pytest.raises(EmbeddingProviderError):
        provider.embed(["x"])
