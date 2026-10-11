"""权限边界测试 — 管理员不得使用用户侧业务功能（记账 / 分类 / 统计 / AI 对话）

规格：utils/auth.py 模块 docstring 的「角色与功能范围矩阵」。

覆盖三件事：
1. `get_current_regular_user` 依赖本身的三条分支（普通用户放行 / 管理员 403 / 用户不存在 401）；
2. 用户侧业务端点：管理员一律 403、普通用户不被权限层拦下；
3. 管理端与「账号自身」端点：管理员放行、普通用户被 403。

约定：不连真实 MySQL。`get_current_user` 覆写为固定登录态（user_id=1），
`users.role` 通过 monkeypatch `utils.auth.get_user_by_id` 控制（同 test_membership.py 模式）。
"""

from decimal import Decimal
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from config.db_config import get_db
from crud import ai as ai_crud
from crud import category as category_crud
from crud import membership as membership_crud
from crud import record as record_crud
from crud import statistics as statistics_crud
from main import app
from utils import auth as auth_utils
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
    app.dependency_overrides[get_current_user] = lambda: 1   # 登录态：固定 user_id=1
    with TestClient(app) as c:
        c.get("/api/health")
        yield c
    app.dependency_overrides.clear()


def _patch_role(monkeypatch, role: int):
    """打桩 users 查询，控制 get_current_regular_user / get_current_admin 的 role 判定"""
    async def _fake_get_user(db, user_id):
        return SimpleNamespace(id=user_id, role=role, status=1)

    monkeypatch.setattr(auth_utils, "get_user_by_id", _fake_get_user)


# 用户侧业务端点代表样本：记账 / 分类 / 统计 / AI 会话 / AI 语音 各取一条
BUSINESS_ENDPOINTS = [
    ("GET", "/api/records"),
    ("GET", "/api/categories"),
    ("GET", "/api/statistics/monthly?year=2026&month=10"),
    ("GET", "/api/ai/sessions"),
    ("GET", "/api/ai/voice/config"),
]

ADMIN_MESSAGE = "管理员账号无需使用该功能，请前往管理后台"


def _patch_business_crud(monkeypatch, path: str):
    """把路径对应的 crud 查询打桩成空结果，让普通用户的请求能真正走到 200。

    这样断言的是「普通用户拿到正常服务」，比只断言「不是 403」强得多
    —— 同时构成一条回归防线：权限改造没有波及普通用户的正常链路。
    """
    if path == "/api/records":
        async def _records(db, user_id, **kw):
            return {"rows": [], "total": 0}

        monkeypatch.setattr(record_crud, "get_records_by_user", _records)
    elif path == "/api/categories":
        async def _categories(db, user_id, type=None):
            return []

        monkeypatch.setattr(category_crud, "get_categories_by_user", _categories)
    elif path.startswith("/api/statistics/monthly"):
        async def _summary(db, user_id, year, month):
            return Decimal("0"), Decimal("0")

        monkeypatch.setattr(statistics_crud, "get_summary", _summary)
    elif path == "/api/ai/sessions":
        async def _sessions(db, user_id, keyword="", sort="updated", order="desc",
                            page=1, size=20):
            return [], 0

        monkeypatch.setattr(ai_crud, "list_sessions", _sessions)
    # /api/ai/voice/config 只读配置常量，不触库，无需打桩


# ---------------------------------------------------------------------------
# 1. get_current_regular_user 依赖本身
# ---------------------------------------------------------------------------
class TestDependencyUnit:
    @pytest.mark.asyncio
    async def test_regular_user_passes(self, monkeypatch):
        _patch_role(monkeypatch, role=0)
        assert await get_current_regular_user(user_id=7, db=FakeDB()) == 7

    @pytest.mark.asyncio
    async def test_admin_rejected_with_403(self, monkeypatch):
        _patch_role(monkeypatch, role=1)
        with pytest.raises(HTTPException) as ei:
            await get_current_regular_user(user_id=7, db=FakeDB())
        assert ei.value.status_code == 403
        assert ei.value.detail == ADMIN_MESSAGE

    @pytest.mark.asyncio
    async def test_missing_user_rejected_with_401(self, monkeypatch):
        async def _none(db, user_id):
            return None

        monkeypatch.setattr(auth_utils, "get_user_by_id", _none)
        with pytest.raises(HTTPException) as ei:
            await get_current_regular_user(user_id=7, db=FakeDB())
        assert ei.value.status_code == 401


# ---------------------------------------------------------------------------
# 2. 用户侧业务端点：管理员 403 / 普通用户放行
# ---------------------------------------------------------------------------
class TestBusinessEndpoints:
    @pytest.mark.parametrize("method,path", BUSINESS_ENDPOINTS)
    def test_admin_gets_403(self, client, monkeypatch, method, path):
        _patch_role(monkeypatch, role=1)

        res = client.request(method, path)

        assert res.status_code == 403
        assert res.json()["message"] == ADMIN_MESSAGE

    @pytest.mark.parametrize("method,path", BUSINESS_ENDPOINTS)
    def test_regular_user_gets_normal_service(self, client, monkeypatch, method, path):
        """普通用户不受权限改造影响：打桩 crud 后应正常拿到 200"""
        _patch_role(monkeypatch, role=0)
        _patch_business_crud(monkeypatch, path)

        res = client.request(method, path)

        assert res.status_code == 200


# ---------------------------------------------------------------------------
# 3. 管理端与「账号自身」端点
# ---------------------------------------------------------------------------
class TestAdminSideAndAccountEndpoints:
    def test_admin_reaches_admin_endpoint(self, client, monkeypatch):
        _patch_role(monkeypatch, role=1)

        async def _fake_list(db, page, size, status):
            return {"rows": [], "total": 0}

        monkeypatch.setattr(membership_crud, "list_codes", _fake_list)

        res = client.get("/api/admin/membership/codes")

        assert res.status_code == 200

    def test_regular_user_blocked_from_admin_endpoint(self, client, monkeypatch):
        _patch_role(monkeypatch, role=0)

        res = client.get("/api/admin/membership/codes")

        assert res.status_code == 403

    def test_admin_can_use_account_endpoint(self, client, monkeypatch):
        """账号自身功能（会员状态）对管理员开放——矩阵中「会员/充值」两角色都可用"""
        _patch_role(monkeypatch, role=1)

        async def _tier(db, user_id):
            return 0

        async def _none(db, user_id, *a, **kw):
            return None

        monkeypatch.setattr(membership_crud, "get_tier", _tier)
        monkeypatch.setattr(membership_crud, "get_effective_membership", _none)
        monkeypatch.setattr(membership_crud, "get_usage_row", _none)

        res = client.get("/api/membership/status")

        assert res.status_code == 200
