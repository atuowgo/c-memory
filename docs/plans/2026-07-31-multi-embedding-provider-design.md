---
标题: Embedding Provider 扩展通用 OpenAI 兼容支持设计
状态: 已确认，待实现
创建时间: 2026-07-31
---

## 1. 背景与目标

延续同一天 LLM Provider 多选型的思路（见 `2026-07-31-multi-llm-provider-design.md`），embedding 这边现在只有 `ArkProvider`（火山引擎专属 multimodal 接口）和 `TfidfProvider`（本地兜底），
选型逻辑是"`ARK_API_KEY` 非空就探活，成功用 Ark，否则 Tfidf"。新增一个**兼容 OpenAI `/embeddings` 接口格式的通用 Provider**（不限定官方 OpenAI，可指向任意中转/自建网关——
Anthropic 官方没有自己的 embedding API，这次不做 Anthropic embedding），选型机制同步改成跟 `LLM_PROVIDER` 一致的显式指定风格。

## 2. 选型机制

新增 `EMBEDDING_PROVIDER=ark|openai|tfidf`（不区分大小写），未设置/不识别一律降级为 `TfidfProvider`（本地兜底，不需要任何 key，天然可用）。
`ark`/`openai` 选中但对应 `API_KEY` 为空，同样降级为 `TfidfProvider`。

`ArkProvider` 现有的"选中后先探活（`embed(["ping"])`），失败也降级 Tfidf"逻辑保留（这是已有行为，本轮不改动，只是从"自动探测该不该用 Ark"变成"确认要用 Ark 之后的健康检查"）。
新增的 `OpenAIProvider`（embedding）不做探活，只检查 key 非空即用——跟 LLM Provider 那边的简单模式一致，不引入额外的一次网络往返。

```python
def get_embedding_provider() -> EmbeddingProvider:
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
        return OpenAIProvider()
    return TfidfProvider()
```

## 3. 新增 `OpenAIProvider`（embedding）

环境变量：`OPENAI_EMBEDDING_API_KEY` / `OPENAI_EMBEDDING_BASE_URL`（默认 `https://api.openai.com/v1`）/ `OPENAI_EMBEDDING_MODEL`（默认 `text-embedding-3-small`）——
故意跟 LLM 那边的 `OPENAI_API_KEY` 等变量名区分开（一个用于对话补全，一个用于 embedding，两者可能指向不同的中转/网关），风格上对齐现有 `ARK_EMBEDDING_*` 的命名习惯。

请求：`POST {base_url}/embeddings`，`Authorization: Bearer {api_key}`，`{"model": model, "input": texts}`——OpenAI 标准接口原生支持批量输入
（一次请求传入整个 `texts` 列表），不需要像 `ArkProvider` 那样逐条循环调用。响应 `data["data"]` 是一批 `{"embedding":[...], "index": N}`，
按 `index` 排序后取 `embedding` 列表，保证顺序跟输入一致（不能直接假设响应数组顺序已经对齐，虽然官方文档说通常如此，排序更保险）。
`texts` 为空列表时直接返回 `[]`，不发请求。`SUPPORTS_CACHE = True`（同一个 model 输出维度稳定）。

错误处理跟 `ArkProvider` 一致：请求异常/解析失败都 `raise EmbeddingProviderError`。

## 4. 改动文件清单

| 文件 | 改动类型 | 说明 |
|---|---|---|
| `memory_lib/providers/embedding.py` | 改 | 新增 `OpenAIProvider(EmbeddingProvider)` |
| `memory_lib/providers/__init__.py` | 改 | `get_embedding_provider()` 改为按 `EMBEDDING_PROVIDER` 显式选择 |
| `.env.example` | 改 | 补 `EMBEDDING_PROVIDER` + `OPENAI_EMBEDDING_*` 三变量 |
| `README.md` | 改 | 同步环境变量说明 |
| `.env`（本地，不进 git） | 改 | 补 `EMBEDDING_PROVIDER=ark`（保持现有 Ark 行为不变，不改真实密钥的值） |
| `tests/test_embedding_providers.py` | 新 | mock `requests.post`，覆盖选型逻辑 + `OpenAIProvider` 的请求构造/批量输入/排序/错误路径 |

## 5. 范围之外

- Anthropic embedding（官方无此 API，不做）。
- 重构 `ArkProvider` 现有的探活逻辑或逐条请求方式（本轮不动，只新增 `OpenAIProvider` 和改选型机制）。
