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
    """每个用例独立索引、查询缓存、single-flight 冷却与 stale 标记，并注入 FakeEmbeddings"""
    fr._index = []
    fr._query_cache.clear()
    fr._rebuild_locked_until = 0.0     # 冷却是进程级状态，不重置会让用例互相污染
    fr._stale_reason = None
    fr._dim_warned.clear()
    fake = FakeEmbeddings()
    import ai.llm as llm_mod
    monkeypatch.setattr(llm_mod, "get_embeddings", lambda: fake)
    yield fake
    fr._index = []
    fr._query_cache.clear()
    fr._rebuild_locked_until = 0.0
    fr._stale_reason = None
    fr._dim_warned.clear()


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
        # 第二次重建会命中冷却（这是预期行为），先解冷却再验证空表分支
        fr._rebuild_locked_until = 0.0
        assert await fr.rebuild([]) == 0
        assert fr.index_size() == 0

    @pytest.mark.asyncio
    async def test_cooldown_blocks_rapid_second_rebuild(self, _reset_index):
        """冷却：刚重建完就再点「重建」应被拒，避免重复计费"""
        await fr.rebuild(ROWS)
        assert await fr.rebuild_cooldown_left() > 0
        with pytest.raises(fr.RebuildBusy):
            await fr.rebuild(ROWS)
        # 关键：被拒的那次**没有**真的调用 embedding
        assert _reset_index.doc_calls == 1

    @pytest.mark.asyncio
    async def test_concurrent_rebuild_runs_once(self, _reset_index):
        """single-flight：并发调用只有一个真正执行"""
        import asyncio as _aio
        results = await _aio.gather(*[fr.rebuild(ROWS) for _ in range(3)],
                                    return_exceptions=True)
        assert len(results) == 3
        ok = [r for r in results if isinstance(r, int) and not isinstance(r, bool)]
        busy = [r for r in results if isinstance(r, fr.RebuildBusy)]
        assert len(ok) == 1, f"应有且仅有 1 次成功，实际 {results}"
        assert len(busy) == 2, f"其余 2 次应被拒为 RebuildBusy，实际 {results}"
        assert _reset_index.doc_calls == 1, "只有一次真正调用了 embedding"

    @pytest.mark.asyncio
    async def test_failed_rebuild_does_not_hold_cooldown(self, _reset_index, monkeypatch):
        """失败不应占住冷却，否则管理员修完问题还得干等一分钟"""
        import ai.llm as llm_mod

        async def boom(texts):
            raise RuntimeError("gateway down")

        monkeypatch.setattr(llm_mod, "get_embeddings", lambda: type(
            "E", (), {"aembed_documents": staticmethod(boom)}
        )())
        with pytest.raises(RuntimeError):
            await fr.rebuild(ROWS)
        assert await fr.rebuild_cooldown_left() == 0

    @pytest.mark.asyncio
    async def test_stale_flag_cleared_after_rebuild(self, _reset_index):
        await fr.rebuild(ROWS)
        await fr.mark_stale("faq_changed")
        assert fr.stale_reason() == "faq_changed"
        assert (await fr.search_faq_detailed("预算"))[1] == "stale"
        fr._rebuild_locked_until = 0.0        # 解冷却，模拟重建按钮被再次点击
        await fr.rebuild(ROWS)
        assert fr.stale_reason() is None

    @pytest.mark.asyncio
    async def test_stale_blocks_untrusted_results(self, _reset_index):
        """索引过期时不返回结果——旧索引的命中不可信"""
        await fr.rebuild(ROWS)
        await fr.mark_stale("faq_changed")
        results, mode = await fr.search_faq_detailed("预算")
        assert results == [] and mode == "stale"

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


class _RaggedEmbeddings:
    """返回长度不一致的向量，模拟「换了 EMBEDDING_MODEL 但索引没重建」"""

    def __init__(self):
        self.n = 0

    async def aembed_documents(self, texts):
        out = []
        for _ in texts:
            self.n += 1
            out.append([1.0, 0.0] if self.n % 2 == 0 else [1.0, 0.0, 0.0, 0.0])
        return out

    async def aembed_query(self, text):
        return [1.0, 0.0, 0.0, 0.0]


class TestEmbeddingDimensionGuard:
    """维度守卫：宁可显式失败，也不静默截断算出错分数

    历史隐患：``zip(a, b)`` 遇长度不等会静默截断，相似度看起来正常实则全错。
    """

    @pytest.mark.asyncio
    async def test_rebuild_rejects_ragged_dimensions(self, monkeypatch):
        import ai.llm as llm_mod
        monkeypatch.setattr(llm_mod, "get_embeddings", lambda: _RaggedEmbeddings())
        with pytest.raises(ValueError, match="维度不一致"):
            await fr.rebuild(ROWS)
        assert fr.index_size() == 0, "维度不一致时不应留下半成品索引"

    @pytest.mark.asyncio
    async def test_rebuild_rejects_count_mismatch(self, monkeypatch):
        class ShortEmbeddings:
            async def aembed_documents(self, texts):
                return [[1.0, 0.0] for _ in texts][:-1]   # 少返回一条

            async def aembed_query(self, text):
                return [1.0, 0.0]

        import ai.llm as llm_mod
        monkeypatch.setattr(llm_mod, "get_embeddings", lambda: ShortEmbeddings())
        with pytest.raises(ValueError, match="条数不匹配"):
            await fr.rebuild(ROWS)
        assert fr.index_size() == 0

    @pytest.mark.asyncio
    async def test_search_skips_stale_index_entries(self, monkeypatch):
        """索引维度过期时该条被跳过，而不是用错分数返回结果"""
        await fr.rebuild(ROWS)                 # 正常维度
        import ai.llm as llm_mod

        # 伪造「索引是旧维度、query 是新维度」
        for it in fr._index:
            it["vector"] = [1.0, 0.0]         # 2 维
            it["vector_answer"] = [1.0, 0.0]

        class NewDimEmbeddings:
            async def aembed_documents(self, texts):
                return [[1.0, 0.0, 0.0, 0.0] for _ in texts]

            async def aembed_query(self, text):
                return [1.0, 0.0, 0.0, 0.0]

        monkeypatch.setattr(llm_mod, "get_embeddings", lambda: NewDimEmbeddings())
        fr._query_cache.clear()
        results, mode = await fr.search_faq_detailed("预算")
        assert results == [], "维度不匹配时不应返回任何结果"
        assert mode == "vector"

    @pytest.mark.asyncio
    async def test_cosine_raw_never_sees_mismatched_lengths(self, monkeypatch):
        """拦截 _cosine_raw，证明守卫在调用前就拦住了维度不匹配的条目

        为什么必须拦：zip() 截断是**静默**的。``_cosine_raw([1,0], [1,0,0])``
        实测返回 1.0（最大相似度）——换了模型维度后，旧索引会跟"完美命中"
        长得一模一样，肉眼和日志都看不出来。
        """
        await fr.rebuild(ROWS)
        for it in fr._index:                  # 伪造旧维度索引
            it["vector"] = [1.0, 0.0]
            it["vector_answer"] = [1.0, 0.0]

        import ai.llm as llm_mod

        class NewDimEmbeddings:
            async def aembed_documents(self, texts):
                return [[1.0, 0.0, 0.0, 0.0] for _ in texts]

            async def aembed_query(self, text):
                return [1.0, 0.0, 0.0, 0.0]

        monkeypatch.setattr(llm_mod, "get_embeddings", lambda: NewDimEmbeddings())
        fr._query_cache.clear()

        seen = []
        real = fr._cosine_raw

        def _spy(a, b):
            seen.append((len(a), len(b)))
            return real(a, b)

        monkeypatch.setattr(fr, "_cosine_raw", _spy)
        await fr.search_faq_detailed("预算")
        assert seen == [], f"维度不匹配时不应调用 _cosine_raw，实际调用了 {seen}"

    def test_zip_truncation_is_silently_wrong(self):
        """记录 zip 截断的具体危害：结果看起来是满分相似度"""
        assert fr._cosine_raw([1.0, 0.0], [1.0, 0.0, 0.0]) == 1.0
        # -> 换模型后旧索引会「完美命中」，故必须在调用前做长度守卫


class TestQueryDesensitized:
    """P0-3（审查报告缺陷 3）：FAQ 检索此前把用户原文直接交给 Embedding，
    用户可能直接输入手机号/卡号（如「退款的卡号怎么填」），PII 随之上云。
    入参必须先本地脱敏（占位符不影响相似度）。"""

    @pytest.mark.asyncio
    async def test_embed_query_masks_pii_before_cloud(self, monkeypatch):
        captured = {}

        class _CapturingEmbeddings:
            async def aembed_query(self, text):
                captured["text"] = text
                return [1.0, 0.0, 0.0, 0.0]

        import ai.llm as llm_mod
        monkeypatch.setattr(llm_mod, "get_embeddings", lambda: _CapturingEmbeddings())
        fr._query_cache.clear()

        await fr._embed_query("手机号 13800138000 怎么改绑定")

        assert "[PHONE]" in captured["text"]
        assert "13800138000" not in captured["text"], "PII 不得出现在上云的查询文本里"

    @pytest.mark.asyncio
    async def test_card_number_masked(self, monkeypatch):
        captured = {}

        class _CapturingEmbeddings:
            async def aembed_query(self, text):
                captured["text"] = text
                return [1.0, 0.0, 0.0, 0.0]

        import ai.llm as llm_mod
        monkeypatch.setattr(llm_mod, "get_embeddings", lambda: _CapturingEmbeddings())
        fr._query_cache.clear()

        await fr._embed_query("还信用卡 6222021234567890 逾期费怎么填")

        assert "[CARD]" in captured["text"]
        assert "6222021234567890" not in captured["text"]

    @pytest.mark.asyncio
    async def test_cache_key_normalized_on_masked_text(self, monkeypatch):
        """脱敏发生在 _cache_key 之前：两条脱敏后相同的原文只付一次 Embedding"""
        calls = {"n": 0}

        class _CountingEmbeddings:
            async def aembed_query(self, text):
                calls["n"] += 1
                return [1.0, 0.0, 0.0, 0.0]

        import ai.llm as llm_mod
        monkeypatch.setattr(llm_mod, "get_embeddings", lambda: _CountingEmbeddings())
        fr._query_cache.clear()

        await fr._embed_query("卡号 6222021234567890 绑定失败")
        await fr._embed_query("卡号 6222021234567891 绑定失败")

        assert calls["n"] == 1, "脱敏后文本相同，应命中同一缓存键（不会重复计费）"

    @pytest.mark.asyncio
    async def test_plain_query_unchanged(self, monkeypatch):
        """不误伤：无 PII 的普通问句原样上云"""
        captured = {}

        class _CapturingEmbeddings:
            async def aembed_query(self, text):
                captured["text"] = text
                return [1.0, 0.0, 0.0, 0.0]

        import ai.llm as llm_mod
        monkeypatch.setattr(llm_mod, "get_embeddings", lambda: _CapturingEmbeddings())
        fr._query_cache.clear()

        await fr._embed_query("预算怎么设置")
        assert captured["text"] == "预算怎么设置"
