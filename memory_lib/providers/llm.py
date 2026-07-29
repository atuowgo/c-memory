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

    @abc.abstractmethod
    def summarize_conversation(self, previous_summary: str, new_turns_text: str) -> str:
        """滚动总结：融合 previous_summary 和 new_turns_text，产出更新后的总结文本。
        previous_summary 可能是空字符串（第一次总结，还没有历史总结）。
        返回值是纯文本（不是 JSON），会被直接整段写入 memory/project-summary.md。"""
        raise NotImplementedError


# 提示词字段结构完全对齐得物开源实现（agent-memory-system 的 analyze_instincts.py 的
# LLM_ANALYSIS_PROMPT / extract_memories.py 的 EXTRACT_PROMPT，2026-07-28 curl 拉取源码核实）：
# - instincts 用 id(LLM 直接生成的英文 kebab-case) + trigger + action + domain + evidence
# - project_facts 用 name(同上) + description + body + type
# id/name 均由 LLM 直接产出，不再走本地对中文文本 slugify——这样文件名/id 才会和得物一样是英文。
# 唯一未对齐之处：project_facts 额外要求 keywords 字段，这是我们自己为语义去重
# （find_similar_memory 用 keywords 交集做分组门槛）加的，得物原版 schema 没有这个字段。
_SYSTEM_PROMPT = """你是一个行为模式与记忆提取专家。给你一段本次会话的操作观测摘要，
可能还附带最后一轮 assistant 回复，请分析其中反映出的：

1. 行为习惯模式（instincts）：
   - id：kebab-case 英文唯一标识，如 read-before-edit-pattern
   - trigger：触发场景描述
   - action：推荐的行为描述
   - domain：只能是 workflow / testing / git / code-style / project-context 之一
   - evidence：支持证据

2. 值得长期记住的记忆（project_facts）：
   提取标准——项目级信息（技术栈/目录结构/配置方式）、用户偏好/反馈、踩过的坑/错误修复方法、工作流约束（部署流程/分支策略）。
   不要提取：一次性的临时操作、过于细节的代码变更、显而易见的通用知识。
   - name：kebab-case 英文唯一标识，如 uses-pnpm
   - description：一句话描述这条记忆的核心内容
   - body：详细说明，包括 why 和 how
   - type：project（项目事实）/ feedback（用户偏好反馈）/ error（踩坑记录）/ workflow（工作流约束）之一
   - keywords：1-3 个用于去重分组的关键词

严格按以下 JSON 格式输出，不要输出任何其他文字：
{
  "instincts": [
    {"id": "read-before-edit-pattern", "trigger": "触发场景描述", "action": "推荐的行为描述", "domain": "workflow", "evidence": "支持证据"}
  ],
  "project_facts": [
    {"name": "uses-pnpm", "description": "一句话描述", "body": "详细说明", "type": "project", "keywords": ["pnpm"]}
  ]
}

如果没有发现任何模式或事实，对应字段返回空数组。"""


# 滚动总结 prompt：目标是"持续演进的项目工作记忆"（情景记忆），跟上面 _SYSTEM_PROMPT 抽取的
# "行为习惯/项目事实"（语义记忆）是两条独立能力，不复用同一个 system prompt。
# 输出要求见设计文档第4节：正文是纯 markdown 叙述性总结（不是结构化列表），风格类似"项目进展简报"。
_SUMMARY_SYSTEM_PROMPT = """你是一个项目工作记忆维护助手。你会收到"当前项目总结"和"新增对话"两部分内容，
请把二者融合成一份更新后的总结，用来覆盖原有总结。

要求：
1. 融合新内容：把新增对话里反映出的进展、决定、待办自然地并入总结。
2. 保留仍然重要的旧信息：当前项目总结里还有效、还相关的内容要继续保留。
3. 去掉过时/已解决的内容：当前项目总结里已经被新增对话解决、否决或不再相关的内容要删掉，避免总结越滚越长。
4. 输出风格：一段能读的、叙述性的 markdown 文字（类似"项目进展简报"），说清楚这个项目在做什么、
   最近聊了什么、决定了什么、还有什么待办事项。不要输出 JSON，不要写成纯罗列的 bullet point 列表。
5. 直接输出总结正文本身，不要输出任何解释性文字、前缀或后缀说明。"""


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

    def summarize_conversation(self, previous_summary: str, new_turns_text: str) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        user_content = (
            f"## 当前项目总结\n\n{previous_summary or '(无，这是第一次总结)'}\n\n"
            f"## 新增对话\n\n{new_turns_text}"
        )
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": _SUMMARY_SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            "temperature": 0.2,
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
        except (KeyError, IndexError, ValueError) as exc:
            raise LLMProviderError(f"DeepSeek API 响应解析失败: {exc}") from exc

        return content.strip()


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
                        "name": f"uses-{manager}",
                        "description": f"项目使用 {manager}",
                        "body": f"项目使用 {manager} 作为包管理器",
                        "type": "project",
                        "keywords": [manager],
                    }
                )
        return {"instincts": [], "project_facts": project_facts}

    def summarize_conversation(self, previous_summary: str, new_turns_text: str) -> str:
        # 无 API key 时不做真正总结，原样返回旧总结——至少不丢已有内容，也绝不抛异常。
        return previous_summary
