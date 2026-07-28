"""Embedding Provider 抽象：把文本转成向量用于余弦相似度召回。"""
from __future__ import annotations

import abc
import os

import requests


class EmbeddingProviderError(Exception):
    """Embedding Provider 调用失败（网络异常/超时/响应解析失败）。"""


class EmbeddingProvider(abc.ABC):
    """Embedding Provider 抽象基类。"""

    # 输出维度是否固定/跨调用稳定，决定 recall.py 能不能用 vector_cache 缓存。
    # TF-IDF 这类"每次现场 fit"的实现必须保持 False。
    SUPPORTS_CACHE = False

    @abc.abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]:
        """把一批文本转成向量列表，顺序与输入一致。"""
        raise NotImplementedError


class ArkProvider(EmbeddingProvider):
    """火山引擎 Ark multimodal embedding。接口格式参考仓库根目录 embedding-demo.txt。"""

    TIMEOUT_SECONDS = 5
    SUPPORTS_CACHE = True

    def __init__(self) -> None:
        self.api_key = os.environ.get("ARK_API_KEY", "")
        base_url = os.environ.get("ARK_EMBEDDING_BASE_URL", "").rstrip("/")
        self.base_url = base_url
        self.model = os.environ.get("ARK_EMBEDDING_MODEL", "")
        self.dim = int(os.environ.get("ARK_EMBEDDING_DIM", "2048"))

    def embed(self, texts: list[str]) -> list[list[float]]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        vectors: list[list[float]] = []
        try:
            for text in texts:
                payload = {
                    "model": self.model,
                    "input": [{"type": "text", "text": text}],
                }
                resp = requests.post(
                    f"{self.base_url}/embeddings/multimodal",
                    headers=headers,
                    json=payload,
                    timeout=self.TIMEOUT_SECONDS,
                )
                resp.raise_for_status()
                data = resp.json()
                # multimodal 接口对单条 input 返回单个融合向量；响应结构以
                # data.data 为 dict({"embedding": [...]})或 list([{"embedding": [...]}])
                # 两种已知形态，做兼容处理。
                raw = data["data"]
                if isinstance(raw, list):
                    vector = raw[0]["embedding"]
                else:
                    vector = raw["embedding"]
                vectors.append(vector)
        except requests.RequestException as exc:
            raise EmbeddingProviderError(f"Ark embedding API 请求失败: {exc}") from exc
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise EmbeddingProviderError(f"Ark embedding API 响应解析失败: {exc}") from exc

        return vectors


class TfidfProvider(EmbeddingProvider):
    """本地 sklearn TfidfVectorizer 兜底方案。

    每次调用对传入的整批 texts 一起 fit_transform，不追求跨调用词表一致性
    （本地兜底方案，只需保证同一批 texts 内部可比较余弦相似度）。
    """

    def embed(self, texts: list[str]) -> list[list[float]]:
        from sklearn.feature_extraction.text import TfidfVectorizer

        if not texts:
            return []

        vectorizer = TfidfVectorizer()
        matrix = vectorizer.fit_transform(texts)
        return matrix.toarray().tolist()
