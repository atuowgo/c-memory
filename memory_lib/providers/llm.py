"""LLM Provider 抽象：语义分析观测摘要，产出候选行为模式/项目知识。"""
from __future__ import annotations

import abc
import json
import os
import re

import requests


class LLMProviderError(Exception):
    """LLM Provider 调用失败（网络异常/超时/响应解析失败）。"""


class LLMProvider(abc.ABC):
    """LLM Provider 抽象基类。"""

    @abc.abstractmethod
    def analyze(self, observations_summary: str) -> dict:
        """分析观测摘要，返回 {"instincts": [...], "project_facts": [...]}。"""
        raise NotImplementedError


_SYSTEM_PROMPT = """你是一个 Claude Code 会话观测分析助手。给你一段本次会话的操作观测摘要，
请分析其中反映出的：
1. 用户的行为习惯模式（instincts），例如"编辑文件前先阅读该文件"
2. 项目相关的客观事实（project_facts），例如"项目使用 pnpm 作为包管理器"

严格按以下 JSON 格式输出，不要输出任何其他文字：
{
  "instincts": [
    {"pattern": "行为模式描述", "domain": "所属领域", "evidence": "支持证据"}
  ],
  "project_facts": [
    {"fact": "事实描述", "keywords": ["关键词1", "关键词2"]}
  ]
}

如果没有发现任何模式或事实，对应字段返回空数组。"""


class DeepSeekProvider(LLMProvider):
    """DeepSeek（OpenAI 兼容接口）LLM Provider。"""

    API_URL = "https://api.deepseek.com/chat/completions"
    TIMEOUT_SECONDS = 10

    def __init__(self) -> None:
        self.api_key = os.environ.get("DEEPSEEK_API_KEY", "")
        self.model = os.environ.get("LLM_MODEL", "deepseek-chat")

    def analyze(self, observations_summary: str) -> dict:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": observations_summary},
            ],
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
        }
        try:
            resp = requests.post(
                self.API_URL,
                headers=headers,
                json=payload,
                timeout=self.TIMEOUT_SECONDS,
            )
            resp.raise_for_status()
        except requests.RequestException as exc:
            raise LLMProviderError(f"DeepSeek API 请求失败: {exc}") from exc

        try:
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            result = json.loads(content)
        except (KeyError, IndexError, ValueError) as exc:
            raise LLMProviderError(f"DeepSeek API 响应解析失败: {exc}") from exc

        return {
            "instincts": result.get("instincts", []),
            "project_facts": result.get("project_facts", []),
        }


class NullProvider(LLMProvider):
    """纯规则 fallback，不发网络请求。目前支持包管理器关键词识别。"""

    # 用 \b 词边界正则，避免 "npm" 误匹配到 "pnpm" 子串
    _PACKAGE_MANAGER_PATTERNS = {
        "pnpm": re.compile(r"\bpnpm\b"),
        "npm": re.compile(r"\bnpm\b"),
        "yarn": re.compile(r"\byarn\b"),
    }

    def analyze(self, observations_summary: str) -> dict:
        project_facts = []
        text = observations_summary or ""
        for manager, pattern in self._PACKAGE_MANAGER_PATTERNS.items():
            if pattern.search(text):
                project_facts.append(
                    {
                        "fact": f"项目使用 {manager}",
                        "keywords": [manager],
                    }
                )
        return {"instincts": [], "project_facts": project_facts}
