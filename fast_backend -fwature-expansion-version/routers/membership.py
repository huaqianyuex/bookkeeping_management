"""会员模块路由 — 用户侧 /api/membership + 管理侧 /api/admin/membership

实现规格：docs/membership-plan.md §6 / 10-实现骨架.md §七；两个 router 在 main.py 一并 include。

约定：
- 本模块走标准 {code, message, data} 信封（utils.response.success_response），
  与 AI 模块裸 JSON 契约无关；业务失败用 HTTPException（全局处理器转信封）；
- 权益数值唯一来源 config.settings.MEMBERSHIP_PLANS，不在此硬编码；
- 过期惰性降级：tier 判定只走 crud.membership.get_tier() 单一入口；
- AI 消费点的配额闸门（/api/ai/** 的 429 裸 JSON QUOTA_EXCEEDED）见 routers/ai.py::_quota_gate。
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from config.db_config import get_db
from config.settings import MEMBERSHIP_PLANS
from crud import membership as membership_crud
from schemas.membership import (
    CodeGenerateIn,
    GrantIn,
    MembershipCodeOut,
    MembershipStatusOut,
    RedeemIn,
)
from utils.auth import get_current_admin, get_current_user
from utils.response import success_response

# 用户侧与管理侧分两个 router（prefix 不同、同一 tag 便于 Swagger 分组）
router = APIRouter(prefix="/api/membership", tags=["membership"])
admin_router = APIRouter(prefix="/api/admin/membership", tags=["membership"])


def _benefits(plan: dict) -> dict:
    """权益矩阵转 camelCase 下发（前端按 dailyChat/premiumModel 读取，勿泄漏 `_` 键）。

    数值仍全部取自 MEMBERSHIP_PLANS（本函数只做键名映射，不硬编码任何额度）；
    键名与 10-实现骨架.md §7.1 响应示例一致。
    """
    return {
        "dailyChat": plan["daily_chat"],
        "concurrency": plan["concurrency"],
        "dailyAnalyze": plan["daily_analyze"],
        "dailyBookkeeping": plan["daily_bookkeeping"],
        "premiumModel": plan["premium_model"],
    }


@router.get("/status", summary="我的会员状态与今日用量")
async def membership_status(
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """等级 + 到期时间 + 今日用量 + 权益矩阵（会员中心与 AI 页额度角标的数据源）。

    benefits 原样下发 MEMBERSHIP_PLANS[tier]，前端权益表动态渲染、不硬编码数值；
    查不到会员行/用量行都按免费与 0 组包，本接口无业务失败分支。
    """
    tier = await membership_crud.get_tier(db, user_id)
    plan = MEMBERSHIP_PLANS[tier]
    membership = await membership_crud.get_effective_membership(db, user_id)
    usage_row = await membership_crud.get_usage_row(db, user_id)

    def _item(kind: str) -> dict:
        used = getattr(usage_row, f"{kind}_count", 0) if usage_row is not None else 0
        return {"used": used or 0, "limit": plan[f"daily_{kind}"]}

    data = MembershipStatusOut(
        tier=tier,
        tier_name=plan["name"],
        expires_at=membership.expires_at.isoformat() if membership else None,
        benefits=_benefits(plan),
        usage={
            "date": datetime.now().strftime("%Y-%m-%d"),
            "chat": _item("chat"),
            "analyze": _item("analyze"),
            "bookkeeping": _item("bookkeeping"),
        },
    ).model_dump(by_alias=True)
    return success_response(data=data)


@router.post("/redeem", summary="兑换码开通/续费")
async def redeem(
    body: RedeemIn,
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """兑换码核销：叠加语义从 max(NOW, 现有到期) 起加天数（未过期续费不损失剩余天数）。"""
    ok, msg, membership = await membership_crud.redeem_code(db, user_id, body.code)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return success_response(message=msg, data={
        "tier": 1,
        "expiresAt": membership.expires_at.isoformat() if membership else None,
    })


@admin_router.post("/codes", summary="批量生成兑换码")
async def generate_codes(
    body: CodeGenerateIn,
    _: int = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """批量生成（count 1-500、days 1-3650 由 schema 校验）。"""
    rows = await membership_crud.generate_codes(db, body.count, body.days, body.batch_no)
    return success_response(message=f"已生成 {len(rows)} 张兑换码", data={
        "batchNo": rows[0].batch_no if rows else None,
        "codes": [MembershipCodeOut.model_validate(r).model_dump(by_alias=True) for r in rows],
    })


@admin_router.get("/codes", summary="兑换码列表")
async def list_codes(
    _: int = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    status: int | None = Query(None, description="0未使用 1已使用 2已作废；缺省全部"),
):
    """兑换码分页列表（id 倒序，PageResult 结构）。"""
    if status is not None and status not in (0, 1, 2):
        raise HTTPException(status_code=400, detail="参数错误")
    result = await membership_crud.list_codes(db, page, size, status)
    total = result["total"]
    return success_response(data={
        "records": [
            MembershipCodeOut.model_validate(r).model_dump(by_alias=True) for r in result["rows"]
        ],
        "total": total,
        "pages": (total + size - 1) // size,
        "current": page,
        "size": size,
    })


@admin_router.put("/codes/{code_id}/void", summary="作废兑换码")
async def void_code(
    code_id: int,
    _: int = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """作废：仅未使用（status=0）可作废。"""
    ok, msg = await membership_crud.void_code(db, code_id)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return success_response(message=msg)


@admin_router.post("/grant", summary="手动开通/延期会员")
async def grant(
    body: GrantIn,
    _: int = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """管理员开通/延期（叠加语义）；用户不存在返回 404（会员模块有意选择）。"""
    membership = await membership_crud.grant_membership(db, body.user_id, body.days)
    if membership is None:
        raise HTTPException(status_code=404, detail="用户不存在")
    return success_response(
        message=f"已为用户 {body.user_id} 开通/延期 {body.days} 天",
        data={
            "tier": membership.tier,
            "expiresAt": membership.expires_at.isoformat() if membership.expires_at else None,
        },
    )
