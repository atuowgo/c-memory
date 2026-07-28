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
    def analyze(self, observations_summary: str, last_message: str = "") -> dict:
        """分析观测摘要（+ 可选的最后一轮 assistant 消息），返回 {"instincts": [...], "project_facts": [...]}。"""
        raise NotImplementedError


# 提示词内容对齐得物开源实现（agent-memory-system 的 analyze_instincts.py / extract_memories.py）：
# instincts 的 domain 固定枚举、project_facts 的排除清单与 type 枚举都来自那两份 prompt。
_SYSTEM_PROMPT = """你是一个行为模式与记忆提取专家。给你一段本次会话的操作观测摘要，
可能还附带最后一轮 assistant 回复，请分析其中反映出的：

1. 行为习惯模式（instincts），例如"编辑文件前先阅读该文件"：
   - pattern：具体的触发场景+行为描述
   - domain：只能是 workflow / testing / git / code-style / project-context 之一

2. 值得长期记住的记忆（project_facts）：
   提取标准——项目级信息（技术栈/目录结构/配置方式）、用户偏好/反馈、踩过的坑/错误修复方法、工作流约束（部署流程/分支策略）。
   不要提取：一次性的临时操作、过于细节的代码变更、显而易见的通用知识。
   type：project（项目事实）/ feedback（用户偏好反馈）/ error（踩坑记录）/ workflow（工作流约束）之一

严格按以下 JSON 格式输出，不要输出任何其他文字：
{
  "instincts": [
    {"pattern": "行为模式描述", "domain": "workflow", "evidence": "支持证据"}
  ],
  "project_facts": [
    {"fact": "事实描述", "type": "project", "keywords": ["关键词1", "关键词2"]}
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

    def analyze(self, observations_summary: str, last_message: str = "") -> dict:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        user_content = (
            f"## 最后一轮对话\n\n{last_message or '(无)'}\n\n"
            f"## 本次会话的工具调用摘要\n\n{observations_summary}"
        )
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
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

    def analyze(self, observations_summary: str, last_message: str = "") -> dict:
        project_facts = []
        text = observations_summary or ""
        for manager, pattern in self._PACKAGE_MANAGER_PATTERNS.items():
            if pattern.search(text):
                project_facts.append(
                    {
                        "fact": f"项目使用 {manager}",
                        "type": "project",
                        "keywords": [manager],
                    }
                )
        return {"instincts": [], "project_facts": project_facts}
