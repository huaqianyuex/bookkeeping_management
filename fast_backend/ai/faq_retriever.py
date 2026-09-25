"""FAQ 检索 — 进程内向量索引 + 余弦相似度匹配，Embedding 不可用时降级关键词检索

口径（06-AI模块.md / AI对话接口说明.md §6.11/§6.12）：
- faq 表不存向量，索引在内存中全量构建（种子数据 8 条）；
- 被 embedding 的 query 是每条 FAQ 的 question 字段；
- rebuild：清空 -> 重载 -> 算向量 -> 存内存，Embedding 失败则抛异常（路由返回 {"error","detail"}）；
- search：正常返回 [{id,question,answer,category,score}]（score 0~1 降序，取 top_k），
  语义链路任何异常自动降级为关键词重合度检索，score 仍为 0~1，不再向外抛。
"""
import asyncio

from config.settings import FAQ_SIMILARITY_THRESHOLD, FAQ_TOP_K
from models.chat import Faq

# 内存索引：[{id, question, answer, category, vector(list[float])}]；vector=None 表示降级条目
_index: list[dict] = []


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(y * y for y in b) ** 0.5
    if na == 0 or nb == 0:
        return 0.0
    # 余弦值域 [-1,1]，归一到 [0,1] 方便前端展示
    return max(0.0, min(1.0, (dot / (na * nb) + 1) / 2))


def _keyword_score(query: str, text: str) -> float:
    """降级方案：字符级重合度（中文场景下近似关键词匹配），归一到 0~1"""
    if not query or not text:
        return 0.0
    hits = sum(1 for ch in set(query) if ch in text)
    return hits / len(set(query))


async def rebuild(rows: list[Faq]) -> int:
    """6.12 全量重建向量索引。Embedding 失败时抛异常，由路由兜底返回错误结构"""
    global _index
    if not rows:
        _index = []
        return 0

    from ai.llm import get_embeddings

    embeddings = get_embeddings()
    texts = [r.question for r in rows]
    vectors = await embeddings.aembed_documents(texts)   # async 批量，不阻塞事件循环

    _index = [
        {
            "id": r.id,
            "question": r.question,
            "answer": r.answer,
            "category": r.category,
            "vector": vec,
        }
        for r, vec in zip(rows, vectors)
    ]
    return len(_index)


async def search_faq(query: str, top_k: int = FAQ_TOP_K) -> list[dict]:
    """6.11 语义检索。优先余弦相似度（阈值 FAQ_SIMILARITY_THRESHOLD），
    查询向量算不出来时降级关键词重合度；两种方式 score 都是 0~1"""
    if not query.strip() or not _index:
        return []

    q_vec: list[float] | None = None
    try:
        from ai.llm import get_embeddings

        q_vec = await get_embeddings().aembed_query(query)
    except Exception:
        q_vec = None   # 降级为关键词检索

    scored: list[tuple[float, dict]] = []
    for item in _index:
        if q_vec is not None and item["vector"] is not None:
            score = _cosine(q_vec, item["vector"])
            if score < FAQ_SIMILARITY_THRESHOLD:
                continue
        else:
            score = max(
                _keyword_score(query, item["question"]),
                _keyword_score(query, item["answer"]),
            )
        scored.append((score, item))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [
        {
            "id": it["id"],
            "question": it["question"],
            "answer": it["answer"],
            "category": it["category"],
            "score": round(score, 4),
        }
        for score, it in scored[:top_k]
    ]
