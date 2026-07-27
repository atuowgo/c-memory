---
标题: 给 Claude Code 装一套自动记忆系统：得物的设计实现
作者: 精神抖擞王大鹏（公众号：精神抖擞王大鹏）
发布时间: 2026年7月18日 00:08 北京
原文链接: https://mp.weixin.qq.com/s/-nl9V-x-KRz6ZvcikAv9mQ
代码仓库: https://github.com/ditingdapeng/agent-memory-system
抓取时间: 2026-07-27
---

## 总结

这篇文章复刻了得物技术团队《让 Claude Code 拥有自我进化和记忆系统》一文的设计思路，给出了具体可运行的实现（开源在 `agent-memory-system` 仓库）。

**要解决的问题**：Claude Code 在跨会话时会丢失项目约定（如包管理器用 pnpm）和用户的行为习惯（如"改文件前先 Read"、"不要自动提交"），这些细节很难靠手写 CLAUDE.md 穷举，尤其是团队里每个人的习惯还不一样。

**核心设计：三个 Hook 串成一个闭环**
1. **观察（PostToolUse Hook）**：每次工具调用后记录工具名、参数、结果到日志，做隐私过滤（正则去除 API Key）和 5 分钟内的去重。
2. **提炼（Stop Hook）**：会话结束时双路径并行提取：
   - 统计路径：硬编码序列检测器（如"70% 的 Edit 前都有 Read"→生成规则），无需依赖 LLM，部署即可用但需要数据积累；
   - LLM 路径：把观测摘要交给 Claude Haiku 做语义分析，同时另有脚本从日志里提取项目知识（检测到 pnpm 命令记"项目用 pnpm"）。
3. **注入（SessionStart Hook）**：新会话启动时用项目名 + 最近 git commit 构造查询，从记忆库向量召回最相关的 5 条注入到上下文；行为规则文件由 Claude Code 自动加载。

**置信度机制**：新发现的行为模式初始置信度 0.5，每次会话再次观测到 +0.05，未观测到 -0.05；达到 0.7（约 2-3 天）才写入规则文件，0.9 封顶，低于 0.55 自动废弃——用来区分"稳定习惯"和"偶发行为"。

**几个从设计图落到代码时才会遇到的实现细节**：
- Hook 的 JSON 字段名（如 `tool_response`）官方文档未列全，需要去 Claude Code 源码的 `coreSchemas.ts` 里确认；
- 每次 Hook 调用都是独立进程（fork），内存里的去重 dict 不会跨调用存活，必须把去重状态持久化到文件，否则 5 分钟内重复 Read 同一文件会写入多条重复记录；
- 架构图上"观测→记忆"这条箭头需要显式的写入者（`extract_memories.py`），只实现读端（`inject_memory.py`）会导致记忆库一直是空的。

**团队协作扩展**：把个人记忆库路径换成仓库内文件（`.claude/team-memory.json`、`.claude/rules/team-rules.md`），frontmatter 加 `scope: team/personal` 字段分流，无需改动架构。

**与得物原文的差异**：得物用 nomic-embed-text 做 768 维向量，本实现用 TF-IDF 减少依赖；得物按月归档历史，本实现只做超限截断；得物有 5 个统计检测器，本实现实现了 3 个。

未配置 `ANTHROPIC_API_KEY` 时走纯规则 fallback（关键词匹配 + 统计检测），配置后走 LLM 路径，两种模式都能跑通完整闭环。

## 原文

给 Claude Code 装一套自动记忆系统：得物的设计实现

原创 精神抖擞王大鹏 精神抖擞王大鹏
2026年7月18日 00:08 北京

当你用 Claude Code 写了一整天代码。第二天早上打开新会话，让它加个新接口，它用了 npm install express，昨天明明全程用的 pnpm，项目目录还有个 pnpm-lock.yaml。你让它改个文件，它直接 Edit，把别人刚提交的内容覆盖了，因为它没先 Read 一遍最新版本。昨天反复说的"改完不要自动提交"，今天又忘了。

当然，你可以在 CLAUDE.md 里写一句"本项目用 pnpm"，Agent 下次就记住了。但你不会在里面事无巨细的写"每次改文件前先读一遍当前内容"，因为这是你的工作习惯，不是项目配置。有时你自己都意识不到它是一条"规则"，团队 N 个人习惯各不相同，不可能让每个人手动维护一份行为规则库。

得物技术团队在《让 Claude Code 拥有自我进化和记忆系统》中给了一套完整设计，文章只讲了原理。这篇对着原理复刻下实现。

代码仓库：github.com/ditingdapeng/agent-memory-system

它能做什么

装上之后不需要任何额外操作。你正常用 Claude Code 写代码，系统在后台默默工作：

第 1 天：你写代码，系统记录每一次工具调用——读了什么文件、执行了什么命令、编辑了哪些代码。会话结束时，自动从中提取两类信息：项目知识（"用 pnpm"、"测试框架是 vitest"）和行为模式（"这个人总是先 Read 再 Edit"）。

第 3 天：行为模式被反复验证 4 次后，置信度达到阈值，系统自动生成一份规则文件。Claude Code 每次启动都会加载它。从此 Agent 会自觉在编辑前先读取文件内容——没人告诉它要这么做，它从你的行为里学到的。

每次新会话启动：系统自动把相关项目记忆注入到 Agent 上下文。第一句话它就知道项目用 pnpm、测试用 vitest，不需要你再解释。

设计：三个Hook串起一个闭环

整套系统建立在 Claude Code 的 Hook 机制，工具调用后、会话结束时、新会话启动时，各运行一段自定义脚本。

数据流分三个阶段：

观察——每次工具调用后，Hook 脚本把工具名、输入参数、执行结果记录到一份日志文件。做了隐私过滤（正则去掉 API Key）和去重（5 分钟内相同内容只记一次）。

提炼——会话结束时，两条路径并行从日志中提取模式：

统计路径用硬编码的序列检测器（"70% 的 Edit 前都有 Read" → 生成规则），LLM 路径把观测摘要发给 Claude Haiku 做语义分析。

两个的区别是，统计路径需要数据积累，LLM 路径刚部署就可以工作。

同时，另一个脚本从工具调用日志中提取项目知识——检测到 pnpm 命令就记一条"项目用 pnpm"，有 API Key 时调 LLM 做更细腻的语义提取。

注入——新会话启动时，用当前项目名 + 最近 git commit 构造查询，从记忆库中向量召回最相关的 5 条，格式化后通过 stdout 注入到 Agent 上下文。同时 Claude Code 自动加载规则文件。

闭环完成时，Agent 带着记忆开始新对话，又产生新的工具调用，又被观察、提炼……循环往复，记忆会越来越准。

置信度来保证什么时候可用

行为规则不会立即生效。首次发现时置信度是 0.5——系统不确定这是习惯还是巧合。每次会话如果再次观测到同一模式，+0.05；没观测到，-0.05。

达到 0.7 才写入规则文件（约 2-3 天），0.9 封顶。长期不触发会衰减，低于 0.55 自动废弃。稳定的习惯越来越强，偶发的行为自然淘汰。

实现细节

得物的文章给了清晰的架构设计，但从设计图到可运行代码之间有一些实现细节。

Hook 的协议确认。Claude Code 的 PostToolUse Hook 通过 stdin 传 JSON，但官方文档没列出完整 schema。字段名叫 tool_response，确认方式是去 Claude Code 源码里找 coreSchemas.ts，那里定义了 Hook 传入的完整字段列表。

Hook 的进程模型。Claude Code 每次工具调用都 fork 一个独立进程跑你的脚本。这意味着模块级变量都是单次调用，如果你在内存里维护的去重 dict，进程结束就消亡了。下次 Hook 触发是一个全新进程和dict。5 分钟内对同一文件连续 Read 三次，会写入三条重复记录。如果理解了"每次调用都是独立进程"这个事实，解法就自然变成了把状态持久化到文件。

数据流闭合。架构图的箭头连着的背后，需要一个实际的执行者。"记忆 → 注入"这条箭头有 inject_memory.py 负责读取和注入，但"观测 → 记忆"这条箭头——谁负责往 memories.json 里写？如果你只按图实现了读端而没有写端，注入脚本每次启动都读到空文件。在 Stop Hook 里补了 extract_memories.py 作为写入者，数据流才真正闭合。

团队记忆：从个人到共享

单人版的记忆存在本地。稍作扩展就能支持团队：

把记忆库提交到仓库（.claude/team-memory.json），团队成员互相 pull 彼此的发现
团队规则文件放仓库 .claude/rules/team-rules.md，所有人的 Claude Code 自动加载
Instinct frontmatter 加 scope: team/personal 字段，按 scope 分流输出

不需要改架构，只改输出路径和数据源。

快速开始

git clone https://github.com/ditingdapeng/agent-memory-system.git
cd agent-memory-system
pip install -r requirements.txt  # 只有 anthropic（可选）

# 把 Hook 配置复制到你的项目
cp .claude/settings.json /path/to/your-project/.claude/settings.json
# 修改里面的脚本路径为绝对路径

# 正常使用 Claude Code，系统自动工作

配了 ANTHROPIC_API_KEY 走 LLM 路径（语义提取 + 模式分析），没配走纯规则 fallback（关键词匹配 + 统计检测）。两种模式都能跑通完整闭环。

和得物原文的差异

得物用 nomic-embed-text 做 768 维向量，github的demo版本用了 TF-IDF 避免依赖。
得物按月归档历史，代码实现只做了超限截断；
得物用了 5 个统计检测器，代码版本实现了 3 个
