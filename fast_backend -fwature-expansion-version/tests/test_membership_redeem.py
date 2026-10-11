"""兑换码核销链路的补充测试 — 防刷限流 + 「我的兑换记录」端点

规格：routers/membership.py（redeem 限流 / GET /api/membership/redemptions）
      crud/membership.py::list_user_redemptions

约定：不连真实 MySQL，crud 层整体 monkeypatch。
"""

from datetime import datetime
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from config.db_config import get_db
from crud import membership as membership_crud
from main import app
from routers import membership as membership_router
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
    app.dependency_overrides[get_current_regular_user] = lambda: 1
    membership_router.redeem_rate_limiter._hits.clear()
    with TestClient(app) as c:
        c.get("/api/health")
        yield c
    app.dependency_overrides.clear()
    membership_router.redeem_rate_limiter._hits.clear()


class TestRedeemRateLimit:
    """核销是带行锁的写操作，需防脚本高频空转打库"""

    def test_throttled_after_limit(self, client, monkeypatch):
        async def _fake_redeem(db, user_id, raw):
            return False, "兑换码不存在", None

        monkeypatch.setattr(membership_crud, "redeem_code", _fake_redeem)

        limit = membership_router.redeem_rate_limiter.max_calls
        body = {"code": "AAAA2222BBBB3333"}

        # 前 limit 次都进入业务层（码不存在 → 400），第 limit+1 次被限流挡下（429）
        for _ in range(limit):
            res = client.post("/api/membership/redeem", json=body)
            assert res.status_code == 400

        res = client.post("/api/membership/redeem", json=body)

        assert res.status_code == 429
        assert "过于频繁" in res.json()["message"]


class TestMyRedemptions:
    def test_page_envelope_and_no_admin_fields(self, client, monkeypatch):
        """出参为 PageResult 结构；且不泄漏 usedBy / batchNo 等管理侧字段"""
        async def _fake_list(db, user_id, page, size):
            assert (user_id, page, size) == (1, 1, 10)
            return {"rows": [SimpleNamespace(
                id=9, code="A7KM2P9XQW4ZRT6B", days=30,
                used_at=datetime(2026, 10, 3, 16, 0, 0),
                created_at=datetime(2026, 10, 3, 15, 30, 0),
            )], "total": 1}

        monkeypatch.setattr(membership_crud, "list_user_redemptions", _fake_list)

        res = client.get("/api/membership/redemptions")

        assert res.status_code == 200
        data = res.json()["data"]
        assert (data["total"], data["pages"], data["current"], data["size"]) == (1, 1, 1, 10)

        row = data["records"][0]
        assert row["code"] == "A7KM2P9XQW4ZRT6B"
        assert row["days"] == 30
        assert row["usedAt"].startswith("2026-10-03T16:00:00")
        assert "usedBy" not in row and "batchNo" not in row

    def test_empty_records(self, client, monkeypatch):
        async def _fake_list(db, user_id, page, size):
            return {"rows": [], "total": 0}

        monkeypatch.setattr(membership_crud, "list_user_redemptions", _fake_list)

        data = client.get("/api/membership/redemptions").json()["data"]

        assert data == {"records": [], "total": 0, "pages": 0, "current": 1, "size": 10}
