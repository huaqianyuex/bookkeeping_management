"""记账「金额确认卡」后端契约测试 — dryRun 预览 → overrides 确认

背景（需求）
------------
前端在语音或文字输入后弹「金额确认框」：显示解析出的金额、允许改，再按改后金额入账。
后端契约是两步：
    ① dryRun=true  → action="preview"，preview.items[] 带 index/amount/...
    ② dryRun=false + overrides=[{index, amount}] → action="created"

本文件锁住三条容易回归的性质：
1. **配额只扣一次**：dryRun 预览不计 daily_bookkeeping，否则「预览+确认」一次记账
   要扣 2 次额度（免费档 daily_bookkeeping=5 → 实际只剩 2.5 次）。预览改走独立滑动
   窗口限流，且必须在 **LLM 解析之前** 判定。
2. **index 是覆盖键**：改第 2 笔金额必须落到第 2 笔上，不能串到第 1 笔。
3. **同 clientMsgId 连点确认幂等**：第二次确认走 duplicate，不重复入账。

约定：不连真实 MySQL、不调真实 LLM。照 tests/test_voice_stt.py 的模式，
用 dependency_overrides + monkeypatch 打桩。
"""

import types
from datetime import date

import pytest
from fastapi.testclient import TestClient

from ai.bookkeeping_chain import Parsed, ParsedItem
from config.db_config import get_db
from main import app
from routers import ai as ai_router
from utils.auth import get_current_regular_user
from utils.throttle import SlidingWindowRateLimiter


class FakeDB:
    """假 AsyncSession：execute 只放行 Category 查询；add/flush 模拟自增主键"""

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
        types.SimpleNamespace(id=1, name="餐饮", user_id=None, type=0, status=1),
        types.SimpleNamespace(id=2, name="交通", user_id=None, type=0, status=1),
        types.SimpleNamespace(id=9, name="其他", user_id=None, type=0, status=1),
    ]


class Env:
    """用例内被观测到的状态"""

    def __init__(self, db):
        self.db = db
        self.quota_kinds = []      # consume_quota 收到的 kind 序列
        self.parse_calls = 0       # LLM 解析调用次数
        self.created_logs = []
        self.updated_logs = []

    @property
    def records(self):
        return self.db._added


@pytest.fixture()
def client():
    async def _override_get_db():
        yield FakeDB(_categories())

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_regular_user] = lambda: 1
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def bk_env(client, monkeypatch):
    """打桩：假 DB + 放行配额 + 假解析 + 假日志读写

    `find_log_by_client_msg` 用「已成功落库的 clientMsgId」集合模拟真实语义
    （真实查询只认 status=1 且 record_ids 非空，见 crud/ai.py）。
    """
    from crud import ai as ai_crud
    from crud import membership as membership_crud
    from utils import ai_concurrency

    fake_db = FakeDB(_categories())
    env = Env(fake_db)

    async def _override_get_db():
        yield fake_db

    app.dependency_overrides[get_db] = _override_get_db

    # ── 配额：只记录，不拦截 ──
    async def _tier(db, user_id):
        return 0

    async def _consume(db, user_id, plan, kind):
        env.quota_kinds.append(kind)
        return True, 1, 100

    monkeypatch.setattr(membership_crud, "get_tier", _tier)
    monkeypatch.setattr(membership_crud, "consume_quota", _consume)

    # ── 日志读写：模拟 uk_abk_client_msg 的可见性语义 ──
    confirmed: dict = {}
    log_key: dict = {}

    async def _create_log(db, **fields):
        env.created_logs.append(fields)
        log_key[77] = fields.get("client_msg_id")
        return types.SimpleNamespace(id=77, **fields)

    async def _update_log(db, log_id, **fields):
        env.updated_logs.append({"id": log_id, **fields})
        if fields.get("record_ids") and log_key.get(log_id):
            confirmed[log_key[log_id]] = fields["record_ids"]
        return None

    async def _find_log(db, user_id, client_msg_id):
        if client_msg_id and client_msg_id in confirmed:
            return types.SimpleNamespace(
                id=77, request_id="bk_prev", record_ids=confirmed[client_msg_id]
            )
        return None

    async def _find_recent(db, user_id, dedup_hash, window):
        return None

    async def _get_records(db, ids, user_id=None):
        return [
            types.SimpleNamespace(id=i, amount=35.0, date=date(2026, 10, 5), remark="午饭")
            for i in ids
        ]

    monkeypatch.setattr(ai_crud, "create_bookkeeping_log", _create_log)
    monkeypatch.setattr(ai_crud, "update_bookkeeping_log", _update_log)
    monkeypatch.setattr(ai_crud, "find_log_by_client_msg", _find_log)
    monkeypatch.setattr(ai_crud, "find_recent_by_dedup", _find_recent)
    monkeypatch.setattr(ai_crud, "get_records_by_ids", _get_records)
    monkeypatch.setattr(ai_crud, "new_id", lambda prefix: f"{prefix}_test")

    async def _acquire(user_id, limit):
        def _release():
            return None
        return _release

    monkeypatch.setattr(ai_concurrency, "try_acquire", _acquire)

    # 每个用例用全新的预览限流器，避免跨用例累计
    monkeypatch.setattr(
        ai_router, "bookkeeping_preview_rate_limiter",
        SlidingWindowRateLimiter(max_calls=20, window=60),
    )

    yield env, monkeypatch
    app.dependency_overrides.pop(get_db, None)


def _patch_parse(env, monkeypatch, items, intent="bookkeeping"):
    """替换 LLM 解析，并统计调用次数（用于验证限流在解析之前生效）"""

    async def _fake_parse(message, today, category_names, user_id=None):
        env.parse_calls += 1
        return Parsed(intent=intent, items=items)

    monkeypatch.setattr(ai_router, "parse_bookkeeping", _fake_parse)


def _one_item(amount=35.0, raw="35块", name="餐饮"):
    return ParsedItem(amount=amount, amount_raw=raw, type=0, category_name=name)


def _preview(client, **body):
    payload = {"message": "午饭35块", "dryRun": True}
    payload.update(body)
    return client.post("/api/ai/bookkeeping", json=payload)


def _confirm(client, **body):
    payload = {"message": "午饭35块", "clientMsgId": "cm-1"}
    payload.update(body)
    return client.post("/api/ai/bookkeeping", json=payload)


# ---------------------------------------------------------------------------
# 1. 配额口径：预览不扣，确认扣一次
# ---------------------------------------------------------------------------
class TestQuotaOnlyChargedOnCommit:
    def test_preview_does_not_consume_daily_quota(self, client, bk_env):
        env, monkeypatch = bk_env
        _patch_parse(env, monkeypatch, [_one_item()])

        assert _preview(client).json()["action"] == "preview"
        assert env.quota_kinds == [], "dryRun 预览不应消耗 daily_bookkeeping 配额"

    def test_confirm_consumes_quota_once(self, client, bk_env):
        env, monkeypatch = bk_env
        _patch_parse(env, monkeypatch, [_one_item()])

        assert _confirm(client).json()["action"] == "created"
        assert env.quota_kinds == ["bookkeeping"]

    def test_preview_then_confirm_charges_exactly_once(self, client, bk_env):
        """回归核心：确认框流程（预览 + 确认）整体只扣 1 次额度

        修复前两次请求各扣一次，免费档 5 次/天会腰斩成 2.5 次。
        """
        env, monkeypatch = bk_env
        _patch_parse(env, monkeypatch, [_one_item()])

        assert _preview(client).json()["action"] == "preview"
        assert _confirm(client).json()["action"] == "created"
        assert env.quota_kinds == ["bookkeeping"], "一次记账只能扣一次配额"


# ---------------------------------------------------------------------------
# 2. 预览限流：独立闸门，且在 LLM 解析之前
# ---------------------------------------------------------------------------
class TestPreviewRateLimit:
    def test_preview_rate_limited_returns_machine_readable_code(self, client, bk_env):
        env, monkeypatch = bk_env
        _patch_parse(env, monkeypatch, [_one_item()])
        monkeypatch.setattr(ai_router, "bookkeeping_preview_rate_limiter",
                            SlidingWindowRateLimiter(max_calls=1, window=60))

        assert _preview(client).json()["action"] == "preview"

        second = _preview(client)
        assert second.status_code == 200, "记账端点失败走 HTTP 200 裸 JSON 契约"
        body = second.json()
        assert body.get("code") == "RATE_LIMIT"
        assert "error" in body

    def test_rate_limit_short_circuits_before_llm(self, client, bk_env):
        """限流必须在解析之前：否则被拒的请求照样烧一次 LLM 成本"""
        env, monkeypatch = bk_env
        _patch_parse(env, monkeypatch, [_one_item()])
        monkeypatch.setattr(ai_router, "bookkeeping_preview_rate_limiter",
                            SlidingWindowRateLimiter(max_calls=1, window=60))

        _preview(client)
        assert env.parse_calls == 1
        _preview(client)
        assert env.parse_calls == 1, "被限流的预览不应触发第二次 LLM 解析"

    def test_preview_limiter_does_not_block_confirm(self, client, bk_env):
        """预览踩到限流，不应连带把「确认入账」也堵住（两条独立闸门）"""
        env, monkeypatch = bk_env
        _patch_parse(env, monkeypatch, [_one_item()])
        monkeypatch.setattr(ai_router, "bookkeeping_preview_rate_limiter",
                            SlidingWindowRateLimiter(max_calls=1, window=60))

        _preview(client)
        assert _preview(client).json().get("code") == "RATE_LIMIT"

        assert _confirm(client).json()["action"] == "created"
        assert env.quota_kinds == ["bookkeeping"]

    def test_confirm_has_no_preview_limit(self, client, bk_env):
        """确认请求不吃预览限流额度：连续确认多次不应出现 RATE_LIMIT"""
        env, monkeypatch = bk_env
        _patch_parse(env, monkeypatch, [_one_item()])
        monkeypatch.setattr(ai_router, "bookkeeping_preview_rate_limiter",
                            SlidingWindowRateLimiter(max_calls=1, window=60))

        for i in range(3):
            body = _confirm(client, clientMsgId=f"cm-{i}").json()
            assert body.get("code") != "RATE_LIMIT", body


# ---------------------------------------------------------------------------
# 3. 金额覆盖：按 preview 的 index 落到对应条目
# ---------------------------------------------------------------------------
class TestAmountOverrideApplied:
    def test_preview_exposes_editable_amount_and_index(self, client, bk_env):
        """确认框渲染所需字段：金额 + 定位键 + 原文片段"""
        env, monkeypatch = bk_env
        _patch_parse(env, monkeypatch, [_one_item(amount=35.0, raw="35块")])

        body = _preview(client).json()
        assert body["action"] == "preview"
        item = body["preview"]["items"][0]
        assert item["index"] == 0
        assert item["amount"] == 35.0
        assert item["amountRaw"] == "35块"
        assert body["records"] == [], "预览不得落库"

    def test_edited_amount_lands_on_confirm(self, client, bk_env):
        """需求：金额可改，并按改后的金额确认入账"""
        env, monkeypatch = bk_env
        _patch_parse(env, monkeypatch, [_one_item(amount=35.0)])

        item = _preview(client).json()["preview"]["items"][0]
        edited = item["amount"] + 15.0          # 用户把 35 改成 50

        out = _confirm(client, overrides=[{"index": item["index"], "amount": edited}]).json()
        assert out["action"] == "created"
        assert out["records"][0]["amount"] == 50.0
        assert [float(r.amount) for r in env.records] == [50.0]

    def test_override_by_index_does_not_bleed_to_other_item(self, client, bk_env):
        """两笔时改第 2 笔，必须落在第 2 笔（index 对齐，不是数组位置碰巧）"""
        env, monkeypatch = bk_env
        _patch_parse(env, monkeypatch, [
            _one_item(amount=30.0, raw="30块", name="餐饮"),
            _one_item(amount=18.0, raw="18块", name="交通"),
        ])

        items = _preview(client, message="午饭30，打车18").json()["preview"]["items"]
        assert [i["index"] for i in items] == [0, 1]

        out = _confirm(
            client,
            message="午饭30，打车18",
            overrides=[{"index": 1, "amount": 99.0}],
        ).json()
        assert out["action"] == "created"
        assert [r["amount"] for r in out["records"]] == [30.0, 99.0]
        assert [float(r.amount) for r in env.records] == [30.0, 99.0]

    def test_override_can_supply_missing_amount(self, client, bk_env):
        """缺金额的条目也能被确认卡补上——否则用户永远走不出 clarify"""
        env, monkeypatch = bk_env
        _patch_parse(env, monkeypatch, [
            ParsedItem(amount=None, amount_raw=None, type=0, category_name="餐饮"),
        ])

        preview = _preview(client).json()
        assert preview["preview"]["items"][0]["amount"] is None

        out = _confirm(client, overrides=[{"index": 0, "amount": 42.0}]).json()
        assert out["action"] == "created"
        assert out["records"][0]["amount"] == 42.0


# ---------------------------------------------------------------------------
# 4. 幂等：同一 clientMsgId 连点确认只入账一次
# ---------------------------------------------------------------------------
class TestDoubleConfirmIdempotent:
    def test_second_confirm_with_same_client_msg_id_is_duplicate(self, client, bk_env):
        env, monkeypatch = bk_env
        _patch_parse(env, monkeypatch, [_one_item()])

        first = _confirm(client, clientMsgId="cm-dup").json()
        assert first["action"] == "created"
        assert len(env.records) == 1

        second = _confirm(client, clientMsgId="cm-dup").json()
        assert second["action"] == "duplicate", "连点确认必须被幂等键拦成 duplicate"
        assert len(env.records) == 1, "不得重复入账"

    def test_preview_does_not_occupy_idempotency_key(self, client, bk_env):
        """预览不写日志、不占幂等键；真正落库只发生在确认那次"""
        env, monkeypatch = bk_env
        _patch_parse(env, monkeypatch, [_one_item()])

        _preview(client, clientMsgId="cm-x")
        assert env.created_logs == [], "dryRun 不应写审计日志"

        out = _confirm(client, clientMsgId="cm-x").json()
        assert out["action"] == "created", "预览占过键的话这里会变成 duplicate/请求处理中"


# ---------------------------------------------------------------------------
# 5. 预览缓存复用：确认回传 previewId 时跳过第二次 LLM（性能优化）
# ---------------------------------------------------------------------------
class TestPreviewCacheReuse:
    """确认请求带 previewId 时复用预览的解析结果。

    动机：确认原先要**再跑一次 LLM 解析**（秒级），而预览刚刚才解析过同一条消息。
    复用后确认只剩 DB 写入（毫秒级）。未命中必须回退重新解析——只慢不错。
    """

    def test_confirm_with_preview_id_skips_second_llm(self, client, bk_env):
        """回归核心：确认回传 previewId 时不再调用 LLM"""
        env, monkeypatch = bk_env
        _patch_parse(env, monkeypatch, [_one_item(amount=35.0)])

        preview = _preview(client).json()
        assert env.parse_calls == 1

        out = _confirm(client, previewId=preview["requestId"]).json()
        assert out["action"] == "created"
        assert env.parse_calls == 1, "命中预览缓存时确认不应再解析一次"

    def test_confirm_without_preview_id_falls_back_to_llm(self, client, bk_env):
        """未回传 previewId（旧客户端）时行为不变：确认重新解析一次"""
        env, monkeypatch = bk_env
        _patch_parse(env, monkeypatch, [_one_item()])

        _preview(client)
        assert _confirm(client).json()["action"] == "created"
        assert env.parse_calls == 2

    def test_unknown_preview_id_falls_back(self, client, bk_env):
        """陈旧/伪造的 previewId 不命中，回退重新解析（只慢不错）"""
        env, monkeypatch = bk_env
        _patch_parse(env, monkeypatch, [_one_item()])

        out = _confirm(client, previewId="bk_not_exists").json()
        assert out["action"] == "created"
        assert env.parse_calls == 1

    def test_preview_id_for_other_message_falls_back(self, client, bk_env):
        """同一 previewId 换了消息：必须回退，不能把旧消息的解析结果套上来"""
        env, monkeypatch = bk_env
        _patch_parse(env, monkeypatch, [_one_item(amount=35.0)])

        preview = _preview(client, message="午饭35块").json()

        out = _confirm(client, message="打车18块", previewId=preview["requestId"]).json()
        assert out["action"] == "created"
        assert env.parse_calls == 2, "消息不一致时不得复用缓存"

    def test_edited_amount_still_applies_when_cache_hit(self, client, bk_env):
        """缓存复用不得绕过 overrides：改后的金额仍要落到记录上"""
        env, monkeypatch = bk_env
        _patch_parse(env, monkeypatch, [_one_item(amount=35.0)])

        preview = _preview(client).json()
        item = preview["preview"]["items"][0]

        out = _confirm(
            client,
            previewId=preview["requestId"],
            overrides=[{"index": item["index"], "amount": 50.0}],
        ).json()
        assert out["action"] == "created"
        assert out["records"][0]["amount"] == 50.0
        assert env.parse_calls == 1, "命中缓存时确认仍不应解析"

    def test_cache_hit_does_not_skip_quota(self, client, bk_env):
        """缓存只省 LLM，不省配额：确认仍要扣一次 daily_bookkeeping"""
        env, monkeypatch = bk_env
        _patch_parse(env, monkeypatch, [_one_item()])

        preview = _preview(client).json()
        assert _confirm(client, previewId=preview["requestId"]).json()["action"] == "created"
        assert env.quota_kinds == ["bookkeeping"]


# ---------------------------------------------------------------------------
# 6. TtlCache 单测（纯内存态，不需要 test client）
# ---------------------------------------------------------------------------
class TestTtlCacheUnit:
    def test_expired_entry_is_miss(self):
        from utils.throttle import TtlCache

        c = TtlCache(ttl=0.0, max_entries=10)
        c.set("k", {"v": 1})
        assert c.get("k") is None

    def test_overflow_evicts_oldest(self):
        from utils.throttle import TtlCache

        c = TtlCache(ttl=300, max_entries=2)
        c.set("a", 1)
        c.set("b", 2)
        c.set("c", 3)
        assert c.get("a") is None, "超容量应淘汰最旧的键"
        assert c.get("b") == 2
        assert c.get("c") == 3

    def test_clear(self):
        from utils.throttle import TtlCache

        c = TtlCache(ttl=300, max_entries=10)
        c.set("a", 1)
        c.clear()
        assert c.get("a") is None