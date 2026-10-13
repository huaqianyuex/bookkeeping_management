"""上游网关重试与错误文案测试（审查报告 P1-6）

背景
----
Agnes 网关在模型过载时返回 ``HTTP 429 + code 1305「该模型当前访问量过大，请稍后再试」``。
改造前只靠 SDK 一次约 0.5s 的重试，实际等于不重试，于是：

- 记账链把 429 兜成「记账解析失败，请换个说法再试」——用户白改说法；
- 对话链 SSE 首字节前 429 直接报错。

本文件锁住四组性质：
1. **分类**：只重试瞬时故障（连接/超时/429/5xx），4xx 不重试；能识别「上游过载」。
2. **退避策略**：指数退避 + 抖动、尊重 Retry-After、受总预算约束、次数用尽即抛。
3. **流式只重试首字节之前**：已 yield 过内容绝不重试（不重复输出、不重复计费）。
4. **文案归因**：上游过载提示「稍后重试」，其它解析失败才提示「换个说法」。

全部用构造的异常与假 LLM，不产生任何真实上游调用。
"""

import types
from datetime import date

import httpx
import openai
import pytest
from fastapi.testclient import TestClient
from langchain_openai.chat_models import base as lc_openai

from ai import chat_chain
from ai import retry
from ai.bookkeeping_chain import Parsed, ParsedItem
from config.db_config import get_db
from main import app
from routers import ai as ai_router
from utils.auth import get_current_regular_user

GW_URL = "https://gw.invalid/v1/chat/completions"


def _resp(code: int, headers: dict | None = None) -> httpx.Response:
    return httpx.Response(code, request=httpx.Request("POST", GW_URL),
                          headers=headers, json={})


def _status_error(code: int, headers: dict | None = None) -> openai.APIStatusError:
    return openai.APIStatusError("boom", response=_resp(code, headers), body=None)


def _json_429(headers: dict | None = None) -> openai.RateLimitError:
    return openai.RateLimitError("busy", response=_resp(429, headers), body=None)


@pytest.fixture()
def no_sleep(monkeypatch):
    """把退避 sleep 换成立即返回并记录时长，测试不真的等"""
    delays: list[float] = []

    async def _sleep(seconds):
        delays.append(seconds)

    import ai.chat_chain as cc
    monkeypatch.setattr(retry, "asyncio", types.SimpleNamespace(sleep=_sleep))
    monkeypatch.setattr(cc, "asyncio", types.SimpleNamespace(sleep=_sleep))
    return delays


# ---------------------------------------------------------------------------
# 1. 分类
# ---------------------------------------------------------------------------
class TestClassifier:
    @pytest.mark.parametrize("code", [408, 409, 429, 500, 502, 503, 504])
    def test_retryable_status(self, code):
        assert retry.is_retryable(_status_error(code)) is True

    @pytest.mark.parametrize("code", [400, 401, 403, 404, 422])
    def test_client_errors_are_not_retryable(self, code):
        """4xx 是请求自身的问题，重试只会白跑并放大计费"""
        assert retry.is_retryable(_status_error(code)) is False

    def test_connection_errors_are_retryable(self):
        assert retry.is_retryable(httpx.ConnectError("boom")) is True
        assert retry.is_retryable(openai.APITimeoutError(
            request=httpx.Request("POST", GW_URL))) is True

    def test_plain_exception_is_not_retryable(self):
        assert retry.is_retryable(RuntimeError("落库失败")) is False

    def test_langchain_wrapped_error_is_recognized(self):
        """真实链路抛的是 langchain_openai 包装类（见线上 traceback），必须认识"""
        wrapped = lc_openai.OpenAIRateLimitError("busy", response=_resp(429), body=None)
        assert retry.is_retryable(wrapped) is True
        assert retry.is_upstream_busy(wrapped) is True

    def test_upstream_busy_covers_429_and_5xx_only(self):
        assert retry.is_upstream_busy(_json_429()) is True
        assert retry.is_upstream_busy(_status_error(503)) is True
        assert retry.is_upstream_busy(_status_error(400)) is False
        # 超时不算「繁忙」：应提示服务不可用，而不是让用户等模型排队
        assert retry.is_upstream_busy(
            openai.APITimeoutError(request=httpx.Request("POST", GW_URL))
        ) is False
        assert retry.is_upstream_busy(RuntimeError("x")) is False


# ---------------------------------------------------------------------------
# 2. 退避策略
# ---------------------------------------------------------------------------
class TestWithRetry:
    @pytest.mark.asyncio
    async def test_succeeds_after_transient_failures(self, no_sleep):
        calls = {"n": 0}

        async def fn():
            calls["n"] += 1
            if calls["n"] < 3:
                raise _json_429()
            return "ok"

        assert await retry.with_retry(fn) == "ok"
        assert calls["n"] == 3
        assert len(no_sleep) == 2, "两次失败各退避一次"

    @pytest.mark.asyncio
    async def test_non_retryable_fails_fast(self, no_sleep):
        calls = {"n": 0}

        async def fn():
            calls["n"] += 1
            raise _status_error(400)

        with pytest.raises(openai.APIStatusError):
            await retry.with_retry(fn)
        assert calls["n"] == 1, "4xx 不应重试"
        assert no_sleep == []

    @pytest.mark.asyncio
    async def test_exhausts_attempts_then_raises(self, no_sleep):
        calls = {"n": 0}

        async def fn():
            calls["n"] += 1
            raise _json_429()

        with pytest.raises(openai.RateLimitError):
            await retry.with_retry(fn)
        assert calls["n"] == retry.max_attempts() == 3

    @pytest.mark.asyncio
    async def test_backoff_is_exponential(self, no_sleep):
        async def fn():
            raise _json_429()

        with pytest.raises(openai.RateLimitError):
            await retry.with_retry(fn)
        # 0.8 → 1.6，±25% 抖动
        assert 0.6 <= no_sleep[0] <= 1.0, no_sleep
        assert 1.2 <= no_sleep[1] <= 2.0, no_sleep

    @pytest.mark.asyncio
    async def test_respects_retry_after_header(self, no_sleep):
        async def fn():
            raise _json_429(headers={"retry-after": "2"})

        with pytest.raises(openai.RateLimitError):
            await retry.with_retry(fn)
        assert 1.5 <= no_sleep[0] <= 2.5, "首跳应采纳上游 Retry-After"

    @pytest.mark.asyncio
    async def test_total_budget_caps_retries(self, monkeypatch, no_sleep):
        """总预算极小 → 直接失败，不把请求拖过前端 timeout"""
        monkeypatch.setattr(retry.settings, "LLM_RETRY_TOTAL_BUDGET_SECONDS", 0.0)
        calls = {"n": 0}

        async def fn():
            calls["n"] += 1
            raise _json_429()

        with pytest.raises(openai.RateLimitError):
            await retry.with_retry(fn)
        assert calls["n"] == 1, "超预算即放弃重试"
        assert no_sleep == []

    @pytest.mark.asyncio
    async def test_no_retry_when_single_attempt_configured(self, monkeypatch, no_sleep):
        monkeypatch.setattr(retry.settings, "LLM_MAX_RETRIES", 0)
        calls = {"n": 0}

        async def fn():
            calls["n"] += 1
            raise _json_429()

        with pytest.raises(openai.RateLimitError):
            await retry.with_retry(fn)
        assert calls["n"] == 1

    def test_attempts_and_budget_read_from_settings(self, monkeypatch):
        monkeypatch.setattr(retry.settings, "LLM_MAX_RETRIES", 4)
        monkeypatch.setattr(retry.settings, "LLM_RETRY_TOTAL_BUDGET_SECONDS", 12.5)
        assert retry.max_attempts() == 5
        assert retry.total_budget() == 12.5


# ---------------------------------------------------------------------------
# 3. 流式：只重试首字节之前
# ---------------------------------------------------------------------------
class _Chunk:
    def __init__(self, content):
        self.content = content
        self.usage_metadata = None
        self.response_metadata = {}


class _ScriptedStreamLLM:
    """按脚本逐次 astream：脚本项是 chunk 列表或要抛出的异常"""

    model_name = "scripted"

    def __init__(self, scripts):
        self.scripts = scripts
        self.calls = 0

    async def astream(self, messages):
        script = self.scripts[min(self.calls, len(self.scripts) - 1)]
        self.calls += 1
        if isinstance(script, Exception):
            raise script
        for chunk in script:
            if isinstance(chunk, Exception):
                # 列表里夹异常 = 「已产出部分内容后流中断」
                raise chunk
            yield chunk


async def _collect(agen):
    out = []
    async for piece in agen:
        out.append(piece)
    return out


class TestStreamFirstByteOnly:
    @pytest.mark.asyncio
    async def test_retries_before_first_byte(self, monkeypatch, no_sleep):
        llm = _ScriptedStreamLLM([_json_429(), [_Chunk("你好")]])
        monkeypatch.setattr(chat_chain, "get_chat_llm", lambda premium=False: llm)

        assert await _collect(chat_chain.chat_stream([], user_id=1)) == ["你好"]
        assert llm.calls == 2, "首字节前应重试一次"
        assert len(no_sleep) == 1

    @pytest.mark.asyncio
    async def test_never_retries_after_output(self, monkeypatch, no_sleep):
        """已吐出内容再重试 = 用户看到重复文本 + 上游重复计费"""
        llm = _ScriptedStreamLLM([[_Chunk("部分内容"), _json_429()]])
        monkeypatch.setattr(chat_chain, "get_chat_llm", lambda premium=False: llm)

        got = []
        with pytest.raises(openai.RateLimitError):
            async for piece in chat_chain.chat_stream([], user_id=1):
                got.append(piece)

        assert got == ["部分内容"], "已产出的内容不应被重放"
        assert llm.calls == 1, "已 yield 过内容后不得再次调用上游"
        assert no_sleep == []

    @pytest.mark.asyncio
    async def test_non_retryable_error_before_first_byte(self, monkeypatch, no_sleep):
        llm = _ScriptedStreamLLM([_status_error(400)])
        monkeypatch.setattr(chat_chain, "get_chat_llm", lambda premium=False: llm)

        with pytest.raises(openai.APIStatusError):
            await _collect(chat_chain.chat_stream([], user_id=1))
        assert llm.calls == 1

    @pytest.mark.asyncio
    async def test_stream_usage_chunk_still_recorded_after_retry(self, monkeypatch, no_sleep):
        """重试后成功也要正常记 token（P1-5 不打折）"""
        from ai import observability as obs
        obs.recorder.reset()
        usage_chunk = _Chunk("")
        usage_chunk.usage_metadata = {"input_tokens": 9, "output_tokens": 4}
        llm = _ScriptedStreamLLM([_json_429(), [_Chunk("好"), usage_chunk]])
        monkeypatch.setattr(chat_chain, "get_chat_llm", lambda premium=False: llm)

        assert await _collect(chat_chain.chat_stream([], user_id=77)) == ["好"]
        row = obs.recorder.snapshot()[obs.KIND_CHAT]["77"]
        assert row["promptTokens"] == 9 and row["completionTokens"] == 4
        obs.recorder.reset()


# ---------------------------------------------------------------------------
# 4. 文案归因（路由层）
# ---------------------------------------------------------------------------
class FakeDB:
    def __init__(self):
        self._added = []
        self._next_id = 101

    async def commit(self):
        return None

    async def rollback(self):
        return None

    async def refresh(self, obj):
        return None

    def add(self, obj):
        self._added.append(obj)

    async def flush(self):
        for obj in self._added:
            if getattr(obj, "id", None) is None:
                obj.id = self._next_id
                self._next_id += 1

    async def execute(self, *args, **kwargs):
        cats = [
            types.SimpleNamespace(id=1, name="餐饮", user_id=None, type=0, status=1),
            types.SimpleNamespace(id=9, name="其他", user_id=None, type=0, status=1),
        ]

        class _R:
            def scalars(self):
                return self

            def all(self):
                return cats

            def first(self):
                return None

        return _R()


class _FakeSessionCtx:
    def __init__(self, db):
        self.db = db

    async def __aenter__(self):
        return self.db

    async def __aexit__(self, *exc):
        return False


@pytest.fixture()
def env(monkeypatch):
    """最小打桩：假 DB + 放行配额/并发 + 假会话查询"""
    from crud import ai as ai_crud
    from crud import membership as membership_crud
    from utils import ai_concurrency

    db = FakeDB()
    state = {"updated": []}

    async def _override_get_db():
        yield db

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_regular_user] = lambda: 1

    async def _tier(d, uid):
        return 0

    async def _consume(d, uid, plan, kind):
        return True, 1, 100

    async def _acquire(uid, limit):
        def _release():
            return None
        return _release

    async def _session(d, sid, uid):
        return types.SimpleNamespace(id=sid, user_id=uid)

    async def _create_log(d, **fields):
        return types.SimpleNamespace(id=77, **fields)

    async def _update_log(d, log_id, **fields):
        state["updated"].append({"id": log_id, **fields})
        return None

    async def _history(d, sid):
        return []

    async def _finance(d, uid):
        return ""

    async def _add_message(d, sid, role, content):
        return types.SimpleNamespace(id="msg_1")

    async def _no_log(d, uid, client_msg_id):
        return None

    async def _no_recent(d, uid, dedup_hash, window):
        return None

    monkeypatch.setattr(membership_crud, "get_tier", _tier)
    monkeypatch.setattr(membership_crud, "consume_quota", _consume)
    monkeypatch.setattr(ai_concurrency, "try_acquire", _acquire)
    monkeypatch.setattr(ai_crud, "get_user_session", _session)
    monkeypatch.setattr(ai_crud, "create_bookkeeping_log", _create_log)
    monkeypatch.setattr(ai_crud, "update_bookkeeping_log", _update_log)
    monkeypatch.setattr(ai_crud, "add_message", _add_message)
    monkeypatch.setattr(ai_crud, "find_recent_by_dedup", _no_recent)
    monkeypatch.setattr(ai_crud, "find_log_by_client_msg", _no_log)
    monkeypatch.setattr(ai_router, "AsyncSessionLocal", lambda: _FakeSessionCtx(db))
    monkeypatch.setattr(ai_router.memory, "build_history", _history)
    monkeypatch.setattr(ai_router.ai_context, "build_finance_block", _finance)

    with TestClient(app) as c:
        c.get("/api/health")
        yield c, state
    app.dependency_overrides.clear()


class TestRouterUpstreamMessaging:
    def test_bookkeeping_reports_busy_not_wrong_wording(self, env, monkeypatch):
        """回归：429 曾被报成「解析失败，请换个说法」，把上游故障甩给用户"""
        client, state = env

        async def _busy(message, today, category_names, user_id=None):
            raise _json_429()

        monkeypatch.setattr(ai_router, "parse_bookkeeping", _busy)
        body = client.post("/api/ai/bookkeeping", json={"message": "午饭35块"}).json()

        assert "繁忙" in body["error"]
        assert "换个说法" not in body["error"]
        assert body["code"] == "UPSTREAM_BUSY"
        assert state["updated"][0]["error_msg"].startswith("upstream_busy:")

    def test_bookkeeping_keeps_hint_for_real_parse_failure(self, env, monkeypatch):
        client, state = env

        async def _parse(message, today, category_names, user_id=None):
            raise ValueError("模型返回了非法 JSON")

        monkeypatch.setattr(ai_router, "parse_bookkeeping", _parse)
        body = client.post("/api/ai/bookkeeping", json={"message": "午饭35块"}).json()

        assert "换个说法" in body["error"]
        assert state["updated"][0]["error_msg"].startswith("parse:")

    def test_non_stream_chat_carries_busy_code(self, env, monkeypatch):
        client, _ = env

        async def _busy(messages, premium=False, user_id=None):
            raise _json_429()

        monkeypatch.setattr(ai_router.chat_chain, "chat", _busy)
        body = client.post("/api/ai/chat",
                           json={"sessionId": "s1", "message": "你好"}).json()

        assert body["code"] == "UPSTREAM_BUSY"
        assert "繁忙" in body["error"]

    def test_stream_chat_carries_busy_code(self, env, monkeypatch):
        client, _ = env

        async def _busy_stream(messages, premium=False, user_id=None):
            raise _json_429()
            yield  # pragma: no cover - 使其成为 async generator

        monkeypatch.setattr(ai_router.chat_chain, "chat_stream", _busy_stream)
        res = client.post("/api/ai/chat/stream",
                          json={"sessionId": "s1", "message": "你好"})

        assert res.status_code == 200         # SSE 保持 200 契约
        assert "UPSTREAM_BUSY" in res.text
        assert "繁忙" in res.text

    def test_llm_clients_disable_sdk_retry(self):
        """两层重试相乘会把一次请求放大成 N×M 次上游调用——SDK 侧必须关掉"""
        import inspect

        from ai import llm

        src = inspect.getsource(llm)
        assert src.count("max_retries=0") >= 2, "chat / analyze 客户端都应关闭 SDK 重试"