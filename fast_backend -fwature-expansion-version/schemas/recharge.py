"""充值模块 Pydantic 模型

命名沿用项目约定：字段 snake_case + alias camelCase。
出参（订单/审计行）由路由层 _order_out()/_log_out() 手工组包（金额 Decimal → 字符串，
避免 jsonable_encoder 把 Decimal 转 float 破坏金额口径），故本文件只有入参模型。
"""

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class RechargePlanOut(BaseModel):
    """GET /api/recharge/plans 单个套餐（服务端定价快照，客户端禁止传金额）"""

    plan_id: str = Field(..., alias="planId", description="套餐 ID，下单只传它")
    name: str = Field(..., description="套餐名称")
    days: int = Field(..., description="会员天数")
    price: str = Field(..., description="价格（元，字符串承载 Decimal）")

    model_config = ConfigDict(populate_by_name=True)


class OrderCreateIn(BaseModel):
    """POST /api/recharge/orders 入参 — 只传套餐 ID，金额/天数服务端定价"""

    plan_id: str = Field(
        ..., alias="planId", min_length=1, max_length=32,
        description="套餐 ID（RECHARGE_PLANS 目录键）",
    )

    model_config = ConfigDict(populate_by_name=True)


class MockPayIn(BaseModel):
    """POST /api/recharge/orders/{orderNo}/mock-pay 入参（模拟收银台行为）"""

    result: Literal["success", "fail"] = Field(
        "success", description="success=模拟支付成功 fail=模拟失败/取消（演示风控计数）"
    )


class PaymentCallbackIn(BaseModel):
    """POST /api/recharge/callback 入参 — 支付网关回调事件（HMAC-SHA256 签名）"""

    order_no: str = Field(..., alias="orderNo", min_length=1, max_length=32, description="订单号")
    amount: str = Field(..., min_length=1, description="网关实收金额原串（签名覆盖）")
    status: Literal["success", "fail"] = Field(..., description="网关侧支付结果")
    sign: str = Field(..., min_length=1, description="HMAC-SHA256 签名（callback_sign 口径）")

    model_config = ConfigDict(populate_by_name=True)


class RechargeApproveIn(BaseModel):
    """POST /api/admin/recharges/{id}/approve 入参（可选备注）"""

    note: Optional[str] = Field(None, max_length=200, description="审批备注（可空）")


class RechargeRejectIn(BaseModel):
    """POST /api/admin/recharges/{id}/reject 入参（原因必填，写入订单与审计）"""

    reason: str = Field(..., min_length=1, max_length=200, description="拒绝原因（必填）")
