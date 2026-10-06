"""ai.faq_retriever 单元测试 — 相似度口径 / 阈值过滤 / 降级 / 缓存 / 知识库闸门

全部用 FakeEmbeddings，**不产生任何真实 Embedding 调用与计费**。
"""

import types

import pytest

from ai import faq_retriever as fr
from config.settings import FAQ_QUERY_CACHE_SIZE


class FakeEmbeddings:
    """按文本内容确定性返回**互相正交**的向量的假 Embedding。

    5 维单位基向量：含"预算" → e0；含"分类" → e1；含"导出" → e2；否则 → e3。
    刻意做成正交，才能构造出「余弦恰好 1.0」与「余弦恰好 0.0」两个极端，
    从而验证阈值是否真的在过滤（若都落进同一个近似方向，测不出过滤是否生效）。
    三条 FAQ 各占一个正交方向，另留一个 e3 给"与任何 FAQ 都无关"的查询。
    """

    _BUCKETS = ("预算", "分类", "导出")

    def __init__(self):
        self.doc_calls = 0
        self.query_calls = 0
        self._vecs = {}

    def _vec(self, text: str) -> list[float]:
        if text not in self._vecs:
            vec = [0.0] * (len(self._BUCKETS) + 1)
            for i, kw in enumerate(self._BUCKETS):
                if kw in text:
                    vec[i] = 1.0
                    break
            else:
                vec[-1] = 1.0
            self._vecs[text] = vec
        return self._vecs[text]

    async def aembed_documents(self, texts):
        self.doc_calls += 1
        return [self._vec(t) for t in texts]

    async def aembed_query(self, text):
        self.query_calls += 1
        return self._vec(text)


def faq(fid, question, answer, category="通用"):
    return types.SimpleNamespace(
        id=fid, question=question, answer=answer, category=category
    )


ROWS = [
    # 每条的 question 与 answer 都落在同一个正交方向上，
    # 这样「与三条都无关」的查询才会落到 e3 而无命中。
    faq(1, "预算怎么设置", "在预算页设置月预算总额", "预算"),
    faq(2, "系统支持哪些分类", "支持餐饮/交通/日用/居住/通讯/娱乐等分类", "功能"),
    faq(3, "数据怎么导出", "在设置页导出 CSV", "数据"),
]


@pytest.fixture(autouse=True)
def _reset_index(monkeypatch):
    """每个用例独立索引与缓存，并注入 FakeEmbeddings"""
    fr._index = []
    fr._query_cache.clear()
    fake = FakeEmbeddings()
    import ai.llm as llm_mod
    monkeypatch.setattr(llm_mod, "get_embeddings", lambda: fake)
    yield fake
    fr._index = []
    fr._query_cache.clear()


class TestCosine:
    def test_raw_cosine_range(self):
        assert fr._cosine_raw([1, 0], [1, 0]) == pytest.approx(1.0)
        assert fr._cosine_raw([1, 0], [0, 1]) == pytest.approx(0.0)
        assert fr._cosine_raw([1, 0], [-1, 0]) == pytest.approx(-1.0)

    def test_zero_vector_returns_negative_sentinel(self):
        # 零向量无法定义相似度，返回 -1（必然低于任何阈值）而不是 0.0
        assert fr._cosine_raw([0, 0], [1, 0]) == -1.0
        assert fr._cosine_raw([], [1, 0]) == -1.0

    def test_display_score_mapping(self):
        assert fr._to_display_score(1.0) == 1.0
        assert fr._to_display_score(0.0) == 0.5
        assert fr._to_display_score(-1.0) == 0.0


class TestThresholdActuallyFilters:
    """回归：阈值必须真的过滤。

    历史 bug —— _cosine 返回 (cos+1)/2 归一化值，而阈值也写 0.5，
    等价于「原始余弦 ≥ 0 即通过」，任何条目都能进 top_k。
    """

    @pytest.mark.asyncio
    async def test_orthogonal_item_filtered_out(self):
        await fr.rebuild(ROWS)
        # query 向量 [1,0]（含"预算"）对"分类"条目余弦 0 < 阈值 → 必须被滤掉
        results, mode = await fr.search_faq_detailed("预算怎么算")
        assert mode == "vector"
        assert [r["id"] for r in results] == [1]

    @pytest.mark.asyncio
    async def test_display_score_not_used_for_filtering(self):
        await fr.rebuild(ROWS)
        results, _ = await fr.search_faq_detailed("预算怎么算")
        # 归一化展示分应 >= 0.5，但过滤依据是原始余弦
        assert all(r["score"] >= 0.5 for r in results)
        assert len(results) == 1  # 不是 3 条

    @pytest.mark.asyncio
    async def test_related_item_kept(self):
        await fr.rebuild(ROWS)
        results, _ = await fr.search_faq_detailed("预算")
        assert 1 in [r["id"] for r in results]


class TestAnswerAlsoEmbedded:
    """answer 也参与召回（原先只 embed question）"""

    @pytest.mark.asyncio
    async def test_rebuild_embeds_question_and_answer(self, _reset_index):
        await fr.rebuild(ROWS)
        fake = _reset_index
        assert fake.doc_calls == 1
        # 3 条 FAQ × 2 字段 = 6 次向量化
        assert len(fake._vecs) == 6
        for it in fr._index:
            assert it["vector"] is not None
            assert it["vector_answer"] is not None

    @pytest.mark.asyncio
    async def test_answer_match_counts_as_hit(self):
        await fr.rebuild(ROWS)
        # "分类" 只出现在第 2 条的 question 与 answer 里
        results, _ = await fr.search_faq_detailed("分类")
        assert 2 in [r["id"] for r in results]


class TestFallback:
    @pytest.mark.asyncio
    async def test_keyword_mode_when_embedding_fails(self, monkeypatch):
        await fr.rebuild(ROWS)
        import ai.llm as llm_mod

        async def boom(text):
            raise RuntimeError("embedding gateway down")

        monkeypatch.setattr(llm_mod, "get_embeddings", lambda: type(
            "E", (), {"aembed_query": staticmethod(boom)}
        )())
        results, mode = await fr.search_faq_detailed("预算怎么设置")
        assert mode == "keyword"
        assert 1 in [r["id"] for r in results]

    @pytest.mark.asyncio
    async def test_keyword_mode_when_index_has_no_vectors(self):
        # 启动兜底只装关键词索引（vector=None）
        await fr.ensure_index(ROWS)
        assert fr.has_vector_index() is False
        results, mode = await fr.search_faq_detailed("预算")
        assert mode == "keyword"
        assert results

    @pytest.mark.asyncio
    async def test_empty_index_returns_empty_mode(self):
        results, mode = await fr.search_faq_detailed("预算")
        assert results == []
        assert mode == "empty"

    @pytest.mark.asyncio
    async def test_blank_query(self):
        await fr.rebuild(ROWS)
        assert await fr.search_faq_detailed("   ") == ([], "empty")

    @pytest.mark.asyncio
    async def test_never_raises_on_empty_answer(self):
        """关键词模式下完全无字符重合时应返回空，而不是 0 分条目堆满 top_k"""
        await fr.ensure_index(ROWS)
        results, mode = await fr.search_faq_detailed("zzzzqqqq")
        assert mode == "keyword"
        assert results == []


class TestQueryCache:
    @pytest.mark.asyncio
    async def test_repeat_query_hits_cache(self, _reset_index):
        await fr.rebuild(ROWS)
        await fr.search_faq_detailed("预算怎么设置")
        await fr.search_faq_detailed("预算怎么设置")
        assert _reset_index.query_calls == 1

    @pytest.mark.asyncio
    async def test_cache_key_normalizes_whitespace_and_case(self, _reset_index):
        await fr.rebuild(ROWS)
        await fr.search_faq_detailed("预算  怎么设置")
        await fr.search_faq_detailed(" 预算 怎么设置 ".strip())
        assert _reset_index.query_calls == 1

    @pytest.mark.asyncio
    async def test_cache_is_lru_bounded(self, _reset_index):
        await fr.rebuild(ROWS)
        for i in range(FAQ_QUERY_CACHE_SIZE + 20):
            await fr.search_faq_detailed(f"查询{i}")
        assert len(fr._query_cache) <= FAQ_QUERY_CACHE_SIZE

    @pytest.mark.asyncio
    async def test_failure_is_not_cached(self, monkeypatch):
        """失败不该进缓存，否则网关恢复前一直走降级"""
        await fr.rebuild(ROWS)
        import ai.llm as llm_mod
        calls = {"n": 0}

        async def flaky(text):
            calls["n"] += 1
            if calls["n"] == 1:
                raise RuntimeError("boom")
            return [1.0, 0.0, 0.0, 0.0, 0.0]

        monkeypatch.setattr(llm_mod, "get_embeddings", lambda: type(
            "E", (), {"aembed_query": staticmethod(flaky)}
        )())
        _, mode1 = await fr.search_faq_detailed("预算")
        assert mode1 == "keyword"
        _, mode2 = await fr.search_faq_detailed("预算")
        assert mode2 == "vector"   # 第二次重新尝试并成功


class TestKnowledgeGate:
    """知识库注入闸门：只为知识库型问句付一次 embedding 代价"""

    @pytest.mark.asyncio
    async def test_kb_question_triggers_retrieval(self, _reset_index):
        await fr.rebuild(ROWS)
        block = await fr.build_knowledge_block("预算怎么设置")
        assert "预算怎么设置" in block
        assert _reset_index.query_calls == 1

    @pytest.mark.asyncio
    async def test_data_question_skipped(self, _reset_index):
        await fr.rebuild(ROWS)
        # 账本数据问题走财务数据块，不该触发知识库检索
        assert await fr.build_knowledge_block("这个月餐饮花了多少") == ""
        assert _reset_index.query_calls == 0

    @pytest.mark.asyncio
    async def test_trend_question_skipped(self, _reset_index):
        await fr.rebuild(ROWS)
        assert await fr.build_knowledge_block("为什么餐饮涨了") == ""
        assert await fr.build_knowledge_block("帮我看看上月支出") == ""
        assert _reset_index.query_calls == 0

    @pytest.mark.asyncio
    async def test_usage_question_not_excluded_by_account_noun(self, _reset_index):
        """「收入怎么记」问的是操作方式而非金额，不能被账本名词误伤"""
        assert fr._needs_knowledge("收入怎么记") is True
        assert fr._needs_knowledge("支出怎么分类") is True
        assert fr._needs_knowledge("预算超了怎么办") is True

    @pytest.mark.asyncio
    async def test_plain_statement_skipped(self, _reset_index):
        await fr.rebuild(ROWS)
        assert await fr.build_knowledge_block("午饭吃了35块") == ""
        assert _reset_index.query_calls == 0

    @pytest.mark.asyncio
    async def test_too_long_query_skipped(self, _reset_index):
        await fr.rebuild(ROWS)
        assert await fr.build_knowledge_block("如何" + "啊" * 80) == ""
        assert _reset_index.query_calls == 0

    @pytest.mark.asyncio
    async def test_no_hit_returns_empty_block(self, _reset_index):
        await fr.rebuild(ROWS)
        assert await fr.build_knowledge_block("有没有会员功能") == ""


class TestIndexHelpers:
    def test_index_size_and_has_vector(self):
        fr._index = []
        assert fr.index_size() == 0
        assert fr.has_vector_index() is False

    @pytest.mark.asyncio
    async def test_ensure_index_does_not_embed(self, _reset_index):
        await fr.ensure_index(ROWS)
        assert fr.index_size() == 3
        assert _reset_index.doc_calls == 0   # 零 API 成本

    @pytest.mark.asyncio
    async def test_rebuild_empty_rows_clears_index(self, _reset_index):
        await fr.rebuild(ROWS)
        assert fr.index_size() == 3
        assert await fr.rebuild([]) == 0
        assert fr.index_size() == 0

    @pytest.mark.asyncio
    async def test_failed_rebuild_keeps_old_index(self, monkeypatch):
        """中途失败不应把索引打成半新半旧（旧索引仍可用）"""
        await fr.rebuild(ROWS)
        import ai.llm as llm_mod

        async def boom(texts):
            raise RuntimeError("gateway down")

        monkeypatch.setattr(llm_mod, "get_embeddings", lambda: type(
            "E", (), {"aembed_documents": staticmethod(boom)}
        )())
        with pytest.raises(RuntimeError):
            await fr.rebuild(ROWS + [faq(4, "新增", "新增答案")])
        assert fr.index_size() == 3
