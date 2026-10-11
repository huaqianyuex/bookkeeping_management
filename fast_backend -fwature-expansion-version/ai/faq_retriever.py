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
import asyncio
import logging
import re
import time
from collections import OrderedDict

from config.settings import (
    FAQ_SIMILARITY_THRESHOLD, FAQ_TOP_K, FAQ_QUERY_CACHE_SIZE,
)

logger = logging.getLogger(__name__)

# 内存索引：[{id, question, answer, category, vector, vector_answer, dim}]
# vector/vector_answer 为 None 表示该条目处于降级（关键词）模式
_index: list[dict] = []

# query(归一化) -> 查询向量。FAQ 问题重复率极高，命中即省一次 Embedding 计费。
# 进程内缓存：重建索引不影响其有效性（查询向量只与 query 有关，与索引无关）。
_query_cache: "OrderedDict[str, list[float]]" = OrderedDict()


def _log_dim_mismatch(q_dim: int, idx_dim: int) -> None:
    """维度不一致只记一次日志，避免每次检索刷屏"""
    key = (q_dim, idx_dim)
    if _dim_warned.get(key):
        return
    _dim_warned[key] = True
    logger.error(
        "FAQ 索引维度过期：query=%d 索引=%d —— EMBEDDING_MODEL 可能已变更，"
        "请调 POST /api/ai/faq/rebuild 重建（本次已跳过该条）",
        q_dim, idx_dim,
    )


_dim_warned: dict[tuple[int, int], bool] = {}

# ── single-flight 与冷却 ──────────────────────────────────────────────────
# rebuild 会调全量 Embedding，是**真金白银**的外部调用。原先没有任何互斥：
# 两个管理员同时点「重建」就会付两次钱，连续点击更是线性放大。
#
# 这里用「布尔标志 + 冷却时间」而非 asyncio.Lock：
#   - 检查与置位之间没有 await，单事件循环下天然原子，不需要锁；
#   - asyncio.Lock 在创建时会绑定当时的 event loop，模块级实例在多 loop
#     场景（测试用例会各自新建 loop）会抛 "bound to a different event loop"，
#     是比它想解决的问题更麻烦的坑。
_rebuilding = False
_rebuild_locked_until: float = 0.0        # 冷却截止时间戳
REBUILD_COOLDOWN_SECONDS = 60
REBUILD_REJECTED = "重建正在进行中或刚完成，请稍后再试"


class RebuildBusy(RuntimeError):
    """重建正在执行或处于冷却中——调用方应转成友好提示，不要当系统错误"""


async def rebuild_cooldown_left() -> int:
    """剩余冷却秒数；0 表示可重建"""
    left = _rebuild_locked_until - time.time()
    return int(left) + 1 if left > 0 else 0


async def mark_stale(reason: str = "faq_changed") -> None:
    """标记索引已过期。

    管理端增删改 FAQ 后调用。此前 CRUD 不通知检索层，管理员新增一条 FAQ，
    /faq/search 依然搜不到（索引里没有），且**系统自己无法感知已过期**。
    标记后下一次检索会明确告知 mode=stale，运维/管理员能立刻看出来。
    """
    global _stale_reason
    if _stale_reason is None:
        _stale_reason = reason


def stale_reason() -> str | None:
    return _stale_reason


_stale_reason: str | None = None


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


async def _rebuild_uncached(rows) -> int:
    """真正的重建逻辑（调用方已持有 single-flight 锁）

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

    # ⚠️ 维度一致性校验：若换过 EMBEDDING_MODEL 而未清索引，各条向量长度可能不一致。
    # 旧的 zip(a, b) 遇长度不等会**静默截断**，算出看似合理实则错误的相似度且全程
    # 不报错——这类静默错误比崩溃更难发现。这里显式拒绝。
    dims = {len(v) for v in vectors if v is not None}
    if len(dims) > 1:
        raise ValueError(
            f"embedding 维度不一致：{sorted(dims)}——"
            "疑似 EMBEDDING_MODEL 已变更，请先清空索引再重建"
        )
    if len(vectors) != len(texts):
        raise ValueError(
            f"embedding 返回条数不匹配：请求 {len(texts)} 条，返回 {len(vectors)} 条"
        )
    dim = dims.pop() if dims else 0

    new_index = []
    for i, r in enumerate(rows):
        new_index.append({
            "id": r.id,
            "question": r.question,
            "answer": r.answer,
            "category": r.category,
            "vector": vectors[2 * i],
            "vector_answer": vectors[2 * i + 1],
            "dim": dim,
        })
    # 全部算完再整体替换：中途异常时旧索引仍可用，不留半新半旧状态
    _index = new_index
    return len(_index)


async def rebuild(rows) -> int:
    """6.12 全量重建向量索引。Embedding 失败时抛异常，由路由兜底返回错误结构。

    single-flight：并发调用只有第一个真正执行，其余直接抛 RebuildBusy，
    由路由转成中文错误。避免多个管理员同时点「重建」重复计费。
    冷却：成功后再锁 REBUILD_COOLDOWN_SECONDS 秒，挡住连续点击。

    ⚠️ 维度一致性：换过 EMBEDDING_MODEL 而未重建时，各条向量长度可能不一致；
    旧实现用 zip() 求点积，长度不等会**静默截断**，算出看似合理实则全错的
    相似度且不报错。_rebuild_uncached 里已改为显式拒绝。
    """
    global _rebuilding, _rebuild_locked_until, _stale_reason

    if _rebuilding:
        raise RebuildBusy(REBUILD_REJECTED)
    left = _rebuild_locked_until - time.time()
    if left > 0:
        raise RebuildBusy(f"{REBUILD_REJECTED}（还需 {int(left) + 1} 秒）")

    # 检查与置位之间没有 await，单事件循环下这一步是原子的
    _rebuilding = True
    _rebuild_locked_until = time.time() + REBUILD_COOLDOWN_SECONDS
    try:
        n = await _rebuild_uncached(rows)
    except Exception:
        # 失败不占冷却，允许管理员立即重试
        _rebuild_locked_until = 0.0
        raise
    finally:
        _rebuilding = False
    _stale_reason = None          # 重建成功即视为新鲜
    _dim_warned.clear()           # 维度告警随之失效
    return n


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

    返回 (results, mode)：mode ∈ {"vector", "keyword", "empty", "stale"}
    历史问题：降级是「静默」的——search_faq 内部吞掉异常后直接换关键词检索，
    路由层的 `except → {"fallback": true}` 几乎永远不触发，前端无从判断
    「没命中」与「向量服务挂了只能凑合答」，两种 score 量纲还不可比。
    新增 stale：管理端改了 FAQ 但未重建时，用旧索引检索出来的结果不可信，
    必须让调用方看见，否则会误以为「知识库里就是没有这条」。
    """
    if not query or not query.strip() or not _index:
        return [], "empty"

    if _stale_reason is not None:
        return [], "stale"

    q_vec = await _embed_query(query)

    scored: list[tuple[float, dict]] = []
    for item in _index:
        vec = item.get("vector")
        vec_ans = item.get("vector_answer")
        if q_vec is not None and vec is not None:
            # ⚠️ 维度守卫：换模型后旧索引未重建时，这里会长度不等。
            # 绝不能让它走到 _cosine_raw —— 那里 zip() 会静默截断算出错分数。
            if len(q_vec) != len(vec):
                _log_dim_mismatch(len(q_vec), len(vec))
                continue
            raw = _cosine_raw(q_vec, vec)
            if vec_ans is not None:
                if len(q_vec) == len(vec_ans):
                    raw = max(raw, _cosine_raw(q_vec, vec_ans))
                else:
                    _log_dim_mismatch(len(q_vec), len(vec_ans))
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
