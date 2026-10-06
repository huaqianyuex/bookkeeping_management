"""充值模块路由 — 用户侧 /api/recharge + 支付回调闸口 + 管理侧 /api/admin/recharges

实现规格：docs/fastapi-backend/11-充值与审批模块.md；两个 router 在 main.py 一并 include。

约定：
- 本模块走标准 {code, message, data} 信封（utils.response.success_response）；
  业务失败用 HTTPException（全局处理器转信封）；回调签名无效固定 401；
- 出参由 _order_out/_log_out 手工组包：金额 Decimal → 字符串（jsonable_encoder 会把
  Decimal 转 float，破坏金额口径，故不走 Pydantic ORM 序列化）；
- 状态机、风控、审计、验签逻辑全部在 crud.recharge / utils.recharge_security，
  本文件只做参数解析、鉴权、HTTP 语义映射——保持闸口薄、可审计。
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from config.db_config import get_db
from config.settings import MEMBERSHIP_PLANS, RECHARGE_PLANS
from crud import recharge as recharge_crud
from routers.membership import _benefits   # 权益 camelCase 映射单一来源（勿在两处各写一份）
from schemas.recharge import (
    MockPayIn,
    OrderCreateIn,
    PaymentCallbackIn,
    RechargeApproveIn,
    RechargeRejectIn,
)
from utils.auth import get_current_admin, get_current_user
from utils.recharge_security import build_payment_event, callback_sign
from utils.response import success_response

# 用户侧与管理侧分两个 router（prefix 不同、同一 tag 便于 Swagger 分组）
router = APIRouter(prefix="/api/recharge", tags=["recharge"])
admin_router = APIRouter(prefix="/api/admin/recharges", tags=["recharge"])

# 订单状态 → 用户可读文案（列表/详情 Tag 用；与管理端 Tag 口径一致）
STATUS_TEXT = {
    0: "待支付",
    1: "待审批",
    2: "已支付",
    3: "已拒绝",
    4: "已取消",
    5: "已关闭",
}


def _client_ip(request: Request) -> str:
    # ⚠️ request.client.host 在反向代理后恒为代理 IP（与登录限流同口径）
    return request.client.host if request.client else "unknown"


def _order_out(order, username: str | None = None) -> dict:
    """订单行出参（camelCase；金额转字符串保口径）"""
    data = {
        "id": order.id,
        "orderNo": order.order_no,
        "planId": order.plan_id,
        "planName": order.plan_name,
        "days": order.days,
        "amount": str(order.amount),
        "status": order.status,
        "statusText": STATUS_TEXT.get(order.status, str(order.status)),
        "payMethod": order.pay_method,
        "riskFlags": order.risk_flags,
        "paidAt": order.paid_at.isoformat() if order.paid_at else None,
        "reviewedAt": order.reviewed_at.isoformat() if order.reviewed_at else None,
        "reviewNote": order.review_note,
        "expiresAt": order.expires_at.isoformat() if order.expires_at else None,
        "createdAt": order.created_at.isoformat() if order.created_at else None,
    }
    if username is not None:
        data["userId"] = order.user_id
        data["username"] = username
    return data


def _log_out(log) -> dict:
    """审计行出参（camelCase）"""
    return {
        "id": log.id,
        "orderNo": log.order_no,
        "actorType": log.actor_type,
        "actorId": log.actor_id,
        "action": log.action,
        "fromStatus": log.from_status,
        "toStatus": log.to_status,
        "detail": log.detail,
        "ip": log.ip,
        "createdAt": log.created_at.isoformat() if log.created_at else None,
    }


# ── 用户侧 ──────────────────────────────────────────────────────────────

@router.get("/plans", summary="充值套餐目录")
async def list_plans(
    _: int = Depends(get_current_user),
):
    """服务端定价的套餐列表 + 两档权益矩阵——充值前信息展示（花多少钱/用多久/享什么）
    的唯一数据源，价格与额度均取自 settings，前端禁止硬编码。"""
    plans = [
        {"planId": pid, "name": p["name"], "days": p["days"], "price": p["price"]}
        for pid, p in RECHARGE_PLANS.items()
    ]
    return success_response(data={
        "plans": plans,
        "benefits": {
            "free": _benefits(MEMBERSHIP_PLANS[0]),
            "member": _benefits(MEMBERSHIP_PLANS[1]),
        },
    })


@router.post("/orders", summary="创建充值订单")
async def create_order(
    body: OrderCreateIn,
    request: Request,
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """只收 planId：金额/天数服务端定价并快照进订单；频率与进行中订单幂等校验在 crud。"""
    ok, msg, order = await recharge_crud.create_order(
        db, user_id, body.plan_id, _client_ip(request)
    )
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return success_response(message=msg, data=_order_out(order))


@router.post("/orders/{order_no}/mock-pay", summary="模拟收银台支付")
async def mock_pay(
    order_no: str,
    body: MockPayIn,
    request: Request,
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """模拟支付网关行为：服务端用回调密钥生成签名事件 → 走与真实回调完全相同的
    apply_payment_callback 处理路径（验签/金额核对/风控/审计一个不少）。

    真实渠道接入后，本端点由第三方收银台 + /callback 替代，代码零改动。
    """
    # 连续失败冷却：先于一切支付动作（防暴力重试/探测风控阈值）
    locked, retry_after = recharge_crud.pay_fail_throttle.is_locked(
        f"recharge:payfail:{user_id}"
    )
    if locked:
        raise HTTPException(status_code=429, detail=f"支付尝试过于频繁，请 {retry_after} 秒后重试")

    # 归属校验：只能支付自己的订单（回调路径无用户概念，签名即信任根；这里是用户路径）
    order = await recharge_crud.get_user_order(db, user_id, order_no)
    if order is None:
        raise HTTPException(status_code=404, detail="订单不存在")

    # 服务端模拟"网关"生成签名事件（密钥不出服务端），再走统一回调处理
    amount = str(order.amount)
    sign = callback_sign(order_no, amount, body.result)
    event = build_payment_event(order_no, amount, body.result, sign)
    if event is None:   # 理论不可达（签名刚生成），防御性兜底
        raise HTTPException(status_code=401, detail="回调签名无效")

    ok, msg, order = await recharge_crud.apply_payment_callback(
        db, event, _client_ip(request)
    )
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return success_response(message=msg, data=_order_out(order))


@router.post("/orders/{order_no}/cancel", summary="取消待支付订单")
async def cancel_order(
    order_no: str,
    request: Request,
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ok, msg = await recharge_crud.cancel_order(db, order_no, user_id, _client_ip(request))
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return success_response(message=msg)


@router.get("/orders", summary="我的充值记录")
async def list_my_orders(
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
):
    """当前用户的充值订单分页（id 倒序，PageResult 结构）。"""
    result = await recharge_crud.list_user_orders(db, user_id, page, size)
    total = result["total"]
    return success_response(data={
        "records": [_order_out(r) for r in result["rows"]],
        "total": total,
        "pages": (total + size - 1) // size,
        "current": page,
        "size": size,
    })


@router.get("/orders/{order_no}", summary="订单详情")
async def get_order(
    order_no: str,
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """归属校验在 crud 查询条件里，跨用户查询一律 404（不暴露订单存在性）。"""
    order = await recharge_crud.get_user_order(db, user_id, order_no)
    if order is None:
        raise HTTPException(status_code=404, detail="订单不存在")
    return success_response(data=_order_out(order))


# ── 支付回调闸口（真实渠道适配器与模拟网关共用）────────────────────────

@router.post("/callback", summary="支付网关回调")
async def payment_callback(
    body: PaymentCallbackIn,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """唯一能把订单推进到「已支付/待审批」的 HTTP 闸口：HMAC 验签 → 金额核对 →
    行锁状态机 → 审计。签名无效固定 401（客户端无密钥，无法伪造支付成功）。"""
    event = build_payment_event(body.order_no, body.amount, body.status, body.sign)
    if event is None:
        raise HTTPException(status_code=401, detail="回调签名无效")
    ok, msg, order = await recharge_crud.apply_payment_callback(
        db, event, _client_ip(request)
    )
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return success_response(message=msg, data=_order_out(order))


# ── 管理侧（审批）───────────────────────────────────────────────────────

@admin_router.get("", summary="充值订单列表（管理端）")
async def admin_list_orders(
    _: int = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    status: int | None = Query(None, description="0待支付 1待审批 2已支付 3已拒绝 4已取消 5已关闭；缺省全部"),
    keyword: str | None = Query(None, max_length=64, description="用户名/订单号/套餐名模糊"),
):
    """订单分页 + 筛选；审批工作台默认按 status=1 过滤使用。"""
    if status is not None and status not in (0, 1, 2, 3, 4, 5):
        raise HTTPException(status_code=400, detail="参数错误")
    result = await recharge_crud.admin_list_orders(db, page, size, status, keyword)
    total = result["total"]
    return success_response(data={
        "records": [_order_out(order, username) for order, username in result["rows"]],
        "total": total,
        "pages": (total + size - 1) // size,
        "current": page,
        "size": size,
    })


@admin_router.get("/{order_id}/logs", summary="订单审计轨迹")
async def admin_order_logs(
    order_id: int,
    _: int = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """某订单全链路审计时间线（创建/支付/风控/审批/延期，append-only）。"""
    if await recharge_crud.get_order_by_id(db, order_id) is None:
        raise HTTPException(status_code=404, detail="订单不存在")
    logs = await recharge_crud.list_order_logs(db, order_id)
    return success_response(data={"records": [_log_out(l) for l in logs]})


@admin_router.post("/{order_id}/approve", summary="通过待审批订单")
async def admin_approve(
    order_id: int,
    request: Request,
    body: RechargeApproveIn | None = None,
    admin_id: int = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """放行到账：状态流转 + 审计 + 会员延期同一事务（风控拦截的订单到此终审）。"""
    note = body.note if body else None
    ok, msg = await recharge_crud.approve_order(
        db, order_id, admin_id, note, _client_ip(request)
    )
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return success_response(message=msg)


@admin_router.post("/{order_id}/reject", summary="拒绝待审批订单")
async def admin_reject(
    order_id: int,
    body: RechargeRejectIn,
    request: Request,
    admin_id: int = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """拒绝：原因必填（schema 层校验），写入订单 review_note 与审计留痕。"""
    ok, msg = await recharge_crud.reject_order(
        db, order_id, admin_id, body.reason, _client_ip(request)
    )
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return success_response(message=msg)
