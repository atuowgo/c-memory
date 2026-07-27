"""Provider 工厂函数：按环境变量配置和探活结果选择合适的 Provider 实现。"""
from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()

from .embedding import ArkProvider, EmbeddingProvider, EmbeddingProviderError, TfidfProvider
from .llm import DeepSeekProvider, LLMProvider, LLMProviderError, NullProvider

__all__ = [
    "get_llm_provider",
    "get_embedding_provider",
    "LLMProvider",
    "DeepSeekProvider",
    "NullProvider",
    "LLMProviderError",
    "EmbeddingProvider",
    "ArkProvider",
    "TfidfProvider",
    "EmbeddingProviderError",
]


def get_llm_provider() -> LLMProvider:
    """DEEPSEEK_API_KEY 非空 -> DeepSeekProvider，否则 NullProvider。"""
    if os.environ.get("DEEPSEEK_API_KEY", "").strip():
        return DeepSeekProvider()
    return NullProvider()


def get_embedding_provider() -> EmbeddingProvider:
    """ARK_API_KEY 非空时先探活（5s 超时），成功用 ArkProvider，否则 TfidfProvider。"""
    if os.environ.get("ARK_API_KEY", "").strip():
        try:
            provider = ArkProvider()
            provider.embed(["ping"])
            return provider
        except Exception:
            return TfidfProvider()
    return TfidfProvider()
