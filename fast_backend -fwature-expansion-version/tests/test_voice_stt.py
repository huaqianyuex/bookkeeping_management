"""语音记账测试 — STT 识别层（M1）+ 落库衔接（M2）

规格：docs/语音记账实施指南.md §2.5 / §5。
约定：不连真实 MySQL。路由流程用 dependency_overrides + monkeypatch
（照 tests/test_membership.py 模式），STT provider 注入假实现，纯逻辑用普通断言。
"""

import time
from collections import deque
from datetime import date
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from ai import stt
from ai.bookkeeping_chain import Parsed, ParsedItem
from config.db_config import get_db
from crud import ai as ai_crud
from crud import membership as membership_crud
from main import app
from routers import ai as ai_router
from utils.auth import get_current_regular_user, get_current_user
from utils.throttle import SlidingWindowRateLimiter


class FakeDB:
    """假 AsyncSession：add/flush 模拟自增主键；execute 只放行 Category 查询"""

    def __init__(self, categories):
        self._categories = categories
        self._added = []
        self._next_id = 101
        self.commits = 0

    async def commit(self):
        self.commits += 1

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
        categories = self._categories

        class _Result:
            def scalars(self):
                return self

            def all(self):
                return categories

            def first(self):
                return None

            def scalar_one_or_none(self):
                return None

        return _Result()


def _categories():
    return [
        SimpleNamespace(id=1, name="餐饮", user_id=None, type=0, status=1),
        SimpleNamespace(id=2, name="交通", user_id=None, type=0, status=1),
        SimpleNamespace(id=9, name="其他", user_id=None, type=0, status=1),
    ]


def _patch_quota(monkeypatch, admitted=True):
    async def _fake_tier(db, user_id):
        return 0

    async def _fake_consume(db, user_id, plan, kind):
        assert kind == "bookkeeping"
        return admitted, 1, 5

    monkeypatch.setattr(membership_crud, "get_tier", _fake_tier)
    monkeypatch.setattr(membership_crud, "consume_quota", _fake_consume)


@pytest.fixture()
def client():
    async def _override_get_db():
        yield FakeDB(_categories())

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = lambda: 1
    # 用户侧业务端点挂 get_current_regular_user（管理员 403）；测试统一按普通用户放行
    app.dependency_overrides[get_current_regular_user] = lambda: 1
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


class _FakeProvider:
    async def transcribe(self, audio_bytes: bytes, filename: str) -> stt.SttResult:
        return stt.SttResult(text="今天打车花了18块", language="zh", confidence=0.92)


class _BoomProvider:
    async def transcribe(self, audio_bytes: bytes, filename: str) -> stt.SttResult:
        raise RuntimeError("provider down")


# 带真实魔数的假音频：服务端会校验内容签名（改后缀的任意字节会被拒）
FAKE_M4A = b"\x00\x00\x00\x20ftypM4A \x00\x00\x00\x00" + b"\x00" * 16
FAKE_WEBM = b"\x1a\x45\xdf\xa3\x42\x86\x81\x01\x42\xf7\x81\x01"


# ---------------------------------------------------------------------------
# 1. 纯单元：SlidingWindowRateLimiter（放行型限流，区别于 LoginThrottle 的失败锁定）
# ---------------------------------------------------------------------------
class TestSlidingWindowRateLimiter:
    def test_allows_within_max_calls_then_blocks(self):
        limiter = SlidingWindowRateLimiter(max_calls=3, window=60)
        for _ in range(3):
            ok, wait = limiter.allow("u1")
            assert ok and wait == 0
        ok, wait = limiter.allow("u1")
        assert not ok and wait > 0

    def test_keys_are_independent(self):
        limiter = SlidingWindowRateLimiter(max_calls=1, window=60)
        assert limiter.allow("a")[0]
        assert not limiter.allow("a")[0]
        assert limiter.allow("b")[0]

    def test_window_expiry_frees_slot(self):
        limiter = SlidingWindowRateLimiter(max_calls=1, window=60)
        assert limiter.allow("u1")[0]
        assert not limiter.allow("u1")[0]
        # 窗口整体滑出：只剩一条窗口外的旧命中，应被清除并重新放行
        limiter._hits["u1"] = deque([time.time() - 61])
        ok, wait = limiter.allow("u1")
        assert ok and wait == 0


# ---------------------------------------------------------------------------
# 2. /api/ai/voice/config — 开关下发
# ---------------------------------------------------------------------------
class TestVoiceConfig:
    def test_routes_registered(self):
        paths = {r.path for r in app.routes}
        assert "/api/ai/voice/config" in paths
        assert "/api/ai/voice/transcribe" in paths

    def test_config_returns_switch_and_limit(self, client):
        res = client.get("/api/ai/voice/config")
        assert res.status_code == 200
        body = res.json()
        assert body["enabled"] is True
        assert body["maxSeconds"] > 0


# ---------------------------------------------------------------------------
# 3. /api/ai/voice/transcribe — 校验链与 provider 注入
# ---------------------------------------------------------------------------
@pytest.fixture()
def stt_client(client, monkeypatch):
    """transcribe 专用：每例换新限流器，避免用例间共享窗口计数"""
    monkeypatch.setattr(ai_router, "voice_rate_limiter", SlidingWindowRateLimiter(max_calls=50, window=60))
    return client


def test_transcribe_requires_auth(monkeypatch):
    async def _override_get_db():
        yield FakeDB(_categories())

    app.dependency_overrides[get_db] = _override_get_db   # 只放 DB，鉴权走真实现
    try:
        with TestClient(app) as c:
            res = c.post(
                "/api/ai/voice/transcribe",
                files={"file": ("a.m4a", b"x", "audio/m4a")},
                headers={"Authorization": "Bearer not-a-jwt"},
            )
        assert res.status_code == 401
    finally:
        app.dependency_overrides.clear()


def test_transcribe_rejects_bad_ext(stt_client):
    res = stt_client.post(
        "/api/ai/voice/transcribe",
        files={"file": ("a.txt", b"x", "text/plain")},
    )
    assert res.status_code == 200
    assert "不支持" in res.json()["error"]


def test_transcribe_rejects_empty_audio(stt_client):
    res = stt_client.post(
        "/api/ai/voice/transcribe",
        files={"file": ("a.m4a", b"", "audio/m4a")},
    )
    assert res.status_code == 200
    assert "音频内容为空" in res.json()["error"]


def test_transcribe_rejects_oversize(stt_client, monkeypatch):
    monkeypatch.setattr(ai_router, "STT_MAX_SIZE_MB", 1)
    res = stt_client.post(
        "/api/ai/voice/transcribe",
        files={"file": ("a.mp3", b"x" * (1024 * 1024 + 1), "audio/mpeg")},
    )
    assert res.status_code == 200
    assert "音频过大" in res.json()["error"]


def test_transcribe_disabled_switch(stt_client, monkeypatch):
    monkeypatch.setattr(ai_router, "STT_ENABLED", False)
    res = stt_client.post(
        "/api/ai/voice/transcribe",
        files={"file": ("a.m4a", b"x", "audio/m4a")},
    )
    assert res.status_code == 200
    assert "语音识别未启用" in res.json()["error"]


def test_transcribe_rate_limited(stt_client, monkeypatch):
    saturated = SlidingWindowRateLimiter(max_calls=1, window=60)
    saturated.allow("voice:1")
    monkeypatch.setattr(ai_router, "voice_rate_limiter", saturated)
    res = stt_client.post(
        "/api/ai/voice/transcribe",
        files={"file": ("a.m4a", FAKE_M4A, "audio/m4a")},
    )
    assert res.status_code == 200
    assert "说话太频繁" in res.json()["error"]


def test_transcribe_rejects_fake_magic(stt_client):
    """任意字节改后缀 .mp3：Content-Type/扩展名可伪造，魔数不符必须拒绝，
    否则白耗外部 ASR 计费"""
    res = stt_client.post(
        "/api/ai/voice/transcribe",
        files={"file": ("a.mp3", b"this-is-not-audio" * 8, "audio/mpeg")},
    )
    assert res.status_code == 200
    assert "格式不符" in res.json()["error"]


def test_transcribe_happy_path_webm(stt_client, monkeypatch):
    """H5 MediaRecorder 产出 webm/opus：白名单必须放行（实施指南 §0 修正 4）"""
    monkeypatch.setattr(stt, "_provider", _FakeProvider())
    res = stt_client.post(
        "/api/ai/voice/transcribe",
        files={"file": ("audio.webm", FAKE_WEBM, "audio/webm")},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["text"] == "今天打车花了18块"
    assert body["language"] == "zh"
    assert body["confidence"] == 0.92


def test_transcribe_provider_not_configured(stt_client, monkeypatch):
    monkeypatch.setattr(ai_router, "STT_ENABLED", True)
    monkeypatch.setattr(stt, "STT_ENABLED", False)   # get_stt_provider 内部判定
    monkeypatch.setattr(stt, "_provider", None)
    res = stt_client.post(
        "/api/ai/voice/transcribe",
        files={"file": ("a.m4a", FAKE_M4A, "audio/m4a")},
    )
    assert res.status_code == 200
    assert "语音识别未启用" in res.json()["error"]


def test_transcribe_provider_error_masked(stt_client, monkeypatch):
    """底层异常不回显（可能含 URL/key 提示），只给通用文案"""
    monkeypatch.setattr(stt, "_provider", _BoomProvider())
    res = stt_client.post(
        "/api/ai/voice/transcribe",
        files={"file": ("a.m4a", FAKE_M4A, "audio/m4a")},
    )
    assert res.status_code == 200
    assert "语音识别暂不可用" in res.json()["error"]


def test_transcribe_confidence_proxy_from_segments():
    from ai.stt import _confidence_from_segments

    payload = {"segments": [{"avg_logprob": -0.2, "no_speech_prob": 0.1}]}
    conf = _confidence_from_segments(payload)
    assert conf is not None and 0 < conf < 1
    assert _confidence_from_segments({"segments": []}) is None


# ---------------------------------------------------------------------------
# 4. M2 落库衔接：overrides 按 index 定位 + source 落审计
# ---------------------------------------------------------------------------
@pytest.fixture()
def bookkeeping_env(client, monkeypatch):
    """打桩 LLM 解析 + 日志读写 + 配额，返回 (FakeDB, 记录器)"""
    fake_db = FakeDB(_categories())

    async def _override_get_db():
        yield fake_db

    app.dependency_overrides[get_db] = _override_get_db

    created_logs: list[dict] = []
    updated_logs: list[dict] = []

    async def _fake_create_log(db, **fields):
        created_logs.append(fields)
        return SimpleNamespace(id=77, **fields)

    async def _fake_update_log(db, log_id, **fields):
        updated_logs.append({"id": log_id, **fields})
        return None

    monkeypatch.setattr(ai_crud, "create_bookkeeping_log", _fake_create_log)
    monkeypatch.setattr(ai_crud, "update_bookkeeping_log", _fake_update_log)
    _patch_quota(monkeypatch)

    yield fake_db, created_logs, updated_logs
    app.dependency_overrides.pop(get_db, None)


def _patch_parse(monkeypatch, items, intent="bookkeeping"):
    # 签名必须镜像 ai.bookkeeping_chain.parse_bookkeeping 的真实签名：
    # 4th 参数 user_id 用于按用户维度记录 Token/延迟用量（ai/observability.py）。
    async def _fake_parse(message, today, category_names, user_id=None):
        return Parsed(intent=intent, items=items)

    monkeypatch.setattr(ai_router, "parse_bookkeeping", _fake_parse)


class TestBookkeepingOverrides:
    def test_override_lands_on_right_item_and_source_persisted(self, bookkeeping_env, monkeypatch):
        """验收 #10：第 2 笔缺金额，用 overrides[index=1] 补金额+分类，必须落在第 2 笔上"""
        fake_db, created_logs, updated_logs = bookkeeping_env
        _patch_parse(monkeypatch, [
            ParsedItem(amount=30.0, amount_raw="30块", type=0, category_name="餐饮", remark="午饭"),
            ParsedItem(amount=None, amount_raw=None, type=0, category_name="交通", remark="晚饭"),
        ])
        res = TestClient(app).post(
            "/api/ai/bookkeeping",
            json={
                "message": "午饭花了30块，晚饭99",
                "clientMsgId": "cm-voice-1",
                "source": "voice",
                "overrides": [{"index": 1, "amount": 99, "categoryId": 2}],
            },
        )
        assert res.status_code == 200
        body = res.json()
        assert body["action"] == "created"
        assert [r["amount"] for r in body["records"]] == [30.0, 99.0]
        assert [r["categoryId"] for r in body["records"]] == [1, 2]
        assert body["totalAmount"] == 129.0
        # source 列落库为 voice；parse_json 带 overrides 审计
        assert created_logs[0]["source"] == "voice"
        assert updated_logs[0]["parse_json"]["_applied_overrides"][0]["index"] == 1
        # Record 落库：index 对齐（第 2 条才是 override 的 99/交通）
        amounts = [(float(r.amount), r.category_id, r.remark) for r in fake_db._added]
        assert amounts == [(30.0, 1, "午饭"), (99.0, 2, "晚饭")]

    def test_dry_run_preview_has_index_and_warnings(self, bookkeeping_env, monkeypatch):
        fake_db, created_logs, updated_logs = bookkeeping_env
        _patch_parse(monkeypatch, [
            ParsedItem(amount=12.0, amount_raw="12块", type=0, category_name="剪头发"),
        ])
        res = TestClient(app).post(
            "/api/ai/bookkeeping",
            json={"message": "剪头发12块", "dryRun": True},
        )
        assert res.status_code == 200
        body = res.json()
        assert body["action"] == "preview"
        assert body["preview"]["items"][0]["index"] == 0
        # 「剪头发」不在分类表也不在别名词典 → 归入「其他」并给 warning
        assert any("其他" in w for w in body["warnings"])
        assert created_logs == []        # dry_run 不写日志
        assert fake_db._added == []      # dry_run 不入账

    def test_override_category_type_mismatch_rejected(self, bookkeeping_env, monkeypatch):
        """override 分类与收支类型不一致 → 拒绝（对齐 amend 口径）"""
        _patch_parse(monkeypatch, [
            ParsedItem(amount=30.0, amount_raw="30块", type=0, category_name="餐饮"),
        ])
        res = TestClient(app).post(
            "/api/ai/bookkeeping",
            json={
                "message": "吃饭30块",
                "overrides": [{"index": 0, "type": 1, "categoryId": 2}],
            },
        )
        assert res.status_code == 200
        assert "分类类型与收支类型不一致" in res.json()["error"]

    def test_duplicate_via_client_msg_id(self, bookkeeping_env, monkeypatch):
        """验收 #12：同 clientMsgId 重发 → duplicate，不重复入账"""
        fake_db, created_logs, updated_logs = bookkeeping_env
        _patch_parse(monkeypatch, [
            ParsedItem(amount=30.0, amount_raw="30块", type=0, category_name="餐饮"),
        ])

        async def _fake_find(db, user_id, client_msg_id):
            return SimpleNamespace(id=55, request_id="bk_first", record_ids=[101])

        async def _fake_get_records(db, ids, user_id=None):
            return [SimpleNamespace(id=101, amount=30.0, date=date(2026, 10, 5), remark="午饭")]

        monkeypatch.setattr(ai_crud, "find_log_by_client_msg", _fake_find)
        monkeypatch.setattr(ai_crud, "get_records_by_ids", _fake_get_records)

        res = TestClient(app).post(
            "/api/ai/bookkeeping",
            json={"message": "午饭花了30块", "clientMsgId": "cm-dup"},
        )
        assert res.status_code == 200
        body = res.json()
        assert body["action"] == "duplicate"
        assert body["originRequestId"] == "bk_first"
        assert created_logs == []        # 短路，不写新日志
        assert fake_db._added == []      # 不重复入账
