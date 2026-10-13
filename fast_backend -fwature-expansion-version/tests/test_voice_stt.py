"""语音记账测试 — STT 识别层（M1）+ 落库衔接（M2）

规格：docs/语音记账实施指南.md §2.5 / §5。
约定：不连真实 MySQL。路由流程用 dependency_overrides + monkeypatch
（照 tests/test_membership.py 模式），STT provider 注入假实现，纯逻辑用普通断言。
"""

import asyncio
import struct
import time
from collections import deque
from datetime import date
from types import SimpleNamespace

import httpx
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

    def test_refund_restores_one_slot(self):
        """refund 撤销一次占位：外部调用失败不应烧掉用户的名额"""
        limiter = SlidingWindowRateLimiter(max_calls=1, window=60)
        assert limiter.allow("u1")[0]
        assert not limiter.allow("u1")[0]
        limiter.refund("u1")               # 失败退还
        assert limiter.allow("u1")[0]      # 名额回来了
        assert not limiter.allow("u1")[0]

    def test_refund_on_empty_key_is_noop(self):
        limiter = SlidingWindowRateLimiter(max_calls=1, window=60)
        limiter.refund("never-seen")       # 不得抛异常
        assert limiter.allow("u1")[0]

    @pytest.mark.asyncio
    async def test_concurrent_allow_admits_at_most_max_calls(self):
        """并发放行量不得超过 max_calls。

        回归护栏：旧实现是 check()（只查）+ record()（只记），两次加锁中间隔着
        一次 await 外部调用——N 个并发请求可全部通过 check 再依次执行，把额度
        放大 N 倍，而并发刷量恰恰是限流要防的攻击形态。改为 allow（原子查+记）
        后放行量严格受限。
        """
        limiter = SlidingWindowRateLimiter(max_calls=3, window=60)

        async def _one():
            return limiter.allow("u")

        results = await asyncio.gather(*[_one() for _ in range(20)])
        assert sum(1 for ok, _ in results if ok) == 3


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


# ---------------------------------------------------------------------------
# 5. P1-7：WAV 服务端时长校验 + 限流槽位（失败不占）
# ---------------------------------------------------------------------------

def _make_wav(*, byte_rate: int, data_size: int, fmt_extra: bytes = b"",
              actual_bytes: int | None = None) -> bytes:
    """构造 PCM WAV 容器。

    ``data_size`` 写进 RIFF 头的 data 块声明长度；``actual_bytes`` 是 data 块
    真正写入的字节数，默认与之相等（真实文件即如此）。显式传入远大于声明值的
    数字即可模拟攻击者伪造 RIFF 头「声明很短、实传很长」绕过时长守卫。
    """
    fmt = struct.pack("<HHIIHH", 1, 1, 16000, byte_rate, 2, 16) + fmt_extra
    body = b"fmt " + struct.pack("<I", len(fmt)) + fmt
    n = data_size if actual_bytes is None else actual_bytes
    body += b"data" + struct.pack("<I", data_size) + b"\x00" * n
    return b"RIFF" + struct.pack("<I", 4 + len(body)) + b"WAVE" + body


class TestWavDuration:
    """回归：STT_MAX_SECONDS 此前只下发给前端，服务端不校验，客户端可绕过上传长音频"""

    def test_parses_standard_wav(self):
        assert ai_router._wav_duration_seconds(
            _make_wav(byte_rate=16000, data_size=32000)) == pytest.approx(2.0)

    def test_tolerates_oversized_fmt_chunk(self):
        """扩展 fmt 块（cbSize>0）不得导致解析失败"""
        assert ai_router._wav_duration_seconds(
            _make_wav(byte_rate=8000, data_size=8000, fmt_extra=b"\x00\x00")
        ) == pytest.approx(1.0)

    def test_non_wav_returns_none(self):
        assert ai_router._wav_duration_seconds(FAKE_M4A) is None
        assert ai_router._wav_duration_seconds(b"this-is-not-audio") is None

    def test_truncated_or_missing_fmt_returns_none(self):
        # 截断头
        assert ai_router._wav_duration_seconds(b"RIFF\x00\x00\x00\x00WAVE") is None
        # data 在 fmt 之前：拿不到 byte_rate → 未校验
        body = b"data" + struct.pack("<I", 999999)
        wav = b"RIFF" + struct.pack("<I", 4 + len(body)) + b"WAVE" + body
        assert ai_router._wav_duration_seconds(wav) is None

    def test_ignores_lied_about_data_length(self):
        """伪造 RIFF 头不能绕过时长守卫：声明 1 秒、实传 180 秒 → 必须按 180s 算

        data 块长度是客户端可控的头字段。若按声明值算，攻击者把 180 秒录音的
        声明长度伪造成 1 秒即可绕过 STT_MAX_SECONDS，而真实音频长度本就等于
        容器里 data 块的字节数——故只能信实际字节数。
        """
        wav = _make_wav(byte_rate=1600, data_size=1600, actual_bytes=1600 * 180)
        assert ai_router._wav_duration_seconds(wav) == pytest.approx(180.0)


class TestVoiceDurationGuard:
    def test_rejects_too_long_wav(self, stt_client, monkeypatch):
        monkeypatch.setattr(ai_router, "STT_MAX_SECONDS", 2)
        monkeypatch.setattr(stt, "_provider", _FakeProvider())
        res = stt_client.post(
            "/api/ai/voice/transcribe",
            files={"file": ("a.wav", _make_wav(byte_rate=16000, data_size=16000 * 3), "audio/wav")},
        )
        assert res.status_code == 200
        assert "录音过长" in res.json()["error"]

    def test_rejects_wav_whose_header_lies_about_length(self, stt_client, monkeypatch):
        """端到端：伪造 RIFF 头（声明 1 秒、实传 60 秒）同样被时长守卫拦下"""
        monkeypatch.setattr(ai_router, "STT_MAX_SECONDS", 2)
        monkeypatch.setattr(stt, "_provider", _FakeProvider())
        res = stt_client.post(
            "/api/ai/voice/transcribe",
            files={"file": ("a.wav", _make_wav(byte_rate=1600, data_size=1600,
                                               actual_bytes=1600 * 60), "audio/wav")},
        )
        assert res.status_code == 200
        assert "录音过长" in res.json()["error"]

    def test_accepts_wav_within_limit(self, stt_client, monkeypatch):
        monkeypatch.setattr(ai_router, "STT_MAX_SECONDS", 10)
        monkeypatch.setattr(stt, "_provider", _FakeProvider())
        res = stt_client.post(
            "/api/ai/voice/transcribe",
            files={"file": ("a.wav", _make_wav(byte_rate=16000, data_size=16000 * 2), "audio/wav")},
        )
        assert res.status_code == 200
        assert res.json()["text"] == "今天打车花了18块"

    def test_unparsable_duration_is_not_blocked(self, stt_client, monkeypatch):
        """解析不出时长（None）视为未校验，不得误伤正常录音"""
        monkeypatch.setattr(ai_router, "STT_MAX_SECONDS", 0)
        monkeypatch.setattr(stt, "_provider", _FakeProvider())
        body = b"data" + struct.pack("<I", 999999)
        wav = b"RIFF" + struct.pack("<I", 4 + len(body)) + b"WAVE" + body
        res = stt_client.post(
            "/api/ai/voice/transcribe",
            files={"file": ("a.wav", wav, "audio/wav")},
        )
        assert res.status_code == 200
        assert res.json()["text"] == "今天打车花了18块"


class TestVoiceRateSlot:
    """回归：转写失败不产生 ASR 计费，却会白占用户每分钟的配额名额"""

    def test_provider_failure_does_not_consume_slot(self, stt_client, monkeypatch):
        monkeypatch.setattr(ai_router, "voice_rate_limiter",
                            SlidingWindowRateLimiter(max_calls=1, window=60))
        monkeypatch.setattr(stt, "_provider", _BoomProvider())

        failed = stt_client.post(
            "/api/ai/voice/transcribe",
            files={"file": ("a.m4a", FAKE_M4A, "audio/m4a")},
        )
        assert "语音识别暂不可用" in failed.json()["error"]

        # 失败未占槽 → 换回可用 provider 后同一用户仍可立即重试
        monkeypatch.setattr(stt, "_provider", _FakeProvider())
        retry = stt_client.post(
            "/api/ai/voice/transcribe",
            files={"file": ("a.m4a", FAKE_M4A, "audio/m4a")},
        )
        assert retry.status_code == 200
        assert retry.json()["text"] == "今天打车花了18块"

    def test_oversize_failure_does_not_consume_slot(self, stt_client, monkeypatch):
        """前置校验失败同样不该占槽"""
        monkeypatch.setattr(ai_router, "voice_rate_limiter",
                            SlidingWindowRateLimiter(max_calls=1, window=60))
        monkeypatch.setattr(stt, "_provider", _FakeProvider())

        bad = stt_client.post(
            "/api/ai/voice/transcribe",
            files={"file": ("a.txt", b"x", "text/plain")},
        )
        assert "不支持" in bad.json()["error"]

        ok = stt_client.post(
            "/api/ai/voice/transcribe",
            files={"file": ("a.m4a", FAKE_M4A, "audio/m4a")},
        )
        assert ok.status_code == 200 and "text" in ok.json()

    def test_success_consumes_slot(self, stt_client, monkeypatch):
        """成功才计槽：额度用尽后必须限流，否则限流形同虚设"""
        monkeypatch.setattr(ai_router, "voice_rate_limiter",
                            SlidingWindowRateLimiter(max_calls=2, window=60))
        monkeypatch.setattr(stt, "_provider", _FakeProvider())

        for _ in range(2):
            ok = stt_client.post(
                "/api/ai/voice/transcribe",
                files={"file": ("a.m4a", FAKE_M4A, "audio/m4a")},
            )
            assert ok.status_code == 200 and "text" in ok.json()

        third = stt_client.post(
            "/api/ai/voice/transcribe",
            files={"file": ("a.m4a", FAKE_M4A, "audio/m4a")},
        )
        assert "说话太频繁" in third.json()["error"]


class TestWhisperProviderClient:
    """P1-7：连接池复用 + 瞬时故障重试一次（4xx 不重试）"""

    def test_reuses_single_client(self):
        p = stt.OpenAIWhisperProvider(
            base_url="https://example.invalid/v1", api_key="k", model="whisper-1", timeout=5.0,
        )
        assert p._get_client() is p._get_client(), "每次 transcribe 不应重建 httpx 客户端"

    @pytest.mark.asyncio
    async def test_client_rebuilt_when_event_loop_changes(self):
        """httpx client 与创建它的 loop 绑定；loop 变了必须重建，否则跨 loop 复用会炸。

        单 worker 生产环境只有一个 loop，但 pytest-asyncio 默认每个 async 用例
        新建 loop——若不做隔离，第二个用例就会踩到 Event loop is closed。
        """
        p = stt.OpenAIWhisperProvider(
            base_url="https://example.invalid/v1", api_key="k", model="whisper-1", timeout=5.0,
        )
        stale = httpx.AsyncClient(timeout=5.0)
        other_loop = asyncio.new_event_loop()
        try:
            p._client, p._client_loop = stale, other_loop
            fresh = p._get_client()
            assert fresh is not stale, "事件循环切换后不得复用绑定旧 loop 的 client"
        finally:
            await stale.aclose()
            await p._client.aclose()
            other_loop.close()

    @pytest.mark.asyncio
    async def test_aclose_releases_connection_pool(self):
        """aclose 必须真正关掉连接池并清空引用（lifespan shutdown 调用）"""
        p = stt.OpenAIWhisperProvider(
            base_url="https://example.invalid/v1", api_key="k", model="whisper-1", timeout=5.0,
        )
        client = p._get_client()
        await p.aclose()
        assert client.is_closed
        assert p._client is None and p._client_loop is None

    @pytest.mark.asyncio
    async def test_aclose_stt_provider_tolerates_unset_and_custom_provider(self, monkeypatch):
        """模块级关闭入口：provider 从未创建、或自定义实现无连接池时都不得抛"""
        monkeypatch.setattr(stt, "_provider", None)
        await stt.aclose_stt_provider()          # 从未创建 → 静默通过

        monkeypatch.setattr(stt, "_provider", _FakeProvider())   # 无 aclose 方法
        await stt.aclose_stt_provider()          # 不应抛异常

    @pytest.mark.asyncio
    async def test_retries_once_on_5xx(self, monkeypatch):
        calls = {"n": 0}

        class _Resp:
            def __init__(self, code):
                self.status_code = code

            def raise_for_status(self):
                return None

            def json(self):
                return {"text": "ok"}

        class _Client:
            async def post(self, *a, **kw):
                calls["n"] += 1
                return _Resp(500 if calls["n"] == 1 else 200)

        p = stt.OpenAIWhisperProvider("https://x.invalid/v1", "k", "m", 1.0)
        monkeypatch.setattr(p, "_get_client", lambda: _Client())
        monkeypatch.setattr(stt, "_RETRY_BACKOFF_SECONDS", 0)

        out = await p.transcribe(b"x", "a.m4a")
        assert out.text == "ok"
        assert calls["n"] == 2

    @pytest.mark.asyncio
    async def test_retries_once_on_transport_error(self, monkeypatch):
        calls = {"n": 0}

        class _Resp:
            status_code = 200

            def raise_for_status(self):
                return None

            def json(self):
                return {"text": "ok"}

        class _Client:
            async def post(self, *a, **kw):
                calls["n"] += 1
                if calls["n"] == 1:
                    raise httpx.ConnectError("boom")
                return _Resp()

        p = stt.OpenAIWhisperProvider("https://x.invalid/v1", "k", "m", 1.0)
        monkeypatch.setattr(p, "_get_client", lambda: _Client())
        monkeypatch.setattr(stt, "_RETRY_BACKOFF_SECONDS", 0)

        out = await p.transcribe(b"x", "a.m4a")
        assert out.text == "ok"
        assert calls["n"] == 2

    @pytest.mark.asyncio
    async def test_does_not_retry_4xx(self, monkeypatch):
        """4xx 是请求自身的问题，重试只会白付一次外部计费"""
        calls = {"n": 0}

        class _Resp:
            status_code = 401

            def raise_for_status(self):
                raise RuntimeError("unauthorized")

            def json(self):
                return {}

        class _Client:
            async def post(self, *a, **kw):
                calls["n"] += 1
                return _Resp()

        p = stt.OpenAIWhisperProvider("https://x.invalid/v1", "k", "m", 1.0)
        monkeypatch.setattr(p, "_get_client", lambda: _Client())

        with pytest.raises(RuntimeError, match="unauthorized"):
            await p.transcribe(b"x", "a.m4a")
        assert calls["n"] == 1
