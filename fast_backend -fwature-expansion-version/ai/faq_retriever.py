"""FAQ 检索 — 进程内向量索引 + 余弦相似度匹配，Embedding 不可用时降级关键词检索

口径（06-AI模块.md / AI对话接口说明.md §6.11/§6.12）：
- faq 表不存向量，索引在内存中全量构建（种子数据 8 条）；
- question 与 answer **分别**向量化，命中取两者较大分（只 embed question 会让
  「答案里出现的问题关键词」完全无法召回）；
- rebuild：清空 -> 重载 -> 算向量 -> 存内存，Embedding 失败则抛异常（路由返回 {"error"}）；
- search：正常返回 [{id,question,answer,category,score}]（score 0~1 降序，取 top_k），
  语义链路任何异常自动降级为关键词重合度检索，score 仍为 0~1，不再向外抛。

⚠️ 相似度口径（勿改回）：阈值比对用**原始余弦** `_cosine_raw`，
返回给前端的 score 用**归一化值** `(cos+1)/2`。
两者混用会让 FAQ_SIMILARITY_THRESHOLD 失效（原始余弦 0 → 归一化 0.5，
恰好等于旧默认值 0.5，等价于不设阈值）。
"""
import re
from collections import OrderedDict

from config.settings import (
    FAQ_SIMILARITY_THRESHOLD, FAQ_TOP_K, FAQ_QUERY_CACHE_SIZE,
)

# 内存索引：[{id, question, answer, category, vector, vector_answer}]
# vector/vector_answer 为 None 表示该条目处于降级（关键词）模式
_index: list[dict] = []

# query(归一化) -> 查询向量。FAQ 问题重复率极高，命中即省一次 Embedding 计费。
# 进程内缓存：重建索引不影响其有效性（查询向量只与 query 有关，与索引无关）。
_query_cache: "OrderedDict[str, list[float]]" = OrderedDict()


def _cosine_raw(a: list[float], b: list[float]) -> float:
    """原始余弦相似度，值域 [-1, 1]。**阈值过滤必须用这个值。**"""
    if not a or not b:
        return -1.0
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(y * y for y in b) ** 0.5
    if na == 0 or nb == 0:
        return -1.0
    return dot / (na * nb)


def _to_display_score(raw: float) -> float:
    """原始余弦 → [0,1] 展示分。前端只展示这个值，不参与过滤。"""
    return max(0.0, min(1.0, (raw + 1) / 2))


def _keyword_score(query: str, text: str) -> float:
    """降级方案：字符级重合度（中文场景下近似关键词匹配），归一到 0~1"""
    if not query or not text:
        return 0.0
    hits = sum(1 for ch in set(query) if ch in text)
    return hits / len(set(query))


def index_size() -> int:
    """索引条目数（供 /faq/search 与启动日志观测）"""
    return len(_index)


def has_vector_index() -> bool:
    """是否已装填向量索引。启动兜底只装关键词索引，此处为 False。"""
    return any(it.get("vector") is not None for it in _index)


def _cache_key(query: str) -> str:
    """归一化：小写 + 折叠空白，让「怎么 记账」与「怎么记账」命中同一条缓存"""
    return re.sub(r"\s+", " ", query.strip().lower())


def _cache_get(key: str) -> list[float] | None:
    vec = _query_cache.get(key)
    if vec is not None:
        _query_cache.move_to_end(key)
    return vec


def _cache_put(key: str, vec: list[float]) -> None:
    _query_cache[key] = vec
    _query_cache.move_to_end(key)
    while len(_query_cache) > FAQ_QUERY_CACHE_SIZE:
        _query_cache.popitem(last=False)


async def ensure_index(rows) -> int:
    """启动兜底重建：只装填关键词索引（vector=None，检索自动降级关键词），不调 embedding、零 API 成本。

    进程重启后内存索引为空，若不兜底，search_faq 会静默返回 [] 直到管理员手动 rebuild。
    向量索引仍由 /api/ai/faq/rebuild（管理员）按需全量重建。
    """
    global _index
    _index = [
        {"id": r.id, "question": r.question, "answer": r.answer,
         "category": r.category, "vector": None, "vector_answer": None}
        for r in rows
    ]
    return len(_index)


async def rebuild(rows) -> int:
    """6.12 全量重建向量索引。Embedding 失败时抛异常，由路由兜底返回错误结构。

    question 与 answer 各算一条向量，检索时取较大者——只 embed question 时，
    「用户按答案里的措辞提问」这一路召回恒为 0。
    """
    global _index
    if not rows:
        _index = []
        return 0

    from ai.llm import get_embeddings

    embeddings = get_embeddings()
    texts: list[str] = []
    for r in rows:
        texts.append(r.question)
        texts.append(r.answer)
    # async 批量，不阻塞事件循环
    vectors = await embeddings.aembed_documents(texts)

    new_index = []
    for i, r in enumerate(rows):
        new_index.append({
            "id": r.id,
            "question": r.question,
            "answer": r.answer,
            "category": r.category,
            "vector": vectors[2 * i],
            "vector_answer": vectors[2 * i + 1] if len(vectors) > 2 * i + 1 else None,
        })
    # 全部算完再整体替换：中途异常时旧索引仍可用，不留半新半旧状态
    _index = new_index
    return len(_index)


async def _embed_query(query: str) -> list[float] | None:
    """算查询向量，失败返回 None（调用方降级关键词）。带 LRU 缓存。"""
    key = _cache_key(query)
    cached = _cache_get(key)
    if cached is not None:
        return cached
    try:
        from ai.llm import get_embeddings

        vec = await get_embeddings().aembed_query(query)
    except Exception:
        return None
    _cache_put(key, vec)
    return vec


async def search_faq(query: str, top_k: int = FAQ_TOP_K) -> list[dict]:
    """6.11 语义检索。

    - question/answer 两个向量取较大分；
    - 过滤用**原始余弦**与 FAQ_SIMILARITY_THRESHOLD 比较（原始余弦值域 [-1,1]）；
    - 返回 score 为归一化到 0~1 的展示分，降序，取 top_k；
    - 查询向量算不出来时降级关键词重合度，且**不再向外抛**。
    """
    return await search_faq_detailed(query, top_k=top_k)[0]


async def search_faq_detailed(query: str, top_k: int = FAQ_TOP_K) -> tuple[list[dict], str]:
    """同 search_faq，但额外返回检索模式，便于路由透出降级状态给前端。

    返回 (results, mode)：mode ∈ {"vector", "keyword", "empty"}
    历史问题：降级是「静默」的——search_faq 内部吞掉异常后直接换关键词检索，
    路由层的 `except → {"fallback": true}` 几乎永远不触发，前端无从判断
    「没命中」与「向量服务挂了只能凑合答」，两种 score 量纲还不可比。
    """
    if not query or not query.strip() or not _index:
        return [], "empty"

    q_vec = await _embed_query(query)

    scored: list[tuple[float, dict]] = []
    for item in _index:
        vec = item.get("vector")
        vec_ans = item.get("vector_answer")
        if q_vec is not None and vec is not None:
            raw = _cosine_raw(q_vec, vec)
            if vec_ans is not None:
                raw = max(raw, _cosine_raw(q_vec, vec_ans))
            if raw < FAQ_SIMILARITY_THRESHOLD:
                continue
            score = _to_display_score(raw)
        else:
            # 降级：question 与 answer 都参与，取较大分
            score = max(
                _keyword_score(query, item["question"]),
                _keyword_score(query, item["answer"]),
            )
            if score <= 0:
                continue
        scored.append((score, item))

    scored.sort(key=lambda x: x[0], reverse=True)
    mode = "keyword" if q_vec is None or not has_vector_index() else "vector"
    return [
        {
            "id": it["id"],
            "question": it["question"],
            "answer": it["answer"],
            "category": it["category"],
            "score": round(score, 4),
        }
        for score, it in scored[:top_k]
    ], mode


# ── 对话链路注入 ──────────────────────────────────────────────────────────
# 知识库型问句（"预算怎么设" / "支持哪些分类"）光靠财务数据块答不了，
# 但每轮都检索 = 每轮多一次 Embedding 调用。故用规则闸门：只有命中
# 「疑问句 + 知识库主题词」的短问句才检索，其余一律返回空串（零成本）。

_KB_QUESTION_HINT = re.compile(
    r"(怎么|如何|怎样|咋|为什么|为啥|凭什么|什么是|啥是|能不能|可不可以|可以吗|"
    r"支持|有哪些|有没有|哪里|在哪|咋样|多少)"
)
# 明确不该触发检索：这些问的是「账本里有多少数据」，走财务数据块更准，
# 知识库里只有 8 条固定问答，检索必然无命中（白花一次 Embedding）。
# 注意别把「收入怎么记」这类**用法**问题误伤进来——它问的是操作方式，
# 不是金额，所以这里只列数据向/统计向的说法，不单列「收入/支出」等账本名词。
_KB_EXCLUDE = re.compile(
    r"(花了|买了|吃了|付了|多少|趋势|环比|占比|排名|统计|"
    r"涨了|降了|涨了|本月|上月|这个月|上个月|明细)"
)
_KB_MAX_QUERY_LEN = 40


def _needs_knowledge(query: str) -> bool:
    """规则闸门：是否值得为这句话检索一次知识库"""
    q = (query or "").strip()
    if not q or len(q) > _KB_MAX_QUERY_LEN:
        return False
    if not _KB_QUESTION_HINT.search(q):
        return False
    return not _KB_EXCLUDE.search(q)


async def build_knowledge_block(query: str, top_k: int = FAQ_TOP_K) -> str:
    """检索知识库并拼成可注入 system prompt 的块；不值得检索/无命中时返回空串。

    与 build_finance_block 同样以空串表示「无可注入内容」，调用方直接拼接。
    """
    if not _needs_knowledge(query):
        return ""
    try:
        results, _mode = await search_faq_detailed(query, top_k=top_k)
    except Exception:
        return ""
    if not results:
        return ""

    lines = "\n".join(
        f"{i + 1}. 【{r['category']}】{r['question']}\n   答：{r['answer']}"
        for i, r in enumerate(results)
    )
    return (
        "\n\n[知识库检索结果（来自 faq 表，仅供参考）]\n"
        "下列条目是系统知识库原文。回答时以它们为准，不要超出其范围自行发挥；"
        "若知识库未覆盖用户所问，如实说明「这个我暂时还不清楚」，不要编造。\n"
        f"{lines}\n"
    )
