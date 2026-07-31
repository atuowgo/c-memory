---
标题: LLM Provider 扩展 OpenAI / Anthropic 支持设计
状态: 已确认，待实现
创建时间: 2026-07-31
---

## 1. 背景与目标

当前 LLM Provider 只有 `DeepSeekProvider`（硬编码 `base_url`）和 `NullProvider`（规则兜底），选型逻辑是"`DEEPSEEK_API_KEY` 非空就用 DeepSeek"。
目标：新增 `OpenAIProvider`/`AnthropicProvider`，三个真实 Provider 都统一成 `model`/`base_url`/`api_key` 三参数可配置形态，
方便挪到其他环境（换用别的 API 中转/自建网关/不同厂商）时只改环境变量，不改代码。

## 2. Provider 选择机制

新增显式环境变量 `LLM_PROVIDER=deepseek|openai|anthropic`（不区分大小写），未设置或值不识别一律降级为 `NullProvider`。
**不做"哪个 key 非空就用哪个"的自动探测**——同时配置多个 key 时容易产生歧义，显式指定意图更明确，换环境只需要改一个变量。

选中的 Provider 如果对应 `{PREFIX}_API_KEY` 为空，同样降级为 `NullProvider`（避免带着空 key 发真实请求，白白等一次网络超时才失败）。

```python
def get_llm_provider() -> LLMProvider:
    name = os.environ.get("LLM_PROVIDER", "").strip().lower()
    provider_cls = {"deepseek": DeepSeekProvider, "openai": OpenAIProvider, "anthropic": AnthropicProvider}.get(name)
    if provider_cls is None:
        return NullProvider()
    provider = provider_cls()
    if not provider.api_key:
        return NullProvider()
    return provider
```

## 3. 三参数配置

| Provider | API Key | Base URL（有默认值，可覆盖） | Model（有默认值，可覆盖） |
|---|---|---|---|
| DeepSeek | `DEEPSEEK_API_KEY` | `DEEPSEEK_BASE_URL`，默认 `https://api.deepseek.com` | `DEEPSEEK_MODEL`，默认 `deepseek-chat` |
| OpenAI | `OPENAI_API_KEY` | `OPENAI_BASE_URL`，默认 `https://api.openai.com/v1` | `OPENAI_MODEL`，默认 `gpt-4o-mini` |
| Anthropic | `ANTHROPIC_API_KEY` | `ANTHROPIC_BASE_URL`，默认 `https://api.anthropic.com` | `ANTHROPIC_MODEL`，默认 `claude-haiku-4-5-20251001` |

**破坏性变更**：原来的 `LLM_MODEL` 变量废弃，改成 `DEEPSEEK_MODEL`（DeepSeek 从"唯一实现"变成"三选一"，不该再用不带前缀的通用名）。
本仓库自己的 `.env` 也要跟着改（本地文件，不进 git，实现时一并处理，不会打印其中的真实密钥）。

## 4. 实现：DeepSeek/OpenAI 共用请求逻辑，Anthropic 单独实现

**DeepSeek 和 OpenAI 都是 OpenAI 兼容接口**（`/chat/completions`，`Authorization: Bearer`，`response_format:{"type":"json_object"}` 强制 JSON），
抽一个私有基类 `_OpenAICompatibleProvider(LLMProvider)` 承载三个方法（`analyze`/`summarize_conversation`/`mine_procedure`）的完整实现，
`DeepSeekProvider`/`OpenAIProvider` 只是设置类属性（`ENV_PREFIX`/`DEFAULT_BASE_URL`/`DEFAULT_MODEL`）的薄子类，避免同一套请求/异常处理代码抄三份。

**Anthropic 不是 OpenAI 兼容**（`/v1/messages`，`x-api-key` 而不是 `Authorization: Bearer`，需要额外的 `anthropic-version` 请求头，
`system` 是顶层参数而不是 messages 里的一条，`max_tokens` 是必填参数，响应体结构是 `content[0].text` 不是 `choices[0].message.content`），
`AnthropicProvider(LLMProvider)` 独立实现三个方法，不继承 `_OpenAICompatibleProvider`。

**JSON 输出的可靠性差异（已知取舍，不在本轮解决）**：DeepSeek/OpenAI 靠 `response_format={"type":"json_object"}` API 层强制 JSON + prompt 指令双重保证；
Anthropic 经典 Messages API 没有等价的强制 JSON 参数，只能靠 prompt 里"严格按JSON格式输出"的指令 + `json.loads()` 解析，可靠性理论上略低于前两者。
现有三个 prompt（`_SYSTEM_PROMPT`/`_SUMMARY_SYSTEM_PROMPT`/`_MINE_PROCEDURE_SYSTEM_PROMPT`）已经要求"严格 JSON、不要输出其他文字"，
Anthropic 复用同一份 prompt，不单独定制。所有三个 Provider 的错误处理约定不变：请求/解析失败都 `raise LLMProviderError`，不吞异常，
由调用方 hook 脚本负责 try/except 降级。

## 5. 改动文件清单

| 文件 | 改动类型 | 说明 |
|---|---|---|
| `memory_lib/providers/llm.py` | 改 | 新增 `_OpenAICompatibleProvider` 基类；`DeepSeekProvider` 改造成可配置薄子类；新增 `OpenAIProvider`/`AnthropicProvider` |
| `memory_lib/providers/__init__.py` | 改 | `get_llm_provider()` 改为按 `LLM_PROVIDER` 显式选择 + 空 key 兜底 Null |
| `.env.example` | 改 | 补三个 Provider 的完整变量块，废弃 `LLM_MODEL` |
| `README.md` | 改 | 同步环境变量说明 |
| `.env`（本地，不进 git） | 改 | 同步变量名，不改变已有真实 key 的值 |
| `tests/test_llm_providers.py` | 新 | mock `requests.post`，覆盖三个 Provider 的 URL/header/payload 构造 + `get_llm_provider()` 选择逻辑 |

`memory_lib/providers/embedding.py`（Ark/TF-IDF）不在本轮范围内，用户明确只要求 LLM Provider。

## 6. 范围之外（本轮不做）

- Anthropic 用 tool-use 强制结构化输出（更可靠但改动更大），本轮先复用现有 prompt-only 方案。
- `LLM_PROVIDER` 自动探测/多 key 优先级兜底，用户明确要求显式指定，不做隐式猜测。
