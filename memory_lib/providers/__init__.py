"""Provider 工厂函数：按环境变量配置和探活结果选择合适的 Provider 实现。"""
from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()

from .embedding import (
    ArkProvider,
    EmbeddingProvider,
    EmbeddingProviderError,
    OpenAIProvider as EmbeddingOpenAIProvider,
    TfidfProvider,
)
from .llm import (
    AnthropicProvider,
    DeepSeekProvider,
    LLMProvider,
    LLMProviderError,
    NullProvider,
    OpenAIProvider,
)

__all__ = [
    "get_llm_provider",
    "get_embedding_provider",
    "LLMProvider",
    "DeepSeekProvider",
    "OpenAIProvider",
    "AnthropicProvider",
    "NullProvider",
    "LLMProviderError",
    "EmbeddingProvider",
    "ArkProvider",
    "EmbeddingOpenAIProvider",
    "TfidfProvider",
    "EmbeddingProviderError",
]


def get_llm_provider() -> LLMProvider:
    """按 LLM_PROVIDER 环境变量显式选择（deepseek/openai/anthropic），未设置/不识别/对应
    API_KEY 为空都降级为 NullProvider——不做多 key 同时存在时的自动探测，换环境只改这一个变量。"""
    name = os.environ.get("LLM_PROVIDER", "").strip().lower()
    provider_cls = {
        "deepseek": DeepSeekProvider,
        "openai": OpenAIProvider,
        "anthropic": AnthropicProvider,
    }.get(name)
    if provider_cls is None:
        return NullProvider()
    provider = provider_cls()
    if not provider.api_key:
        return NullProvider()
    return provider


def get_embedding_provider() -> EmbeddingProvider:
    """按 EMBEDDING_PROVIDER 环境变量显式选择（ark/openai/tfidf），未设置/不识别/对应
    API_KEY 为空都降级为 TfidfProvider（本地兜底，不需要任何 key）。ark 选中后仍保留
    现有的探活逻辑（embed(["ping"])，失败也降级 Tfidf）；openai 不探活，只检查 key 非空即用，
    跟 LLM Provider 那边的简单模式一致，不引入额外的一次网络往返。"""
    name = os.environ.get("EMBEDDING_PROVIDER", "").strip().lower()
    if name == "ark":
        if not os.environ.get("ARK_API_KEY", "").strip():
            return TfidfProvider()
        try:
            provider = ArkProvider()
            provider.embed(["ping"])
            return provider
        except Exception:
            return TfidfProvider()
    if name == "openai":
        if not os.environ.get("OPENAI_EMBEDDING_API_KEY", "").strip():
            return TfidfProvider()
        return EmbeddingOpenAIProvider()
    return TfidfProvider()
