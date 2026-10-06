"""充值模块测试 — 套餐定价 / 回调验签闸口 / 下单防刷 / 审批权限 / 出参口径

规格：docs/fastapi-backend/11-充值与审批模块.md §测试清单。
约定：不连真实 MySQL。路由流程用 dependency_overrides + monkeypatch
（照 tests/test_membership.py 模式），纯逻辑（签名/事件构造）用普通断言。

覆盖的防绕过要点：
- 服务端定价：/plans 与 RECHARGE_PLANS 一致，价格 Decimal 可解析且为正；
- 回调闸口：坏签名/篡改金额/非法 status 一律 401，永远到不了状态机；
- 归属校验：mock-pay 查无此单（含跨用户）404；
- 审批权限：role!=1 一律 403，拒绝原因必填（schema 层 422）；
- 进程内防刷器用例间由 conftest 清理（见 _reset_in_memory_throttles）。
"""

from datetime import datetime
from decimal import Decimal
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from config.db_config import get_db
from config.settings import MEMBERSHIP_PLANS, RECHARGE_PLANS
from crud import recharge as recharge_crud
from main import app
from utils import auth as auth_utils
from utils.auth import get_current_user
from utils.recharge_security import (
    PaymentEvent,
    build_payment_event,
    callback_sign,
    verify_callback_sign,
)


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
    """登录态客户端：固定 user_id=1（get_current_user 整体覆写，不触库）"""
    async def _override_get_db():
        yield FakeDB()

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = lambda: 1
    with TestClient(app) as c:      # with 触发 lifespan，与 test_app.py 一致
        c.get("/api/health")
        yield c
    app.dependency_overrides.clear()


def _patch_admin_ok(monkeypatch, role: int = 1):
    """打桩 users 查询，让 get_current_admin 的 role 判定可控（同 test_membership）"""
    async def _fake_get_user(db, user_id):
        return SimpleNamespace(id=user_id, role=role, status=1)

    monkeypatch.setattr(auth_utils, "get_user_by_id", _fake_get_user)


def _order_stub(**overrides) -> SimpleNamespace:
    """订单行桩：字段与 _order_out 输出对齐"""
    base = dict(
        id=1, order_no="RCH20261006000000ABCDEF", user_id=1,
        plan_id="month", plan_name="月卡", days=30, amount=Decimal("18.00"),
        status=0, pay_method=0, risk_flags=None, client_ip="127.0.0.1",
        paid_at=None, reviewed_by=None, reviewed_at=None, review_note=None,
        expires_at=datetime(2026, 10, 6, 12, 15, 0),
        created_at=datetime(2026, 10, 6, 12, 0, 0),
    )
    base.update(overrides)
    return SimpleNamespace(**base)


class TestPaymentSignature:
    """HMAC 签名与事件构造：验签闸口的纯逻辑单测"""

    def test_sign_verify_roundtrip(self):
        sign = callback_sign("RCH1", "18.00", "success")
        assert verify_callback_sign("RCH1", "18.00", "success", sign)

    def test_tampered_amount_rejected(self):
        sign = callback_sign("RCH1", "18.00", "success")
        assert not verify_callback_sign("RCH1", "0.01", "success", sign)

    def test_tampered_order_no_rejected(self):
        sign = callback_sign("RCH1", "18.00", "success")
        assert not verify_callback_sign("RCH2", "18.00", "success", sign)

    def test_build_event_rejects_bad_sign(self):
        assert build_payment_event("RCH1", "18.00", "success", "0" * 64) is None

    def test_build_event_rejects_illegal_status(self):
        # status 不在白名单：即便签名"正确"也拒绝（签名对非法串可被攻击者自己计算）
        sign = callback_sign("RCH1", "18.00", "paid")
        assert build_payment_event("RCH1", "18.00", "paid", sign) is None

    def test_build_event_ok_returns_frozen_event(self):
        sign = callback_sign("RCH1", "18.00", "success")
        event = build_payment_event("RCH1", "18.00", "success", sign)
        assert isinstance(event, PaymentEvent)
        assert event.order_no == "RCH1" and event.amount == "18.00"
        with pytest.raises(Exception):
            event.amount = "0.01"   # frozen：状态机输入不可被篡改


class TestPlanCatalog:
    """服务端定价：前端拿到的就是唯一的定价源"""

    def test_plans_from_settings(self, client):
        res = client.get("/api/recharge/plans")
        assert res.status_code == 200
        plans = res.json()["data"]["plans"]
        assert {p["planId"] for p in plans} == set(RECHARGE_PLANS.keys())
        for p in plans:
            src = RECHARGE_PLANS[p["planId"]]
            assert p["name"] == src["name"]
            assert p["days"] == src["days"]
            assert p["price"] == src["price"]

    def test_plans_include_tier_benefits(self, client):
        """充值前权益展示的数据源：两档权益矩阵随套餐下发，前端不硬编码额度"""
        res = client.get("/api/recharge/plans")
        assert res.status_code == 200
        b = res.json()["data"]["benefits"]
        assert b["member"]["dailyChat"] == MEMBERSHIP_PLANS[1]["daily_chat"]
        assert b["member"]["concurrency"] == MEMBERSHIP_PLANS[1]["concurrency"]
        assert b["member"]["premiumModel"] == MEMBERSHIP_PLANS[1]["premium_model"]
        assert b["free"]["dailyChat"] == MEMBERSHIP_PLANS[0]["daily_chat"]
        assert b["free"]["premiumModel"] == MEMBERSHIP_PLANS[0]["premium_model"]

    def test_prices_are_positive_decimals(self):
        """价格必须是可解析、为正的 Decimal 字符串（禁 float 口径）"""
        for pid, p in RECHARGE_PLANS.items():
            assert Decimal(p["price"]) > 0, f"{pid} 价格非法"
            assert int(p["days"]) > 0, f"{pid} 天数非法"

    def test_plans_requires_login(self):
        async def _override_get_db():
            yield FakeDB()

        app.dependency_overrides[get_db] = _override_get_db
        try:
            with TestClient(app) as c:
                res = c.get("/api/recharge/plans")
                assert res.status_code == 401
        finally:
            app.dependency_overrides.clear()


class TestCreateOrder:
    """下单：服务端定价 + 幂等/防刷提示透传"""

    def test_unknown_plan_rejected(self, client):
        # 套餐目录是 settings 查询，触库前即拒绝（FakeDB 未打桩也不会报错）
        res = client.post("/api/recharge/orders", json={"planId": "hack-plan"})
        assert res.status_code == 400
        assert "套餐不存在" in res.json()["message"]

    def test_create_ok_returns_snapshot(self, client, monkeypatch):
        captured = {}

        async def _fake_create(db, user_id, plan_id, ip):
            captured["args"] = (user_id, plan_id, ip)
            return True, "订单已创建，请在 15 分钟内完成支付", _order_stub()

        monkeypatch.setattr(recharge_crud, "create_order", _fake_create)
        res = client.post("/api/recharge/orders", json={"planId": "month"})
        assert res.status_code == 200
        assert captured["args"][1] == "month"
        data = res.json()["data"]
        assert data["amount"] == "18.00"          # Decimal → 字符串，非 float
        assert data["status"] == 0 and data["statusText"] == "待支付"
        assert data["orderNo"].startswith("RCH")

    def test_create_blocked_by_pending_limit(self, client, monkeypatch):
        async def _fake_create(db, user_id, plan_id, ip):
            return False, "您已有待支付的订单，请先完成支付或取消", None

        monkeypatch.setattr(recharge_crud, "create_order", _fake_create)
        res = client.post("/api/recharge/orders", json={"planId": "month"})
        assert res.status_code == 400
        assert "待支付" in res.json()["message"]


class TestCallbackGate:
    """/api/recharge/callback：唯一入账闸口，验签必须在状态机之前"""

    def test_bad_sign_401(self, client):
        res = client.post("/api/recharge/callback", json={
            "orderNo": "RCH1", "amount": "18.00", "status": "success", "sign": "0" * 64,
        })
        assert res.status_code == 401
        assert "签名" in res.json()["message"]

    def test_tampered_amount_401(self, client):
        """签名对 18.00、报文改 0.01：伪造改单在闸口被拦（到不了 crud）"""
        sign = callback_sign("RCH1", "18.00", "success")
        res = client.post("/api/recharge/callback", json={
            "orderNo": "RCH1", "amount": "0.01", "status": "success", "sign": sign,
        })
        assert res.status_code == 401

    def test_valid_sign_reaches_state_machine(self, client, monkeypatch):
        sign = callback_sign("RCHOK", "18.00", "success")
        events = []

        async def _fake_apply(db, event, ip):
            events.append(event)
            return True, "支付成功，会员已延长 30 天", _order_stub(status=2, paid_at=datetime(2026, 10, 6, 12, 1, 0))

        monkeypatch.setattr(recharge_crud, "apply_payment_callback", _fake_apply)
        res = client.post("/api/recharge/callback", json={
            "orderNo": "RCHOK", "amount": "18.00", "status": "success", "sign": sign,
        })
        assert res.status_code == 200
        assert len(events) == 1
        assert events[0].status == "success"

    def test_business_failure_maps_to_400(self, client, monkeypatch):
        sign = callback_sign("RCH1", "18.00", "fail")

        async def _fake_apply(db, event, ip):
            return False, "订单不存在", None

        monkeypatch.setattr(recharge_crud, "apply_payment_callback", _fake_apply)
        res = client.post("/api/recharge/callback", json={
            "orderNo": "RCH1", "amount": "18.00", "status": "fail", "sign": sign,
        })
        assert res.status_code == 400


class TestMockPay:
    """模拟收银台：归属校验 + 同一回调处理路径"""

    def test_pay_own_order_success(self, client, monkeypatch):
        order = _order_stub()
        applied = []

        async def _fake_get(db, user_id, order_no):
            assert (user_id, order_no) == (1, "RCH1")
            return order

        async def _fake_apply(db, event, ip):
            applied.append(event)
            return True, "支付成功，会员已延长 30 天", _order_stub(status=2, paid_at=datetime(2026, 10, 6, 12, 1, 0))

        monkeypatch.setattr(recharge_crud, "get_user_order", _fake_get)
        monkeypatch.setattr(recharge_crud, "apply_payment_callback", _fake_apply)
        res = client.post("/api/recharge/orders/RCH1/mock-pay", json={"result": "success"})
        assert res.status_code == 200
        assert applied[0].order_no == "RCH1" and applied[0].status == "success"

    def test_pay_other_users_order_404(self, client, monkeypatch):
        async def _fake_get(db, user_id, order_no):
            return None   # 归属校验不通过（跨用户/不存在同路径）

        monkeypatch.setattr(recharge_crud, "get_user_order", _fake_get)
        res = client.post("/api/recharge/orders/RCH1/mock-pay", json={"result": "success"})
        assert res.status_code == 404

    def test_pay_failure_maps_to_400(self, client, monkeypatch):
        async def _fake_get(db, user_id, order_no):
            return _order_stub()

        async def _fake_apply(db, event, ip):
            assert event.status == "fail"
            return False, "支付未完成，如需开通请重新发起支付", _order_stub()

        monkeypatch.setattr(recharge_crud, "get_user_order", _fake_get)
        monkeypatch.setattr(recharge_crud, "apply_payment_callback", _fake_apply)
        res = client.post("/api/recharge/orders/RCH1/mock-pay", json={"result": "fail"})
        assert res.status_code == 400

    def test_pay_fail_cooldown_kicks_in(self, client):
        """真实防刷器：连续失败达到阈值后进入冷却（conftest 用例间清空）"""
        key = "recharge:payfail:999"
        for _ in range(recharge_crud.pay_fail_throttle.max_fails):
            recharge_crud.pay_fail_throttle.record_fail(key)
        locked, retry_after = recharge_crud.pay_fail_throttle.is_locked(key)
        assert locked and retry_after > 0


class TestMyOrders:
    """我的充值记录：归属过滤 + 金额口径"""

    def test_list_ok(self, client, monkeypatch):
        async def _fake_list(db, user_id, page, size):
            assert user_id == 1
            return {"rows": [_order_stub()], "total": 1}

        monkeypatch.setattr(recharge_crud, "list_user_orders", _fake_list)
        res = client.get("/api/recharge/orders?page=1&size=20")
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["total"] == 1 and data["current"] == 1
        assert data["records"][0]["amount"] == "18.00"


class TestAdminApproval:
    """管理端审批：角色权限 / 参数校验 / 出参"""

    def test_approve_requires_admin_role(self, client, monkeypatch):
        _patch_admin_ok(monkeypatch, role=0)
        res = client.post("/api/admin/recharges/1/approve")
        assert res.status_code == 403

    def test_reject_requires_admin_role(self, client, monkeypatch):
        _patch_admin_ok(monkeypatch, role=0)
        res = client.post("/api/admin/recharges/1/reject", json={"reason": "x"})
        assert res.status_code == 403

    def test_approve_ok(self, client, monkeypatch):
        _patch_admin_ok(monkeypatch, role=1)
        captured = {}

        async def _fake_approve(db, order_id, admin_id, note, ip):
            captured["args"] = (order_id, admin_id, note)
            return True, "已通过，会员已延长 90 天"

        monkeypatch.setattr(recharge_crud, "approve_order", _fake_approve)
        res = client.post("/api/admin/recharges/7/approve", json={"note": "核实无误"})
        assert res.status_code == 200
        assert captured["args"] == (7, 1, "核实无误")   # admin_id 来自 get_current_admin

    def test_approve_business_reject_maps_to_400(self, client, monkeypatch):
        _patch_admin_ok(monkeypatch, role=1)

        async def _fake_approve(db, order_id, admin_id, note, ip):
            return False, "仅待审批订单可执行通过操作"

        monkeypatch.setattr(recharge_crud, "approve_order", _fake_approve)
        res = client.post("/api/admin/recharges/7/approve", json={})
        assert res.status_code == 400

    def test_reject_requires_reason(self, client, monkeypatch):
        _patch_admin_ok(monkeypatch, role=1)
        res = client.post("/api/admin/recharges/7/reject", json={})
        assert res.status_code == 422   # schema 层必填校验

    def test_reject_ok(self, client, monkeypatch):
        _patch_admin_ok(monkeypatch, role=1)
        captured = {}

        async def _fake_reject(db, order_id, admin_id, reason, ip):
            captured["args"] = (order_id, admin_id, reason)
            return True, "已拒绝，模拟支付款项将原路退回"

        monkeypatch.setattr(recharge_crud, "reject_order", _fake_reject)
        res = client.post("/api/admin/recharges/7/reject", json={"reason": "异常交易"})
        assert res.status_code == 200
        assert captured["args"] == (7, 1, "异常交易")

    def test_admin_list_invalid_status_400(self, client, monkeypatch):
        _patch_admin_ok(monkeypatch, role=1)
        res = client.get("/api/admin/recharges?status=9")
        assert res.status_code == 400

    def test_admin_list_ok(self, client, monkeypatch):
        _patch_admin_ok(monkeypatch, role=1)

        async def _fake_list(db, page, size, status, keyword):
            assert status == 1
            return {"rows": [(_order_stub(status=1, risk_flags="SINGLE_AMOUNT"), "alice")], "total": 1}

        monkeypatch.setattr(recharge_crud, "admin_list_orders", _fake_list)
        res = client.get("/api/admin/recharges?status=1")
        assert res.status_code == 200
        record = res.json()["data"]["records"][0]
        assert record["username"] == "alice"
        assert record["statusText"] == "待审批"

    def test_admin_logs_ok_and_404(self, client, monkeypatch):
        _patch_admin_ok(monkeypatch, role=1)
        log = SimpleNamespace(
            id=3, order_no="RCH1", actor_type=2, actor_id=1, action="APPROVE",
            from_status=1, to_status=2, detail="ok", ip="127.0.0.1",
            created_at=datetime(2026, 10, 6, 13, 0, 0),
        )

        async def _fake_get(db, order_id):
            return _order_stub(id=order_id) if order_id == 1 else None

        async def _fake_logs(db, order_id):
            return [log]

        monkeypatch.setattr(recharge_crud, "get_order_by_id", _fake_get)
        monkeypatch.setattr(recharge_crud, "list_order_logs", _fake_logs)
        res = client.get("/api/admin/recharges/1/logs")
        assert res.status_code == 200
        assert res.json()["data"]["records"][0]["action"] == "APPROVE"

        res = client.get("/api/admin/recharges/404/logs")
        assert res.status_code == 404
