"""会员模块测试 — 配额闸门 / 兑换 / 管理端

规格：docs/membership-plan.md §9 / 10-实现骨架.md §七。
约定：不连真实 MySQL。路由流程用 dependency_overrides + monkeypatch
（照 tests/test_sqli_login.py 模式），纯逻辑用普通断言。
"""

import asyncio
from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from config.db_config import get_db
from config.settings import MEMBERSHIP_PLANS
from crud import membership as membership_crud
from main import app
from utils import ai_concurrency
from utils import auth as auth_utils
from utils.auth import get_current_regular_user, get_current_user


class FakeDB:
    """假 AsyncSession：未被打桩的查询一律失败，防止测试偷偷触库"""

    async def commit(self):
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
    app.dependency_overrides[get_current_user] = lambda: 1   # 登录态：固定 user_id=1
    # 用户侧业务端点挂 get_current_regular_user（管理员 403）；测试统一按普通用户放行
    app.dependency_overrides[get_current_regular_user] = lambda: 1
    with TestClient(app) as c:      # with 触发 lifespan，与 test_app.py 一致
        c.get("/api/health")
        yield c
    app.dependency_overrides.clear()


def _patch_admin_ok(monkeypatch, role: int = 1):
    """打桩 users 查询，让 get_current_admin 的 role 判定可控"""
    async def _fake_get_user(db, user_id):
        return SimpleNamespace(id=user_id, role=role, status=1)

    monkeypatch.setattr(auth_utils, "get_user_by_id", _fake_get_user)


def _patch_quota(monkeypatch, admitted: bool, used: int, limit: int, kind_expected: str | None = None):
    """打桩等级判定 + 原子占额度，返回 consume_quota 的调用记录"""
    calls: list[tuple] = []

    async def _fake_tier(db, user_id):
        return 0

    async def _fake_consume(db, user_id, plan, kind):
        assert kind in ("chat", "analyze", "bookkeeping"), f"未知 kind: {kind}"
        if kind_expected is not None:
            assert kind == kind_expected, f"闸门 kind 应为 {kind_expected}，实际 {kind}"
        calls.append((user_id, kind))
        return admitted, used, limit

    monkeypatch.setattr(membership_crud, "get_tier", _fake_tier)
    monkeypatch.setattr(membership_crud, "consume_quota", _fake_consume)
    return calls


class TestMembershipRoutes:
    """路由注册冒烟：main 导入成功本身即覆盖 import 依赖完整性"""

    def test_membership_routes_registered(self):
        paths = {r.path for r in app.routes}
        assert "/api/membership/status" in paths
        assert "/api/membership/redeem" in paths
        assert "/api/admin/membership/codes" in paths
        assert "/api/admin/membership/codes/{code_id}/void" in paths
        assert "/api/admin/membership/grant" in paths


# ---------------------------------------------------------------------------
# 1. 纯单元：兑换码归一化 / 生成 / 权益矩阵 / 并发槽
# ---------------------------------------------------------------------------
class TestPureLogic:
    def test_normalize_code(self):
        assert membership_crud.normalize_code("  mp-a7km-2p9x-qw4z-rt6b ") == "MPA7KM2P9XQW4ZRT6B"
        assert membership_crud.normalize_code("a7km 2p9x") == "A7KM2P9X"
        assert membership_crud.normalize_code("") == ""
        assert membership_crud.normalize_code(None) == ""

    def test_gen_code_is_16_chars_without_ambiguous_letters(self):
        for _ in range(50):
            code = membership_crud._gen_code()
            assert len(code) == 16
            assert set(code) <= set(membership_crud._CODE_ALPHABET)
            assert not (set(code) & set("0O1I")), f"出现易混淆字符: {code}"

    def test_membership_plans_complete_and_monotonic(self):
        keys = {"name", "daily_chat", "concurrency", "daily_analyze",
                "daily_bookkeeping", "premium_model"}
        free, member = MEMBERSHIP_PLANS[0], MEMBERSHIP_PLANS[1]
        assert keys <= set(free) and keys <= set(member)
        for key in ("daily_chat", "concurrency", "daily_analyze", "daily_bookkeeping"):
            assert member[key] > free[key], f"会员权益 {key} 未高于免费档"
        assert free["premium_model"] is False and member["premium_model"] is True

    def test_try_acquire_enforces_per_user_limit(self):
        ai_concurrency._slots.clear()

        async def _scenario():
            # limit=1：占满后第二次必须拿不到
            release1 = await ai_concurrency.try_acquire(7, 1)
            assert release1 is not None
            assert await ai_concurrency.try_acquire(7, 1) is None
            release1()
            release2 = await ai_concurrency.try_acquire(7, 1)
            assert release2 is not None
            release2()

            # 不同用户互不影响
            assert await ai_concurrency.try_acquire(8, 1) is not None

            # limit 变化（升级）时重建信号量：旧持有者仍释放旧信号量
            release3 = await ai_concurrency.try_acquire(9, 1)
            assert release3 is not None
            assert await ai_concurrency.try_acquire(9, 3) is not None
            release3()

        try:
            asyncio.run(_scenario())
        finally:
            ai_concurrency._slots.clear()


# ---------------------------------------------------------------------------
# 2. /api/membership/status：信封 + benefits camelCase + 用量组包
# ---------------------------------------------------------------------------
class TestMembershipStatus:
    def test_status_free_tier_envelope(self, client, monkeypatch):
        async def _fake_tier(db, user_id):
            return 0

        async def _fake_none(db, user_id):
            return None

        monkeypatch.setattr(membership_crud, "get_tier", _fake_tier)
        monkeypatch.setattr(membership_crud, "get_effective_membership", _fake_none)
        monkeypatch.setattr(membership_crud, "get_usage_row", _fake_none)

        res = client.get("/api/membership/status")

        assert res.status_code == 200
        body = res.json()
        assert body["code"] == 200
        data = body["data"]
        assert data["tier"] == 0
        assert data["tierName"] == "免费版"
        assert data["expiresAt"] is None
        assert data["usage"]["chat"] == {"used": 0, "limit": 10}
        assert data["usage"]["analyze"] == {"used": 0, "limit": 2}
        assert data["usage"]["bookkeeping"] == {"used": 0, "limit": 5}
        # benefits 数值取自 MEMBERSHIP_PLANS，键名为 camelCase（无 `_` 泄漏）
        assert data["benefits"] == {
            "dailyChat": 10, "concurrency": 1, "dailyAnalyze": 2,
            "dailyBookkeeping": 5, "premiumModel": False,
        }
        assert all("_" not in key for key in data["benefits"])

    def test_status_active_member_usage_and_expiry(self, client, monkeypatch):
        expires = datetime(2026, 11, 2, 0, 0, 0)
        usage_row = SimpleNamespace(chat_count=3, analyze_count=0, bookkeeping_count=1)

        async def _fake_tier(db, user_id):
            return 1

        async def _fake_member(db, user_id):
            return SimpleNamespace(expires_at=expires)

        async def _fake_usage(db, user_id):
            return usage_row

        monkeypatch.setattr(membership_crud, "get_tier", _fake_tier)
        monkeypatch.setattr(membership_crud, "get_effective_membership", _fake_member)
        monkeypatch.setattr(membership_crud, "get_usage_row", _fake_usage)

        body = client.get("/api/membership/status").json()["data"]

        assert body["tier"] == 1 and body["tierName"] == "会员"
        assert body["expiresAt"] == "2026-11-02T00:00:00"
        assert body["usage"]["chat"] == {"used": 3, "limit": 100}
        assert body["usage"]["analyze"] == {"used": 0, "limit": 30}
        assert body["usage"]["bookkeeping"] == {"used": 1, "limit": 50}
        assert body["benefits"]["dailyChat"] == 100


# ---------------------------------------------------------------------------
# 3. /api/membership/redeem：失败 400 / 成功出参 / 请求体校验
# ---------------------------------------------------------------------------
class TestRedeem:
    def test_redeem_error_branch(self, client, monkeypatch):
        async def _fake_redeem(db, user_id, raw):
            return False, "该兑换码已被使用", None

        monkeypatch.setattr(membership_crud, "redeem_code", _fake_redeem)

        res = client.post("/api/membership/redeem", json={"code": "A7KM2P9XQW4ZRT6B"})

        assert res.status_code == 400
        assert res.json()["message"] == "该兑换码已被使用"

    def test_redeem_success_returns_expiry(self, client, monkeypatch):
        async def _fake_redeem(db, user_id, raw):
            assert raw == "mp-a7km-2p9x-qw4z-rt6b"      # 归一化在 crud 层，路由原样下传
            return True, "兑换成功，会员已延长 30 天", SimpleNamespace(
                expires_at=datetime(2026, 11, 2, 0, 0, 0)
            )

        monkeypatch.setattr(membership_crud, "redeem_code", _fake_redeem)

        res = client.post("/api/membership/redeem", json={"code": "mp-a7km-2p9x-qw4z-rt6b"})

        assert res.status_code == 200
        body = res.json()
        assert body["message"] == "兑换成功，会员已延长 30 天"
        assert body["data"] == {"tier": 1, "expiresAt": "2026-11-02T00:00:00"}

    def test_redeem_too_short_code_rejected(self, client, monkeypatch):
        """RedeemIn: min_length=4 —— 极短输入在 Pydantic 层即挡下（422），不到 crud"""
        res = client.post("/api/membership/redeem", json={"code": "ab"})

        assert res.status_code == 422


# ---------------------------------------------------------------------------
# 4. 管理端：鉴权 403 / 生成 / 列表参数 / 作废 / 开通
# ---------------------------------------------------------------------------
class TestAdminMembership:
    def test_codes_requires_admin(self, client, monkeypatch):
        _patch_admin_ok(monkeypatch, role=0)      # 已登录但非管理员

        res = client.get("/api/admin/membership/codes")

        assert res.status_code == 403
        assert res.json()["message"] == "无管理员权限"

    def test_generate_codes_success(self, client, monkeypatch):
        _patch_admin_ok(monkeypatch)

        async def _fake_generate(db, count, days, batch_no=None):
            assert (count, days) == (10, 30)
            return [SimpleNamespace(
                id=1, code="A7KM2P9XQW4ZRT6B", days=30, status=0,
                batch_no="20261003153000", used_by=None, used_at=None,
                created_at=datetime(2026, 10, 3, 15, 30, 0),
            )]

        monkeypatch.setattr(membership_crud, "generate_codes", _fake_generate)

        res = client.post("/api/admin/membership/codes", json={"count": 10, "days": 30})

        assert res.status_code == 200
        body = res.json()
        assert body["message"] == "已生成 1 张兑换码"
        assert body["data"]["batchNo"] == "20261003153000"
        code = body["data"]["codes"][0]
        assert code["code"] == "A7KM2P9XQW4ZRT6B"
        assert code["status"] == 0 and code["usedBy"] is None
        assert code["createdAt"].startswith("2026-10-03T15:30:00")

    def test_list_codes_rejects_bad_status(self, client, monkeypatch):
        _patch_admin_ok(monkeypatch)

        res = client.get("/api/admin/membership/codes?status=9")

        assert res.status_code == 400
        assert res.json()["message"] == "参数错误"

    def test_list_codes_page_envelope(self, client, monkeypatch):
        _patch_admin_ok(monkeypatch)

        async def _fake_list(db, page, size, status):
            assert (page, size, status) == (2, 5, 0)
            return {"rows": [], "total": 12}

        monkeypatch.setattr(membership_crud, "list_codes", _fake_list)

        body = client.get("/api/admin/membership/codes?page=2&size=5&status=0").json()["data"]

        assert body == {"records": [], "total": 12, "pages": 3, "current": 2, "size": 5}

    def test_void_code_error_branch(self, client, monkeypatch):
        _patch_admin_ok(monkeypatch)

        async def _fake_void(db, code_id):
            assert code_id == 9
            return False, "已使用的兑换码不能作废"

        monkeypatch.setattr(membership_crud, "void_code", _fake_void)

        res = client.put("/api/admin/membership/codes/9/void")

        assert res.status_code == 400
        assert res.json()["message"] == "已使用的兑换码不能作废"

    def test_grant_unknown_user_404(self, client, monkeypatch):
        _patch_admin_ok(monkeypatch)

        async def _fake_grant(db, user_id, days):
            return None

        monkeypatch.setattr(membership_crud, "grant_membership", _fake_grant)

        res = client.post("/api/admin/membership/grant", json={"userId": 404, "days": 30})

        assert res.status_code == 404
        assert res.json()["message"] == "用户不存在"

    def test_grant_success_shape(self, client, monkeypatch):
        """按 10-实现骨架.md §7.6：data 只含 tier / expiresAt（RedeemOut）"""
        _patch_admin_ok(monkeypatch)

        async def _fake_grant(db, user_id, days):
            assert (user_id, days) == (2, 30)
            return SimpleNamespace(tier=1, expires_at=datetime(2026, 11, 2, 0, 0, 0))

        monkeypatch.setattr(membership_crud, "grant_membership", _fake_grant)

        res = client.post("/api/admin/membership/grant", json={"userId": 2, "days": 30})

        assert res.status_code == 200
        body = res.json()
        assert body["message"] == "已为用户 2 开通/延期 30 天"
        assert body["data"] == {"tier": 1, "expiresAt": "2026-11-02T00:00:00"}


# ---------------------------------------------------------------------------
# 4.5 会员标识注入（既有接口加字段，不得改动原有字段/逻辑）
# ---------------------------------------------------------------------------
class TestMembershipBadge:
    def _patch_user(self, monkeypatch):
        from crud import user as user_crud

        async def _fake_user(db, user_id):
            return SimpleNamespace(id=user_id, username="u1", role=0, status=1)

        monkeypatch.setattr(user_crud, "get_user_by_id", _fake_user)

    def test_user_info_free_tier_badge(self, client, monkeypatch):
        self._patch_user(monkeypatch)

        async def _fake_none(db, user_id):
            return None

        monkeypatch.setattr(membership_crud, "get_effective_membership", _fake_none)

        res = client.get("/api/user/info")

        assert res.status_code == 200
        data = res.json()["data"]
        assert data["username"] == "u1"                  # 原字段不变
        assert data["membership_tier"] == 0
        assert data["membership_expires_at"] is None

    def test_user_info_active_member_badge(self, client, monkeypatch):
        self._patch_user(monkeypatch)

        async def _fake_member(db, user_id):
            return SimpleNamespace(expires_at=datetime(2026, 11, 2, 0, 0, 0))

        monkeypatch.setattr(membership_crud, "get_effective_membership", _fake_member)

        data = client.get("/api/user/info").json()["data"]

        assert data["membership_tier"] == 1
        assert data["membership_expires_at"].startswith("2026-11-02T00:00:00")


# ---------------------------------------------------------------------------
# 5. AI 配额闸门：429 裸 JSON / 通过即计数 / 并发槽 SSE 事件
# ---------------------------------------------------------------------------class TestAiQuotaGate:
    def _patch_session(self, monkeypatch):
        from routers import ai as ai_router

        async def _fake_session(db, session_id, user_id):
            return SimpleNamespace(id=session_id)

        monkeypatch.setattr(ai_router.ai_crud, "get_user_session", _fake_session)
        return ai_router

    def test_chat_quota_exceeded_returns_bare_429(self, client, monkeypatch):
        self._patch_session(monkeypatch)
        _patch_quota(monkeypatch, admitted=False, used=10, limit=10, kind_expected="chat")

        res = client.post("/api/ai/chat", json={"sessionId": "s1", "message": "你好"})

        assert res.status_code == 429
        body = res.json()
        assert body["code"] == "QUOTA_EXCEEDED"
        assert body["used"] == 10 and body["limit"] == 10
        assert "今日AI 对话次数已用完" in body["error"]
        # 裸 JSON 契约：不得出现 Result 信封字段
        assert "data" not in body and "message" not in body

    def test_chat_quota_passed_consumes_once(self, client, monkeypatch):
        ai_router = self._patch_session(monkeypatch)
        calls = _patch_quota(monkeypatch, admitted=True, used=3, limit=10, kind_expected="chat")

        async def _fake_history(db, session_id):
            return []

        async def _fake_finance(db, user_id):
            return ""

        async def _fake_chat(messages, premium=False, user_id=None):
            return "好的"

        async def _fake_add_message(db, session_id, role, content):
            return SimpleNamespace(id="msg_1")

        monkeypatch.setattr(ai_router.memory, "build_history", _fake_history)
        monkeypatch.setattr(ai_router.ai_context, "build_finance_block", _fake_finance)
        monkeypatch.setattr(ai_router.chat_chain, "chat", _fake_chat)
        monkeypatch.setattr(ai_router.ai_crud, "add_message", _fake_add_message)

        res = client.post("/api/ai/chat", json={"sessionId": "s1", "message": "你好"})

        assert res.status_code == 200
        assert res.json() == {"content": "好的", "messageId": "msg_1"}
        assert calls == [(1, "chat")]      # 闸门只调用一次原子占额度，无重复计数

    def test_analyze_quota_exceeded_returns_bare_429(self, client, monkeypatch):
        _patch_quota(monkeypatch, admitted=False, used=2, limit=2, kind_expected="analyze")

        res = client.post("/api/ai/analyze/expenses", json={})

        assert res.status_code == 429
        assert res.json()["code"] == "QUOTA_EXCEEDED"

    def test_budget_quota_exceeded_returns_bare_429(self, client, monkeypatch):
        _patch_quota(monkeypatch, admitted=False, used=2, limit=2, kind_expected="analyze")

        res = client.post("/api/ai/analyze/budget", json={"monthlyIncome": 8000, "savingsGoal": 2000})

        assert res.status_code == 429
        assert res.json()["code"] == "QUOTA_EXCEEDED"

    def test_bookkeeping_quota_exceeded_returns_bare_error(self, client, monkeypatch):
        """按 membership-plan §5.5：bookkeeping 超额走 HTTP 200 + 裸 {"error"}"""
        from routers import ai as ai_router

        _patch_quota(monkeypatch, admitted=False, used=5, limit=5, kind_expected="bookkeeping")

        async def _fake_find_client(db, user_id, client_msg_id):
            return None

        async def _fake_find_dedup(db, user_id, dedup_hash, window_seconds=300):
            return None

        async def _fake_create_log(db, **fields):
            return SimpleNamespace(id=1)

        monkeypatch.setattr(ai_router.ai_crud, "find_log_by_client_msg", _fake_find_client)
        monkeypatch.setattr(ai_router.ai_crud, "find_recent_by_dedup", _fake_find_dedup)
        monkeypatch.setattr(ai_router.ai_crud, "create_bookkeeping_log", _fake_create_log)

        res = client.post("/api/ai/bookkeeping", json={"message": "今天午饭花了35"})

        assert res.status_code == 200
        body = res.json()
        assert "action" not in body            # 不是 created/clarify/ignored 分支
        assert "code" not in body              # 不是 429 裸 JSON 体
        assert "已用完" in body["error"]

    def test_stream_concurrency_limit_emits_sse_error(self, client, monkeypatch):
        ai_router = self._patch_session(monkeypatch)
        _patch_quota(monkeypatch, admitted=True, used=0, limit=10, kind_expected="chat")

        async def _fake_try_acquire(user_id, limit):
            assert limit == 1               # 免费档并发 = 1
            return None                     # 模拟并发已满

        monkeypatch.setattr(ai_router.ai_concurrency, "try_acquire", _fake_try_acquire)

        res = client.post("/api/ai/chat/stream", json={"sessionId": "s1", "message": "你好"})

        assert res.status_code == 200       # 流式契约：HTTP 仍 200，错误走 SSE 事件
        assert "CONCURRENCY_LIMIT" in res.text
        assert '"type": "error"' in res.text

    def test_stream_quota_exceeded_is_http_429_not_sse(self, client, monkeypatch):
        """超额必须在进入 SSE 之前以 HTTP 429 返回（进入流后状态码已发出）"""
        self._patch_session(monkeypatch)
        _patch_quota(monkeypatch, admitted=False, used=10, limit=10, kind_expected="chat")

        res = client.post("/api/ai/chat/stream", json={"sessionId": "s1", "message": "你好"})

        assert res.status_code == 429
        assert res.json()["code"] == "QUOTA_EXCEEDED"
