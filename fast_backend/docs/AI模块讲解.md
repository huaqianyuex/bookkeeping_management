# AI 模块系统讲解（基于 fast_backend 真实代码）

> 阅读基准：工作区 `E:\一些毕设探索\记账管理系统_fastapi\fast_backend`，代码版本以本次通读为准。
> 行号引用均来自当前磁盘文件，可直接跳转核对。

---

## 0. 一句话结论

AI 模块不是「本地模型工程」，而是**基于 LangChain 的 API 编排层**：用 `langchain-openai` 的 `ChatOpenAI` / `OpenAIEmbeddings` 打到一个 OpenAI 兼容网关（agnes-ai），把大模型能力包装成 4 条业务链（对话 / 分析 / 预算 / 自然语言记账）+ 1 条检索链（FAQ），再通过 `routers/ai.py` 的 17 个端点对外暴露。

因此本模块**没有模型权重加载、没有训练、没有 GPU 依赖**；「模型加载」对应客户端懒加载单例，「预处理」对应上下文与提示词组装，「推理」对应四种调用形态，「后处理」对应规则级归一化与落库审计。

---

## 1. 模块定位与整体架构

### 1.1 定位

AI 模块在系统里承担三类职责，全部围绕「记账」这个核心业务：

| 职责 | 用户可感知的功能 | 对应链路 |
|---|---|---|
| 对话助手 | 「小记」聊天问答，SSE 流式回复 | `ai/chat_chain.py` |
| 财务洞察 | 消费分析、预算规划（结构化 JSON） | `ai/analyze_chain.py` |
| 记账入口 | 说一句「昨天打车 18 块」直接入账 | `ai/bookkeeping_chain.py` |
| 知识检索 | FAQ 语义搜索 | `ai/faq_retriever.py` |

### 1.2 六层架构

```
客户端        前端 AiChat.jsx / uni-app  ── SSE 流 + 裸 JSON
   │
路由层        routers/ai.py（17 端点，裸返回 + ai_error）
   │
编排层        chat_chain │ analyze_chain │ bookkeeping_chain │ faq_retriever
   │
支撑层        memory.py │ context.py │ normalizers.py │ category_alias.py
   │
模型层        ai/llm.py（ChatOpenAI / OpenAIEmbeddings → agnes-ai API）
   │
数据层        crud/ai.py → models/chat.py + models/bookkeeping.py → MySQL
```

**关键设计约束（写在 `routers/ai.py:1-21` 模块头注释里，是全模块最重要的一条铁律）：**

`/api/ai/**` **一律裸返回，不套 `{code,message,data}` 信封**。原因是前端 `src/api/request.js` 的响应拦截器是 `return response.data`，`pages/AiChat.jsx` 直接按裸结构消费（`res.items` / `data.id` / `msgs || []`）。一旦包信封，会话列表直接空白。

配套的三条子规则：
1. 业务失败统一 `return ai_error("中文")`（HTTP 200），**禁止抛 `HTTPException`**——会被全局异常处理器包成 Result 信封；
2. 会话/消息时间戳是 **int 毫秒**，不是 ISO 字符串；
3. SSE 事件行固定 `data: {"type":"content"|"done"|"error",...}\n\n`。

---

## 2. 目录与文件结构、核心类与函数

### 2.1 `ai/` 目录（9 个模块）

| 文件 | 行数 | 核心符号 | 职责 |
|---|---|---|---|
| `ai/llm.py` | 32 | `get_chat_llm` / `get_analyze_llm` / `get_embeddings` | LLM 客户端工厂（模型层） |
| `ai/chat_chain.py` | 25 | `SYSTEM_PROMPT` / `chat` / `chat_stream` | 对话链 |
| `ai/analyze_chain.py` | 79 | `ANALYZE_SYSTEM` / `BUDGET_SYSTEM` / `analyze_expense` / `plan_budget` | 分析 + 预算 |
| `ai/bookkeeping_chain.py` | 62 | `ParsedItem` / `Parsed` / `_PROMPT` / `parse_bookkeeping` | 记账抽取 |
| `ai/faq_retriever.py` | 101 | `_index` / `_cosine` / `_keyword_score` / `rebuild` / `search_faq` | FAQ 检索 |
| `ai/memory.py` | 25 | `MAX_TOKENS` / `KEEP_RECENT` / `build_history` | 历史窗口裁剪 |
| `ai/context.py` | 44 | `build_user_context` | 财务上下文组装 |
| `ai/normalizers.py` | 124 | `normalize_amount` / `normalize_date` / `_cn_to_int` | 规则级清洗 |
| `ai/category_alias.py` | 58 | `ALIAS` / `resolve_category` | 分类映射 |

### 2.2 关联模块

| 文件 | 说明 |
|---|---|
| `routers/ai.py` | 17 个端点，860 行，全模块业务编排中枢 |
| `crud/ai.py` | AI 表数据访问 + 记账日志 + 幂等查询 |
| `schemas/ai.py` | 出入参 Pydantic 模型（含 4 种记账 action 出参） |
| `models/chat.py` | `ChatSession` / `ChatMessage` / `Feedback` / `Faq` |
| `models/bookkeeping.py` | `AiBookkeepingLog` |
| `config/settings.py:32-45` | AI 相关配置项 |
| `tasks/purge.py` | 软删会话物理清理（**当前为空桩**） |

### 2.3 数据模型要点（`models/chat.py:1-10`）

四张 AI 表刻意**不使用** `IdMixin` / `TimestampMixin`，全部显式声明列：

- 表名是**单数**（`sessions` / `messages` / `feedback` / `faq`），沿用旧 Express 项目口径；
- 主键是**业务字符串 ID**：`session_{毫秒}_{随机9位}`、`msg_...`、`feedback_...`，由 `crud/ai.py:27` 的 `new_id(prefix)` 生成；
- 时间列是 **BIGINT 毫秒**，由 `crud/ai.py:33` 的 `now_ms()` 产出，**不是 DATETIME**；
- `deleted_at = 0` 表示未删，`> 0` 存删除毫秒（软删）。

`models/bookkeeping.py:37` 的 `AiBookkeepingLog` 反过来用了 mixin，一张表承担三件事：幂等去重、追问草稿、审计纠错样本。

---

## 3. 数据流、调用链路与关键接口

### 3.1 接口全清单（`routers/ai.py`）

| # | 方法 | 路径 | 行号 | 说明 |
|---|---|---|---|---|
| 1 | POST | `/api/ai/sessions` | 66 | 创建会话 |
| 2 | GET | `/api/ai/sessions` | 77 | 会话列表（裸 `{items,total}`） |
| 3 | POST | `/api/ai/sessions/batch-delete` | 105 | 批量软删，≤50 条 |
| 4 | PATCH | `/api/ai/sessions/{id}` | 119 | 重命名 |
| 5 | DELETE | `/api/ai/sessions/{id}` | 131 | 单个软删 |
| 6 | GET | `/api/ai/sessions/{id}/messages` | 143 | 消息列表（裸数组） |
| 7 | POST | `/api/ai/chat` | 164 | 非流式对话 |
| 8 | POST | `/api/ai/chat/stream` | 197 | 流式对话（SSE） |
| 9 | POST | `/api/ai/analyze/expenses` | 252 | 消费分析 |
| 10 | POST | `/api/ai/analyze/budget` | 270 | 预算规划 |
| 11 | GET | `/api/ai/faq/search` | 289 | FAQ 检索 |
| 12 | POST | `/api/ai/faq/rebuild` | 313 | 重建向量索引 |
| 13 | POST | `/api/ai/feedback` | 329 | 保存反馈 |
| 14 | GET | `/api/ai/admin/stats` | 347 | AI 使用统计 |
| 15 | POST | `/api/ai/bookkeeping` | 384 | 自然语言记账 |
| 16 | PATCH | `/api/ai/bookkeeping/{record_id}` | 605 | 修改 AI 记账 |
| 17 | DELETE | `/api/ai/bookkeeping/{record_id}` | 798 | 删除 AI 记账 |

**路由注册顺序陷阱**（`routers/ai.py:19-20`）：`/sessions/batch-delete` 必须注册在 `/sessions/{session_id}` 之前，因为 Starlette 按注册顺序匹配，否则 `"batch-delete"` 会被当成 `session_id` 吃掉。当前代码第 105 行确实排在第 119 行之前，是对的。

### 3.2 对话链路

```
POST /api/ai/chat 或 /chat/stream
  → get_current_user（utils/auth.py，JWT）
  → ai_crud.get_user_session(db, session_id, user_id)   归属校验，失败返 ai_error
  → memory.build_history(db, session_id)                历史窗口
  → [SystemMessage(SYSTEM_PROMPT), *history, HumanMessage(message)]
  → chat_chain.chat() / chat_stream()
  → 落库 + 返回
```

`ai/chat_chain.py:14` 的 system prompt：

```python
SYSTEM_PROMPT = "你是个人记账管理系统「小记」的 AI 助手，帮助用户记账、分析消费、解答财务问题。回答用中文，简洁口语化。"
```

注意**当前对话链路没有注入用户财务数据**——`build_user_context` 只在分析/预算端点里用。`docs/API文档_FastAPI.md:1073` 描述的「回复内容基于当前用户当月统计、Top10 账单自动组装上下文」在 `chat` / `chat_stream` 里并未实现，这是一处文档与代码的偏差。

流式端点 `routers/ai.py:197` 的时序有三处设计细节：

```python
# 1) 归属校验在生成器外完成，否则错误只能以 SSE error 事件发出（见 211 行注释）
session = await ai_crud.get_user_session(db, body.session_id, user_id)
if session is None:
    return ai_error("会话不存在")

def sse(d: dict) -> str:
    return f"data: {json.dumps(d, ensure_ascii=False)}\n\n"

async def event_gen():
    # 2) 先落库用户消息，失败直接发 error 事件
    # 3) 边 yield content 边把 chunk 拼进 full，全部产出后一次性落库助手消息，再发 done
    yield sse({"type": "done", "messageId": ai_msg.id if ai_msg else None})
```

`done` 事件回传 `messageId` 是为了让前端拿它去调 `/api/ai/feedback`（`FeedbackIn.message_id`）。

### 3.3 分析 / 预算链路

```
POST /api/ai/analyze/expenses
  → ai_context.build_user_context(db, user_id)   查库组包（前端不传金额）
  → analyze_chain.analyze_expense(ctx)
  → {"success": True, "data": ExpenseAnalysis.model_dump()}   注意 data 内是 snake_case
```

`schemas/ai.py:9-11` 特别强调：分析与预算的 `data` **内部字段是 snake_case**（`total_expense` / `savings_rate` / `monthly_budget`），与业务模块「对外 camelCase」的约定相反，前端 `AiChat.jsx` 按此读取，不能改成驼峰。

### 3.4 FAQ 链路（双路降级）

`ai/faq_retriever.py` 是本模块唯一涉及向量检索的地方：

- `faq` 表**不存向量**，`_index`（第 16 行）是模块级内存索引，全量构建；
- 被 embedding 的文本是每条 FAQ 的 `question` 字段；
- `rebuild()`（第 37 行）用 `aembed_documents(texts)` 批量异步算向量；失败抛异常 → 路由返回 `{"error","detail"}`；
- `search_faq()`（第 63 行）用 `aembed_query(query)` 算查询向量，任何异常都吞掉降级为 `_keyword_score` 字符重合度；
- 两种模式的 score 都归一到 0~1 降序取 top_k。

`routers/ai.py:289` 区分了两种失败形态：**无命中返回 `{"results": []}`（没有 fallback 键）**，**异常才返回 `{"results": [], "fallback": true}`**。

### 3.5 自然语言记账链路（本模块最复杂的一条，9 步）

代码在 `routers/ai.py:384-602`，逐步骤拆解：

| 步 | 行号 | 动作 |
|---|---|---|
| 1 | 396-406 | 参数校验（message 非空、≤500 字）+ 会话归属 |
| 2 | 411-412 | 归一化文本并算 `dedup_hash = SHA256(f"{user_id}|{normalized}")` |
| 3 | 414-420 | 幂等检查：`client_msg_id` 强幂等 → `find_recent_by_dedup(300s)` 弱幂等；命中且 `record_ids` 非空 → `_duplicate_response` |
| 4 | 424-446 | 先 INSERT 日志占位并 commit，靠 `uk_abk_client_msg` 唯一键兜底并发；`IntegrityError` 回查走 duplicate |
| 5 | 448-466 | 查分类（用户自定义 + 系统预设）→ `parse_bookkeeping()` LLM 抽取 |
| 6 | 468-483 | 意图过滤：`query` / `chitchat` 或全部非消费相关 → `ignored` |
| 7 | 485-499 | 条目数 ≤10；逐条 `normalize_amount` / `normalize_date` / `resolve_category` |
| 8 | 501-547 | 三分支：`dry_run` → preview；`ok_items` 为空 → `clarify`（status=0 草稿）；否则入账 |
| 9 | 549-602 | 同一事务逐条 INSERT records + 回写日志 + 落会话消息 + `echo` |

`echo` 的生成（第 566 行）是很有代表性的「后处理」——把结构化结果拼成口语化回执：

```python
echo = "已记下：" + "；".join(
    f"{(cat.name if cat else '其他')} ¥{amount:.2f} · {rec_date.isoformat()}"
    + (f" · 备注「{item.remark}」" if item.remark else "")
    + f" · 记录 #{rid}"
    for (item, amount, rec_date, cat), rid in zip(ok_items, record_ids)
) + "\n回复「改成45块」可修改，回复「删掉」可撤销。"
```

---

## 4. 核心流程：模型加载 → 预处理 → 推理 → 后处理

这一节把通用 LLM 工程范式映射到项目真实代码。

### 4.1 「模型加载」= 客户端工厂

`ai/llm.py` 全部内容就是三件事：

```python
_chat_llm: ChatOpenAI | None = None   # 进程内单例，避免每次请求重建客户端

def get_chat_llm() -> ChatOpenAI:
    global _chat_llm
    if _chat_llm is None:
        _chat_llm = ChatOpenAI(
            model=CHAT_MODEL,
            api_key=AGNES_API_KEY,
            base_url=OPENAI_BASE_URL,
            temperature=0.7,
            streaming=True,          # /chat/stream 需要
        )
    return _chat_llm
```

三个客户端的设计意图各不相同：

| 函数 | 模型 | temperature | 特殊点 |
|---|---|---|---|
| `get_chat_llm`（:11） | `CHAT_MODEL` = agnes-2.5-flash | **0.7** | 全局单例；`streaming=True` |
| `get_analyze_llm`（:24） | `ANALYZE_MODEL` = agnes-2.0-flash | **0** | 每次新建；配合 `with_structured_output` 保证稳定 |
| `get_embeddings`（:29） | `EMBEDDING_MODEL` = text-embedding-3-small | — | 函数内延迟 `import OpenAIEmbeddings` |

温度分层的逻辑很清晰：**聊天要自然（0.7），抽取要确定（0）**。`get_embeddings` 把 import 写在函数体里是刻意的——避免 FAQ 功能未启用时也付加载成本。

### 4.2 「预处理」= 三层组装

**第一层：上下文与历史裁剪**

`ai/memory.py:10` 的 `build_history` 从尾部往前累计，超预算即停：

```python
MAX_TOKENS = 2000  # 近似：中文 1 字 ≈ 1 token，毕设够用
KEEP_RECENT = 6    # 最近 N 条

for m in reversed(msgs):
    used += len(m.content)
    if used > MAX_TOKENS or len(picked) >= KEEP_RECENT:
        break
    cls = HumanMessage if m.role == "user" else AIMessage
    picked.append(cls(content=m.content))
picked.reverse()  # 恢复升序
```

`ai/context.py:11` 的 `build_user_context` 是财务数据的组包口径：

```python
today = date.today()
this_start = today.replace(day=1)
last_end = this_start - timedelta(days=1)   # 上月最后一天
last_start = last_end.replace(day=1)

this_income, this_expense = await get_summary(db, user_id, today.year, today.month)
_, last_expense = await get_summary(db, user_id, last_start.year, last_start.month)   # 环比
cat_rows = await get_category_stats(db, user_id, today.year, today.month, stat_type=0)  # Top5
```

返回裸 dict：`{this_month, total_income, total_expense, last_month_expense, top_categories}`。`Decimal → float` 只为 JSON 序列化展示。

**第二层：提示词模板**

全模块共 5 个提示词常量，都采用「角色 + 输出契约 + 约束」的三段式：

- `ai/chat_chain.py:14` `SYSTEM_PROMPT` — 闲聊型，只约束语言风格；
- `ai/analyze_chain.py:9` `ANALYZE_SYSTEM` — 强约束型，「insights 正好 3 条」「risk_level 必须从低/一般/高三选一」「只输出 JSON，不要多余文字」；
- `ai/analyze_chain.py:17` `BUDGET_SYSTEM` — 限定 `category_limits` 最多 6 个分类；
- `ai/bookkeeping_chain.py:38` `_PROMPT` — 带 `{today}` / `{message}` / `{categories}` 三个占位符的模板，把「系统已有分类」注入进去让 LLM 优先复用现有叫法；
- `ai/faq_retriever.py` 无提示词（纯向量检索）。

`_PROMPT` 里的日期推算规则是全文最关键的一句：

```
2. 相对日期（今天/昨天/前天/大前天/N天前/本周三/上周三/M月D号）按今天推算为 yyyy-MM-dd，
   无日期词 date 与 date_expr 均为 null；
```

**第三层：结构化约束**

`ai/bookkeeping_chain.py:19-35` 用 Pydantic 的 `Field(description=...)` 把字段说明直接当成 schema 提示词下发：

```python
class ParsedItem(BaseModel):
    amount: float | None = Field(None, description="金额；原文无法确定则为 null，绝不猜测")
    amount_raw: str | None = Field(None, description="原文中的金额片段，如「79块」")
    type: int = Field(1, description="0=支出 1=收入（records 口径）")
    category_name: str | None = Field(None, description="分类名（优先用系统已有分类的叫法）")
    date_expr: str | None = Field(None, description="原文日期词，如「昨天」「上周三」；无则 null")
    date: str | None = Field(None, description="按今天推算的 yyyy-MM-dd；推不出则 null")
    remark: str | None = Field(None, description="备注（消费内容摘要）")
    confidence: float = Field(0.0, description="抽取置信度 0~1")
    is_expense_related: bool = Field(True, description="是否消费相关")
```

注意 `amount` 的 description 写着「绝不猜测」——这是贯穿全模块的**反幻觉口径**：宁可 `None` 触发追问，也不编造金额。

### 4.3 「推理」= 四种调用形态

| 形态 | 方法 | 调用点 |
|---|---|---|
| 流式 | `astream()` | `chat_chain.chat_stream`（:23） |
| 非流式 | `ainvoke()` | `chat_chain.chat`（:19） |
| 结构化 | `with_structured_output()` + `ainvoke()` | `parse_bookkeeping` / `analyze_expense` / `plan_budget` |
| 向量化 | `aembed_documents()` / `aembed_query()` | `faq_retriever.rebuild` / `search_faq` |

全部走 async，且**没有一个同步调用阻塞事件循环**。

结构化输出最巧的一处是 `ai/analyze_chain.py:32` 的内嵌子模型——让 LLM 只负责它擅长的文本字段，数值字段由系统算：

```python
class _LLMPart(BaseModel):
    summary: str = Field(description="一句话总结")
    insights: list[str] = Field(description="洞察，正好3条")
    suggestions: list[str] = Field(description="建议，正好3条")
    risk_level: str = Field(description="低/一般/高 三选一")

llm = get_analyze_llm().with_structured_output(_LLMPart)
...
part: _LLMPart = await llm.ainvoke([SystemMessage(content=ANALYZE_SYSTEM), HumanMessage(content=prompt)])

income = float(ctx["total_income"]); expense = float(ctx["total_expense"])
rate = round((income - expense) / income * 100, 1) if income > 0 else 0.0

return ExpenseAnalysis(
    summary=part.summary, total_expense=expense, top_categories=ctx["top_categories"],
    insights=part.insights, suggestions=part.suggestions,
    savings_rate=rate, risk_level=part.risk_level,
)
```

预算链路同理（`ai/analyze_chain.py:77`）：`plan.savings_target = target`，储蓄目标以系统计算为准，不信任 LLM 的算术。

不传 `savings_goal` 时按 50/30/20 法则推导（第 66 行）：`target = round(monthly_income * 0.2, 2)`。

### 4.4 「后处理」= 规则兜底 + 服务端计算 + 落库审计

后处理是三层：

**（1）金额归一化** `ai/normalizers.py:46`

```python
def normalize_amount(amount_raw: str | None, parsed: float | None) -> float | None:
    if parsed is not None:                 # 1) LLM 已给数：只做范围校验
        return _clip(float(parsed))
    if amount_raw:                         # 2) 从原文再抓一次
        m = _RE_WAN.search(amount_raw)     # 1万2 → 12000
        ...
        m = _RE_ARABIC.search(amount_raw)  # 79 / 79.5 / 1,200
        ...
        m = _RE_CN.search(amount_raw)      # 七十九块
        ...
    return None                            # 3) 仍失败 → None，上层触发追问
```

三个正则按「万 → 阿拉伯 → 中文」优先级匹配，`_clip` 做 `(0, 99999999.99]` 范围校验。中文数字只支持到十位（`_cn_to_int` 注释明确写「不支持百以上（交给 LLM）」）。

**（2）日期归一化** `ai/normalizers.py:74`

支持 6 类相对词：`今天/昨天/前天/大前天`、`N天前`、`本周X`、`上周X`、`M月D号`。两处年份回退逻辑很关键：

```python
d = date.fromisoformat(parsed_iso)
if d > today:                       # 未来日期且未显式带未来语义 → 年份-1
    return d.replace(year=d.year - 1)
```

即用户说「3月5号」而今天是 9 月，会正确落到今年 3 月而非报错。解析全失败一律回落 `today`。

**（3）分类映射** `ai/category_alias.py:22`

四级优先级，注释写得很清楚：

```python
# 1) 精确匹配（用户自定义优先——列表顺序由调用方保证：自定义在前）
# 2) 别名词典 → 再精确匹配一次
canonical = ALIAS.get(target)     # 「打车」→「交通」
# 3) 模糊包含（cat.name in target or target in cat.name）
# 4) 兜底：由调用方归入「其他」
```

返回 `(category | None, fallback)` 二元组，调用方 `routers/ai.py:495-498` 在 `fallback=True` 时归入「其他」并追加 warning。`ALIAS` 词典内置 30+ 条口语映射（吃饭→餐饮、下馆子→餐饮、滴滴→交通、房租→居住……）。

**（4）服务端计算与落库审计**

`savings_rate`、`total_expense`、`savings_target` 全部由系统算；`_LLMPart` 的拆分就是这条原则的代码化。落库侧 `ai_bookkeeping_logs` 通过 `parent_id` 自关联记录「AI 记账 → 用户修改 → 撤销」的完整链路（`routers/ai.py:738-767` 与 `826-853`）。

---

## 5. 配置项、依赖库、环境变量与外部服务

### 5.1 配置项（`config/settings.py:32-52`）

```python
# ---- AI ----
AGNES_API_KEY = os.getenv("AGNES_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://apihub.agnes-ai.com/v1")
CHAT_MODEL = os.getenv("CHAT_MODEL", "agnes-2.5-flash")
ANALYZE_MODEL = os.getenv("ANALYZE_MODEL", "agnes-2.0-flash")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")

# ---- 对话记忆 ----
MAX_HISTORY_TOKENS = int(os.getenv("MAX_HISTORY_TOKENS", "2000"))
KEEP_RECENT_MESSAGES = int(os.getenv("KEEP_RECENT_MESSAGES", "6"))

# ---- FAQ 检索 ----
FAQ_TOP_K = int(os.getenv("FAQ_TOP_K", "3"))
FAQ_SIMILARITY_THRESHOLD = float(os.getenv("FAQ_SIMILARITY_THRESHOLD", "0.5"))

# ---- 清理任务 ----
PURGE_INTERVAL_HOURS = int(os.getenv("PURGE_INTERVAL_HOURS", "6"))
PURGE_DELAY_DAYS = int(os.getenv("PURGE_DELAY_DAYS", "7"))
```

**⚠️ 配置读取存在 4 处失效**（详见第 8 节）：`MAX_HISTORY_TOKENS`、`KEEP_RECENT_MESSAGES`、`PURGE_INTERVAL_HOURS`、`PURGE_DELAY_DAYS` 这四个配置项**没有任何代码读取**，全是死配置。

### 5.2 环境变量（`.env` 实测值，密钥已脱敏）

```
DATABASE_URL=mysql+aiomysql://root:***@localhost:3306/bookkeeping_fastapi?charset=utf8mb4
CORS_ORIGINS=http://localhost:5174
JWT_SECRET=this-i****
AGNES_API_KEY=sk-V7F****
OPENAI_BASE_URL=https://api.agnes-ai.cn/v1
CHAT_MODEL=agnes-2.5-flash
ANALYZE_MODEL=agnes-2.0-flash
EMBEDDING_MODEL=text-embedding-3-small
DEBUG_MODE=true
```

**两处默认值不一致，值得注意：**
- `.env` 的 `OPENAI_BASE_URL` 是 `https://api.agnes-ai.cn/v1`，而 `settings.py:34` 的默认值是 `https://apihub.agnes-ai.com/v1`（域名不同）；
- `.env` 的 `CORS_ORIGINS` 是 `http://localhost:5174`，`settings.py:19` 的默认值是 `http://localhost:5173`。

删掉 `.env` 或换机器部署时会静默切到另一套地址。

### 5.3 依赖库

`requirements.txt` 第 22-24 行的状态是个坑：

```
# 以下为 AI / 定时任务的可选依赖，实现对应模块时再安装：
# langchain-openai
# apscheduler
```

**AI 依赖仍是注释状态**。但 `ai/llm.py:3` 是顶层导入：

```python
from langchain_openai import ChatOpenAI
```

而 `main.py:14` 导入 `routers.ai`，`routers/ai.py:34` 导入 `from ai import memory, chat_chain, ...`。所以**只按 `requirements.txt` 装依赖，`main.py` 会直接 ImportError**。

实测当前环境（`D:\anaconda\python.exe`）已装好 `fastapi / sqlalchemy / langchain_openai`，属于「环境比清单新」的状态。

实际依赖链：`langchain-openai` → `langchain-core` → `openai` → `httpx`。

### 5.4 外部服务

单一外部依赖：**agnes-ai OpenAI 兼容网关**（`https://api.agnes-ai.cn/v1`），承载三类模型：

| 用途 | 模型 | 调用方式 |
|---|---|---|
| 对话 | agnes-2.5-flash | `/chat/completions`（stream=true） |
| 抽取 / 分析 | agnes-2.0-flash | `/chat/completions`（response_format json_schema） |
| 向量化 | text-embedding-3-small | `/embeddings` |

由于是 OpenAI 兼容协议，**换供应商只需改 `OPENAI_BASE_URL` + `AGNES_API_KEY`**，代码零改动——这是选 LangChain 的最大收益。

---

## 6. 关键代码片段解读

### 6.1 裸返回契约的实现（`routers/ai.py:60`）

```python
def ai_error(msg: str) -> dict:
    """AI 业务失败统一返回：HTTP 200 + 裸 {"error": "中文"}"""
    return {"error": msg}
```

全模块所有失败分支都 `return ai_error(...)`，不抛异常。唯一的 `HTTPException(400, ...)` 出现在 `chat`（:171）和 `chat_stream`（:209）的「sessionId 和 message 不能为空」场景，这是模块内**唯一**允许的 400。

### 6.2 幂等设计（`routers/ai.py:410-446`）

```python
normalized = " ".join(message.split())
dedup_hash = hashlib.sha256(f"{user_id}|{normalized}".encode()).hexdigest()
hit = None
if body.client_msg_id:
    hit = await ai_crud.find_log_by_client_msg(db, user_id, body.client_msg_id)   # 强幂等，不过期
if hit is None and not body.force:
    hit = await ai_crud.find_recent_by_dedup(db, user_id, dedup_hash, 300)        # 弱幂等，300 秒

if hit is not None and hit.record_ids:
    return await _duplicate_response(db, hit)

# 先 INSERT 占位，撞唯一键才算真并发
try:
    log = await ai_crud.create_bookkeeping_log(...)
    await db.commit()           # 占位必须先落库，撞键才有意义
except IntegrityError:
    first = await ai_crud.find_log_by_client_msg(db, user_id, body.client_msg_id)
    if first and first.record_ids:
        return await _duplicate_response(db, first)
    return ai_error("请求处理中，请稍后重试")
```

这是标准的「**先写后查**」幂等模式，而非「先查后写」。`crud/ai.py:327` 的注释特意强调：

> 幂等靠 `uk_abk_client_msg` 唯一键冲突兜底——捕获 `IntegrityError` 后回查首次记录返回 duplicate，**禁止先 SELECT 再 INSERT**。

`client_msg_id` 允许为 NULL（`models/bookkeeping.py:69`），因为 MySQL 唯一索引对多行 NULL 不冲突，正好实现「不传幂等键就不启用强幂等」。

### 6.3 余弦相似度归一化（`ai/faq_retriever.py:19-26`）

```python
def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(y * y for y in b) ** 0.5
    if na == 0 or nb == 0:
        return 0.0
    # 余弦值域 [-1,1]，归一到 [0,1] 方便前端展示
    return max(0.0, min(1.0, (dot / (na * nb) + 1) / 2))
```

**这里有一个阈值语义 bug**：归一化后原始余弦 0.0 会变成 0.5，而 `FAQ_SIMILARITY_THRESHOLD` 默认也是 `0.5`（`config/settings.py:45`），并且在第 81 行直接拿归一化值比较：

```python
score = _cosine(q_vec, item["vector"])
if score < FAQ_SIMILARITY_THRESHOLD:
    continue
```

等价于「原始余弦 ≥ 0.0 就通过」，阈值形同虚设。要么比较原始余弦值，要么把阈值提到 0.7~0.8。

### 6.4 修改链路的「显式字段优先」合并（`routers/ai.py:627-677`）

```python
new_amount = body.amount          # ── 1) 显式字段优先收集
new_category_id = body.category_id
new_date = None
...
if body.message:                  # ── 2) message 解析链取增量字段（显式字段优先覆盖）
    parsed = await parse_bookkeeping(msg, _date.today().isoformat(), [c.name for c in cat_rows])
    item = next((i for i in parsed.items
                 if i.is_expense_related and (i.amount_raw or i.amount is not None)), None)
    if item is not None:
        if new_amount is None:                      # 关键：只在显式字段为空时才用解析值
            amt = bk_norm.normalize_amount(item.amount_raw, item.amount)
            ...
```

四个字段都遵循同一个模式：`if new_xxx is None: 用解析值`。最终只把**实际变化**的字段写进 `changes`（第 683-723 行），全部无变化时返回 `echo: "记录没有需要修改的内容"` 而不是报错。

分类变更还额外做了类型一致性校验（第 701 行）：`if cat.type != rec.type: return ai_error("分类类型与原记录收支类型不一致")`——防止把支出记录改到收入分类上。

### 6.5 分页查询避免 N+1（`crud/ai.py:91-132`）

```python
msg_agg = (
    select(ChatMessage.session_id,
           func.count().label("message_count"),
           func.max(ChatMessage.timestamp).label("last_ts"))
    .group_by(ChatMessage.session_id).subquery()
)
last_msg = (select(ChatMessage.content)
            .where(ChatMessage.session_id == ChatSession.id)
            .order_by(ChatMessage.timestamp.desc()).limit(1)
            .correlate(ChatSession).scalar_subquery())
```

用一次 `outerjoin` 子查询聚合出 `message_count`，再用相关子查询取末条 `preview`，最后 `order_by(order_col, ChatSession.id.desc())` **恒追加 id DESC 保证排序稳定**。参数白名单与夹取放在仓储层（`size = min(max(size, 1), 100)`），保证仓储自身安全。

---

## 7. 扩展点

| 扩展方向 | 落点 | 说明 |
|---|---|---|
| 接入对话财务上下文 | `routers/ai.py:180` 和 `:229` | 在组装 messages 前调 `ai_context.build_user_context`，把数据塞进 system prompt |
| 分类别名从 DB 读 | `ai/category_alias.py:9` `ALIAS` | 现为硬编码词典，可改为 `categories.alias` 列或独立表 |
| 向量持久化 | `models/chat.py:105` 注释已给出指引 | 补 `embedding: Mapped[str \| None] = mapped_column(Text)`，避免每次重启重建 |
| 检索升级 | `ai/faq_retriever.py:78` 循环 | 种子 8 条够用；上千条换 numpy 矩阵点积或 FAISS |
| 工具调用（Agent） | 新增 `ai/tools.py` | 把「查账」「统计」注册成 LangChain Tool，让 LLM 自主决定是否查库，替代当前纯 prompt 方案 |
| 定时清理 | `tasks/purge.py` + `main.py` lifespan | 空桩，需接 APScheduler 并读取 `PURGE_*` 配置 |
| 追问续写闭环 | `routers/ai.py:426` | `BookkeepingIn.draft_id` 已定义但从未被读取，需在 LLM 解析前把草稿的 `raw_text` 与本次 message 拼接 |
| 评测数据集 | `ai_bookkeeping_logs.parse_json` | 每次解析结果都落库，可直接导出为微调/评测样本 |
| 多供应商切换 | `ai/llm.py` | 已是 OpenAI 兼容协议，加一层路由即可支持多网关降级 |

---

## 8. 常见问题（含 1 个阻断级缺陷）

### 8.1 阻断级 P0：`crud/statistics.py` 语法错误导致应用无法启动

```python
# crud/statistics.py:6-19 当前磁盘内容
async def get_summary(db: AsyncSession, user_id: int):
    """收支汇总：总收入、总支出、结余、记录数"""
    # TODO: 实现
    stmt=                     # ← 第 9 行，写了一半，SyntaxError
```

**故障传导链：**

```
main.py:14  from routers import admin, ai, category, record, statistics, user
  └─ routers/ai.py:35  from ai import context as ai_context
       └─ ai/context.py:7  from crud.statistics import get_category_stats, get_summary
            └─ crud/statistics.py:9  SyntaxError: invalid syntax
```

实测输出：

```
File "E:\一些毕设探索\记账管理系统_fastapi\fast_backend\crud\statistics.py", line 9
    stmt=
         ^
SyntaxError: invalid syntax
```

**影响范围**：不止 AI 模块——`main.py` 整个起不来，所有端点全挂。

**佐证**：工作区根目录的 `_verify_stats.py` 第 42 行注释写着「整个 app 能否导入（覆盖 crud/statistics.py 之前的语法错误）」——说明这个坑之前修好过，现在又回退了。

**修复口径**（签名已由两处调用方确定）：

```python
# routers/statistics.py:27  → get_summary(db, user_id, year, month) -> (total_income, total_expense)
# routers/statistics.py:53  → get_category_stats(db, user_id, year, month, type) -> [(category_id, name, amount)]
# ai/context.py:25/29/29    → 同上，context 传的是 stat_type=0
```

`_verify_stats.py:26-40` 里已经写好了参考 SQL（`func.coalesce(func.sum(case(...)), 0)` + `outerjoin` + 日期区间过滤），直接搬过来即可。

### 8.2 P1：运行期必崩的 4 处

**（1）`crud/ai.py:164-168` 更新了不存在的列**

```python
stmt=update(ChatSession)\
    .where(...).values(title=title, update_time=now_ms())
```

`ChatSession`（`models/chat.py:18-39`）的列是 `created_at` / `updated_at` / `deleted_at`，**没有 `update_time`**。SQLAlchemy 会抛 `InvalidRequestError`。应为 `updated_at=now_ms()`。

**（2）`routers/ai.py:127` 参数顺序颠倒**

```python
await ai_crud.rename_session(db, session_id, body.title, user_id)
#     定义是: async def rename_session(db, session_id, user_id, title)   # crud/ai.py:158
```

`user_id` 与 `title` 互换，`WHERE user_id = <标题字符串>` 永远匹配不到。

**（3）`crud/ai.py:200-205` 批量删除条件写错**

```python
stmt=update(ChatSession)\
    .where(
        ChatSession.user_id==user_id,
        ChatSession.user_id.in_(ids),      # ← 应为 ChatSession.id.in_(ids)
        ChatSession.deleted_at==0
    )
```

`user_id` 判断写了两遍，目标会话永远删不掉，接口会一直返回 `{"success": true, "deleted": 0}`——**静默失败**，比报错更难排查。

**（4）`crud/ai.py:282` 与调用方签名不匹配**

```python
async def ai_stats(db: AsyncSession) -> dict:                 # 只收 1 个参数
stats = await ai_crud.ai_stats(db, user_id)                   # routers/ai.py:354 传了 2 个
```

直接 `TypeError`。顺带一提，`ai_stats` 的返回是 dict，而路由用 `stats.totalSessions` 属性访问（第 355 行），**即使参数修对了这里还会 `AttributeError`**——应改成 `stats["totalSessions"]`。

### 8.3 P2：功能性缺口

| 问题 | 位置 | 影响 |
|---|---|---|
| FAQ 索引从未构建 | `main.py` 无 lifespan/startup 钩子 | `_index` 初始为 `[]`，未调 `/faq/rebuild` 前 `/faq/search` 恒返回 `{"results": []}` |
| `draft_id` 从未被读取 | `routers/ai.py:426` 之后 | clarify 追问闭环未实现，返回的 `draftId` 无人消费 |
| `now` 参数从未被读取 | `BookkeepingIn.now` | 联调时无法覆盖「今天」 |
| 用户诉求被忽略 | `analyze_chain.py:45` | 硬编码「请分析我的消费情况」，`ExpenseAnalyzeIn.query` 不生效 |
| 近 10 条账单缺失 | `ai/context.py` | `UserFinanceContext.recent_records` 定义未用，与 `API文档_FastAPI.md:1073` 不符 |
| 清理任务空桩 | `tasks/purge.py` | 软删会话永不物理清理 |
| 阈值形同虚设 | `faq_retriever.py:81` | 见 6.3 |
| 占位日志状态错误 | `routers/ai.py:436-439` | 占位写 `action="created"` + `status=1`；若第 5 步 LLM 解析异常直接 return，会留下「created 但 record_ids 为空」的脏日志。建议占位用 `status=0` / `action="pending"` |

### 8.4 代码整洁度

- `ai/chat_chain.py:3` 残留 `# TODO: 实现见 06-AI模块.md` 与重复的模块 docstring（第 1 行和第 6 行各一个）；
- `schemas/ai.py` 前 179 行是被注释掉的旧定义，第 180 行起又重复 `import` 了一遍，同一文件两套结构；
- `routers/ai.py` 的 `import hashlib` 出现两次（第 22 行模块级 + 第 408 行函数内）；`amend_bookkeeping`（:613）和 `delete_bookkeeping`（:805）也有函数内的局部 import；
- `crud/ai.py:48` `get_user_session` 是唯一带 `# TODO: 实现（...）` 但实际已实现的函数，注释未清理。

### 8.5 事务边界混乱（值得单独说）

`crud/ai.py` 多个函数内部自带 `await db.commit()`：`create_session`（:153）、`rename_session`（:171）、`soft_delete_session`（:192）、`batch_soft_delete_sessions`（:207）、`add_message`（:235）。

而 `config/db_config.py:41` 的 `get_db` 依赖本身就在请求结束时统一 commit：

```python
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()      # 请求级事务边界
        except Exception:
            await session.rollback()
            raise
```

两者叠加后，记账链路的原子性被切成三段：占位日志 commit → records flush → 日志回写 commit。中途失败会留下脏日志，且**强幂等查询 `find_log_by_client_msg` 要求 `record_ids IS NOT NULL`**（`crud/ai.py:350`），脏日志会被跳过 → 用户重发时不会走 duplicate 分支，而是重新入账。

建议：CRUD 层只 `flush`，`commit` 统一交给 `get_db` 或路由层显式控制。

### 8.6 多进程部署注意

`ai/faq_retriever.py:16` 的 `_index` 是**模块级全局**。`uvicorn --workers 4` 时每个 worker 有独立副本，需各自调一次 `/faq/rebuild`；`ai/llm.py:9` 的 `_chat_llm` 单例同理（但只是多建几个客户端，无害）。

---

## 9. 性能与优化建议

### 9.1 客户端复用（收益最大，改动最小）

`get_chat_llm` 已有单例，但 `get_analyze_llm`（:24）和 `get_embeddings`（:29）每次调用都 `new` 一个对象——每个 `ChatOpenAI` 实例自带一个 `httpx.AsyncClient` 连接池，**每次请求都重建连接**。建议同样加 `@lru_cache` 或模块级单例。

### 9.2 结构化输出的 schema 复用

`ai/analyze_chain.py:32` 的 `_LLMPart` 定义在**函数体内**，每次请求都要重新构造 Pydantic 模型、重新生成 JSON Schema 并随请求下发。提到模块级即可，零风险。

### 9.3 检索性能

`faq_retriever.search_faq` 是纯 Python 循环 + 逐条 `zip` 求余弦（:78-88）。种子数据 8 条无所谓，量级上千时应改为：

- numpy 矩阵化：`np.dot(matrix, q_vec)` 一次算完；
- 或引入 FAISS / pgvector；
- 加一层 LRU 缓存查询向量（高频问题会重复）。

### 9.4 会话列表查询

`crud/ai.py:57-134` 的两个相关子查询在会话量大时是 O(n) 次子查询，且 `keyword` 用了 `LIKE '%kw%'` 前缀通配（无法走索引）。优化路径：

- 冗余一个 `sessions.preview` 列，在 `add_message` 时同步更新，省掉两个子查询；
- 关键词检索改用 MySQL 全文索引（`FULLTEXT`）或倒排表。

### 9.5 记账链路串行耗时

`routers/ai.py:448-466` 的分类查询与 LLM 解析是串行的，可并行：

```python
cat_task = db.execute(select(Category).where(...))
parse_task = parse_bookkeeping(message, today.isoformat(), names)   # names 依赖 cat_task
```

但 `parse_bookkeeping` 的 `category_names` 依赖分类查询结果，无法完全并行。可行的优化是**缓存分类列表**（用户分类变更频率极低），用 `user_id` 做键的 TTL 缓存，这样 LLM 调用就能和幂等检查并行发起。

### 9.6 历史窗口裁剪的语义修正

`ai/memory.py:17-20` 是**先累加再判断**：

```python
for m in reversed(msgs):
    used += len(m.content)
    if used > MAX_TOKENS or len(picked) >= KEEP_RECENT:
        break                       # 超预算的那条被丢弃，不进窗口
    picked.append(...)
```

超预算的单条消息会被整条丢弃。若某条消息本身就超过 2000 字，窗口会直接变空。更稳的做法是先 append 再判断，或对超长单条做截断。

同时建议把硬编码的 `MAX_TOKENS` / `KEEP_RECENT` 改为读 `settings.MAX_HISTORY_TOKENS` / `settings.KEEP_RECENT_MESSAGES`，让那两个配置项真正生效。

### 9.7 其他

- **SSE 落库时机**：当前必须等全部 chunk 产出才落库助手消息，用户中途断连则回复丢失。可改为每 N 个 chunk 增量 UPDATE，或至少在 `finally` 里落库已生成的部分。
- **`analyze_expenses` 异常回显**：`routers/ai.py:267` 是 `ai_error(f"分析失败: {e}")`，直接把异常字符串回给前端，会泄露内部信息（对比 `analyze_budget` 第 284 行只返回「预算规划失败」并记日志）。建议统一为不透明错误 + `logger.exception`。
- **`requirements.txt` 补依赖**：把 `langchain-openai` / `apscheduler` 从注释改为正式依赖，否则换机部署必挂。

---

## 10. 小结

这个 AI 模块的工程质量整体是**高于一般毕设水平**的，几个亮点值得在论文里写：

1. **反幻觉口径贯穿全链路**——`amount` 绝不猜测、数值字段服务端计算、`fallback` 走「其他」分类并附 warning，把「LLM 不可信」当成第一性假设来做设计；
2. **幂等设计完整**——强幂等（`client_msg_id` + 唯一键）+ 弱幂等（`dedup_hash` + 300 秒窗口）双层，且用「先写后查」而非「先查后写」解决并发；
3. **审计可追溯**——`ai_bookkeeping_logs` 用 `parent_id` 串起「记账 → 修改 → 撤销」，`parse_json` 保留 LLM 原始输出，天然是评测数据集；
4. **降级路径明确**——FAQ 检索的语义→关键词降级、SSE 的 `error` 事件、`ai_error` 裸返回，都有清晰的失败语义；
5. **契约意识强**——`routers/ai.py` 头部用 20 行注释解释「为什么必须裸返回」，并标注了路由注册顺序陷阱，这类注释在毕设项目里很罕见。

主要待办按优先级：

| 优先级 | 事项 |
|---|---|
| P0 | 补 `crud/statistics.py` 的 `get_summary` / `get_category_stats` 实现（否则应用起不来） |
| P1 | 修 `rename_session` 的列名与参数顺序、`batch_soft_delete_sessions` 的 `id.in_`、`ai_stats` 的参数与属性访问 |
| P2 | 启动时构建 FAQ 索引；实现 `draft_id` 追问闭环；接通 `ExpenseAnalyzeIn.query`；修 `_cosine` 阈值语义 |
| P3 | 客户端单例化、`_LLMPart` 提到模块级、事务边界统一、清理 `requirements.txt` 与冗余注释 |
