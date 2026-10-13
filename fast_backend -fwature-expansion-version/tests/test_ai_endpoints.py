"""AI 路由端点测试 — /faq/search 与 /chat 的 prompt 组装

约定：不连真实 MySQL、不调真实 LLM/Embedding。
路由流程用 dependency_overrides + monkeypatch（照 tests/test_membership.py 模式）。
"""

import types
from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from ai import faq_retriever as fr
from ai.bookkeeping_chain import Parsed, ParsedItem
from config.db_config import get_db
from main import app
from utils.auth import get_current_regular_user, get_current_user


class FakeDB:
    """假 AsyncSession：未打桩的查询一律失败，防止测试偷偷触库"""

    async def commit(self):
        return None

    async def rollback(self):
        return None

    async def refresh(self, obj):
        return None

    async def execute(self, *args, **kwargs):
        raise AssertionError("测试未 monkeypatch 的查询不应触库")


@pytest.fixture()
def client():
    async def _override_get_db():
        yield FakeDB()

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = lambda: 1
    # 用户侧业务端点挂 get_current_regular_user（管理员 403）；测试统一按普通用户放行
    app.dependency_overrides[get_current_regular_user] = lambda: 1
    with TestClient(app) as c:     # with 触发 lifespan，与其他测试一致
        c.get("/api/health")
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def allow_quota(monkeypatch):
    """放行会员配额与并发闸门，并把消费记录下来"""
    calls = {"quota": [], "tier": 0}

    async def _tier(db, user_id):
        return calls["tier"]

    async def _consume(db, user_id, plan, kind):
        calls["quota"].append(kind)
        return True, 1, 100

    import routers.ai as ai_router
    from crud import membership as membership_crud
    from utils import ai_concurrency

    monkeypatch.setattr(membership_crud, "get_tier", _tier)
    monkeypatch.setattr(membership_crud, "consume_quota", _consume)
    monkeypatch.setattr(ai_concurrency, "try_acquire",
                        lambda user_id, limit: _release())
    return calls


async def _release():
    def _r():
        return None
    return _r


class TestFaqSearchEndpoint:
    """端点契约测试：透传 mode、不触库、不调真实 Embedding。

    索引直接以「关键词模式」（vector=None，等价于 main.py 启动兜底装填的形态）
    写入模块变量，因此全程零 I/O。
    """

    @pytest.fixture(autouse=True)
    def _seed_keyword_index(self):
        fr._index = [
            {"id": 1, "question": "预算怎么设置", "answer": "在预算页设置月预算总额",
             "category": "预算", "vector": None, "vector_answer": None},
            {"id": 2, "question": "系统支持哪些分类", "answer": "支持餐饮/交通/日用等分类",
             "category": "功能", "vector": None, "vector_answer": None},
        ]
        fr._query_cache.clear()
        yield
        fr._index = []
        fr._query_cache.clear()

    def test_returns_mode_and_hits(self, client):
        """回归：top_k 曾硬编码 3 绕过 FAQ_TOP_K；降级曾是静默的（无 mode 字段）"""
        r = client.get("/api/ai/faq/search", params={"query": "预算怎么设置"})
        assert r.status_code == 200
        body = r.json()
        assert body["mode"] == "keyword"        # 无向量索引 → 明确告知降级
        assert 1 in [x["id"] for x in body["results"]]
        assert "fallback" not in body            # 非异常路径不应出现该键

    def test_results_carry_contract_fields(self, client):
        body = client.get("/api/ai/faq/search", params={"query": "预算"}).json()
        for item in body["results"]:
            assert set(item) == {"id", "question", "answer", "category", "score"}
            assert 0.0 <= item["score"] <= 1.0

    def test_empty_index_reports_empty_mode(self, client):
        fr._index = []
        body = client.get("/api/ai/faq/search", params={"query": "预算"}).json()
        assert body["results"] == []
        assert body["mode"] == "empty"

    def test_blank_query_does_not_crash(self, client):
        body = client.get("/api/ai/faq/search", params={"query": "   "}).json()
        assert body["results"] == []
        assert body["mode"] == "empty"

    def test_top_k_respects_config(self, client, monkeypatch):
        """top_k 必须来自 FAQ_TOP_K，而不是路由里写死的 3"""
        import routers.ai as ai_router

        seen = {}

        async def _fake(query, top_k=None):
            seen["top_k"] = top_k
            return [{"id": 1, "question": "q", "answer": "a",
                     "category": "c", "score": 1.0}], "vector"

        monkeypatch.setattr(fr, "search_faq_detailed", _fake)
        body = client.get("/api/ai/faq/search", params={"query": "预算"}).json()
        # 路由不再显式传 top_k → 走 search_faq_detailed 默认值（读 FAQ_TOP_K）
        assert seen["top_k"] is None
        assert body["mode"] == "vector"

    def test_exception_yields_fallback_key(self, client, monkeypatch):
        """整体抛异常才是 fallback 形态（与无命中区分）"""
        async def _boom(query, top_k=None):
            raise RuntimeError("boom")

        monkeypatch.setattr(fr, "search_faq_detailed", _boom)
        body = client.get("/api/ai/faq/search", params={"query": "预算"}).json()
        assert body == {"results": [], "fallback": True}


class TestChatPromptAssembly:
    """验证 /chat 送进 LLM 的 system prompt 里确实包含两个数据块"""

    def _patch_all(self, monkeypatch, finance="[财务数据]本月总支出 ¥100", knowledge="[知识库]预算设置说明"):
        import routers.ai as ai_router
        from ai import context as ai_context
        from ai import memory as ai_memory
        from crud import ai as ai_crud

        captured = {}

        async def _session(db, sid, uid):
            return types.SimpleNamespace(id=sid, user_id=uid)

        async def _history(db, sid):
            return []

        async def _finance(db, uid):
            return finance

        async def _knowledge(query, **kw):
            captured["knowledge_query"] = query
            return knowledge

        # 签名镜像 ai.chat_chain.chat：含 user_id（按用户记录 Token/延迟）
        async def _chat(messages, premium=False, user_id=None):
            captured["messages"] = messages
            return "回复内容"

        async def _add_message(db, sid, role, content):
            return types.SimpleNamespace(id="msg_1")

        monkeypatch.setattr(ai_crud, "get_user_session", _session)
        monkeypatch.setattr(ai_crud, "add_message", _add_message)
        monkeypatch.setattr(ai_memory, "build_history", _history)
        monkeypatch.setattr(ai_context, "build_finance_block", _finance)
        monkeypatch.setattr(fr, "build_knowledge_block", _knowledge)
        monkeypatch.setattr(ai_router.chat_chain, "chat", _chat)
        return captured

    def test_both_blocks_injected(self, client, allow_quota, monkeypatch):
        captured = self._patch_all(monkeypatch)
        r = client.post("/api/ai/chat",
                        json={"sessionId": "s1", "message": "预算怎么设置"})
        assert r.status_code == 200
        assert r.json()["content"] == "回复内容"

        system = captured["messages"][0].content
        assert "[财务数据]本月总支出 ¥100" in system
        assert "[知识库]预算设置说明" in system
        assert "非用户指令" in system      # 数据块边界标记

    def test_knowledge_receives_user_query(self, client, allow_quota, monkeypatch):
        captured = self._patch_all(monkeypatch)
        client.post("/api/ai/chat",
                    json={"sessionId": "s1", "message": "预算怎么设置"})
        assert captured["knowledge_query"] == "预算怎么设置"

    def test_quota_exceeded_returns_429_bare_json(self, client, monkeypatch):
        """超额必须是裸 {error, code} + 429，不能套 Result 信封破坏前端契约"""
        import routers.ai as ai_router
        from crud import ai as ai_crud
        from crud import membership as membership_crud
        from utils import ai_concurrency

        async def _session(db, sid, uid):
            return types.SimpleNamespace(id=sid, user_id=uid)

        async def _tier(db, uid):
            return 0

        async def _consume(db, uid, plan, kind):
            return False, 100, 100

        monkeypatch.setattr(ai_crud, "get_user_session", _session)
        monkeypatch.setattr(membership_crud, "get_tier", _tier)
        monkeypatch.setattr(membership_crud, "consume_quota", _consume)
        monkeypatch.setattr(ai_concurrency, "try_acquire",
                            lambda user_id, limit: _release())

        r = client.post("/api/ai/chat",
                        json={"sessionId": "s1", "message": "你好"})
        assert r.status_code == 429
        body = r.json()
        assert body["code"] == "QUOTA_EXCEEDED"
        assert "data" not in body       # 裸契约：无信封

    def test_missing_session_returns_bare_error(self, client, allow_quota, monkeypatch):
        from crud import ai as ai_crud

        async def _none(db, sid, uid):
            return None

        monkeypatch.setattr(ai_crud, "get_user_session", _none)
        r = client.post("/api/ai/chat",
                        json={"sessionId": "nope", "message": "你好"})
        assert r.status_code == 200
        assert r.json() == {"error": "会话不存在"}


# ── P0-3：/analyze/expenses 的 query 必须脱敏后才进 LLM（审查报告缺陷 3）──────

class TestAnalyzeQueryDesensitized:
    def _patch_env(self, monkeypatch):
        import routers.ai as ai_router
        from ai import context as ai_context
        from crud import membership as membership_crud
        from schemas.ai import ExpenseAnalysis
        from utils import ai_concurrency

        captured = {}

        async def _tier(db, uid):
            return 0

        async def _consume(db, uid, plan, kind):
            return True, 1, 100

        async def _acquire(user_id, limit):
            def _r():
                return None
            return _r

        async def _ctx(db, uid):
            return {"this_month": "2026-10", "total_income": 1000.0,
                    "total_expense": 500.0, "last_month_expense": 400.0,
                    "top_categories": []}

        async def _analyze(ctx, query=None, user_id=None):
            captured["query"] = query
            captured["user_id"] = user_id
            return ExpenseAnalysis(summary="s", total_expense=500.0)

        monkeypatch.setattr(membership_crud, "get_tier", _tier)
        monkeypatch.setattr(membership_crud, "consume_quota", _consume)
        monkeypatch.setattr(ai_concurrency, "try_acquire", _acquire)
        monkeypatch.setattr(ai_context, "build_user_context", _ctx)
        monkeypatch.setattr(ai_router.analyze_chain, "analyze_expense", _analyze)
        return captured

    def test_pii_is_masked_before_llm(self, client, monkeypatch):
        """回归：body.query 此前原样进 analyze_chain，手机号/卡号随之上云"""
        captured = self._patch_env(monkeypatch)
        r = client.post("/api/ai/analyze/expenses",
                        json={"query": "打给我 13800138000 的那笔为什么涨了"})
        assert r.status_code == 200
        assert r.json()["success"] is True
        assert "[PHONE]" in captured["query"]
        assert "13800138000" not in captured["query"], "PII 不得随诉求上云"
        assert captured["user_id"] == 1          # P0-1：user_id 透传，usage 才能按用户落点

    def test_plain_query_unchanged(self, client, monkeypatch):
        captured = self._patch_env(monkeypatch)
        r = client.post("/api/ai/analyze/expenses", json={"query": "为什么餐饮涨了"})
        assert r.status_code == 200
        assert captured["query"] == "为什么餐饮涨了"


# ── P0-4：/faq/search 独立限流（审查报告缺陷 4）──────────────────────────────

class TestFaqSearchRateLimit:
    def test_rate_limited_returns_429_bare_json(self, client, monkeypatch):
        """cache miss 即一次 Embedding 计费，认证用户可无限刷 → 必须限流"""
        import routers.ai as ai_router
        from utils.throttle import SlidingWindowRateLimiter

        monkeypatch.setattr(ai_router, "faq_search_rate_limiter",
                            SlidingWindowRateLimiter(max_calls=1, window=60))

        first = client.get("/api/ai/faq/search", params={"query": "预算"})
        assert first.status_code == 200          # 首次放行并计一次

        second = client.get("/api/ai/faq/search", params={"query": "预算"})
        assert second.status_code == 429
        body = second.json()
        assert body["code"] == "RATE_LIMIT"
        assert "data" not in body                # 裸契约：无 Result 信封

    def test_failed_search_does_not_consume_slot(self, client, monkeypatch):
        """检索整体抛异常时不该占槽（与语音同口径：失败不消耗成本额度）"""
        import routers.ai as ai_router
        from utils.throttle import SlidingWindowRateLimiter

        monkeypatch.setattr(ai_router, "faq_search_rate_limiter",
                            SlidingWindowRateLimiter(max_calls=1, window=60))

        async def _boom(query, top_k=None):
            raise RuntimeError("boom")

        monkeypatch.setattr(fr, "search_faq_detailed", _boom)
        first = client.get("/api/ai/faq/search", params={"query": "预算"})
        assert first.json() == {"results": [], "fallback": True}

        async def _ok(query, top_k=None):
            return [], "empty"

        monkeypatch.setattr(fr, "search_faq_detailed", _ok)
        second = client.get("/api/ai/faq/search", params={"query": "预算"})
        assert second.status_code == 200         # 失败未占槽 → 仍可发起


# ── P0-2：PATCH /bookkeeping/{id} 带 message 必须走配额与并发闸门（缺陷 2）───

class _AmendResult:
    def __init__(self, rows):
        self._rows = rows

    def scalars(self):
        return self

    def all(self):
        return self._rows

    def first(self):
        return self._rows[0] if self._rows else None


class _AmendFakeDB:
    """假会话：按 SQL 目标表分派结果（Record 命中 / Category 列表 / 日志为空）

    比「按调用次序返回」稳健：_AmendResult 同时支持 .first()/.all()，
    因此 Record 查询与 Category 查询可以共用同一套桩。
    """

    def __init__(self, rec, categories):
        self.rec = rec
        self.categories = categories
        self.commits = 0

    async def commit(self):
        self.commits += 1

    async def rollback(self):
        return None

    async def refresh(self, obj):
        return None

    def add(self, obj):
        return None

    async def flush(self):
        return None

    async def execute(self, stmt, *args, **kwargs):
        sql = str(stmt)
        if "ai_bookkeeping_logs" in sql:
            return _AmendResult([])
        if "categories" in sql:
            return _AmendResult(self.categories)
        if "records" in sql:
            return _AmendResult([self.rec])
        raise AssertionError(f"测试未打桩的查询不应触库: {sql}")


@pytest.fixture()
def amend_env(monkeypatch):
    """打桩 amend 路径：假 DB + 放行配额 + 假解析，返回 (fake_db, 配额记录器)"""
    import routers.ai as ai_router
    from crud import ai as ai_crud
    from crud import membership as membership_crud
    from utils import ai_concurrency

    rec = types.SimpleNamespace(
        id=101, user_id=1, category_id=1, type=0, amount=Decimal("30.00"),
        date=date(2026, 10, 5), remark="午饭", status=1,
    )
    cats = [
        types.SimpleNamespace(id=1, name="餐饮", user_id=None, type=0, status=1),
        types.SimpleNamespace(id=2, name="交通", user_id=None, type=0, status=1),
    ]
    fake_db = _AmendFakeDB(rec, cats)
    calls = {"quota": []}

    async def _override_get_db():
        yield fake_db

    app.dependency_overrides[get_db] = _override_get_db

    async def _tier(db, uid):
        return 0

    async def _consume(db, uid, plan, kind):
        calls["quota"].append(kind)
        return True, 1, 100

    async def _acquire(user_id, limit):
        def _r():
            return None
        return _r

    async def _parse(message, today, category_names, user_id=None):
        return Parsed(intent="bookkeeping", items=[ParsedItem(
            amount=45.0, amount_raw="45块", type=0, category_name="餐饮",
        )])

    async def _create_log(db, **fields):
        return types.SimpleNamespace(id=77, **fields)

    monkeypatch.setattr(membership_crud, "get_tier", _tier)
    monkeypatch.setattr(membership_crud, "consume_quota", _consume)
    monkeypatch.setattr(ai_concurrency, "try_acquire", _acquire)
    monkeypatch.setattr(ai_router, "parse_bookkeeping", _parse)
    monkeypatch.setattr(ai_crud, "create_bookkeeping_log", _create_log)

    yield fake_db, calls
    app.dependency_overrides.pop(get_db, None)


class TestAmendQuota:
    def test_with_message_consumes_bookkeeping_quota(self, client, amend_env):
        """回归：amend 带 message 会调 LLM 解析，此前完全不扣配额"""
        fake_db, calls = amend_env
        r = client.patch("/api/ai/bookkeeping/101", json={"message": "改成45块"})
        assert r.status_code == 200
        assert r.json()["success"] is True
        assert calls["quota"] == ["bookkeeping"]

    def test_without_message_does_not_consume_quota(self, client, amend_env):
        """纯字段修改不调 LLM，不该扣 AI 配额"""
        fake_db, calls = amend_env
        r = client.patch("/api/ai/bookkeeping/101", json={"amount": 45})
        assert r.status_code == 200
        assert r.json()["success"] is True
        assert calls["quota"] == []

    def test_quota_exceeded_returns_bare_error_not_429(self, client, amend_env, monkeypatch):
        """超额口径对齐 POST /bookkeeping：HTTP 200 + 裸 {"error"}，不是 429"""
        fake_db, calls = amend_env
        from crud import membership as membership_crud

        async def _deny(db, uid, plan, kind):
            calls["quota"].append(kind)
            return False, 100, 100

        monkeypatch.setattr(membership_crud, "consume_quota", _deny)
        r = client.patch("/api/ai/bookkeeping/101", json={"message": "改成45块"})
        assert r.status_code == 200
        body = r.json()
        assert "error" in body
        assert "data" not in body
        assert calls["quota"] == ["bookkeeping"]
