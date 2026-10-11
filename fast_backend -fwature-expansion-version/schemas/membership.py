"""会员模块 Pydantic 模型（骨架：完整声明，无逻辑）

实现规格：docs/membership-plan.md §4.1。
命名沿用项目约定：字段 snake_case + alias camelCase；*Out 继承 OrmBase（ORM 派生），
组合型出参（MembershipStatusOut/RedeemOut 等）为服务端组包，用 populate_by_name。
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from schemas.base import OrmBase


class UsageItem(BaseModel):
    """单项配额的今日用量"""

    used: int = Field(..., description="今日已用")
    limit: int = Field(..., description="今日上限")


class MembershipStatusOut(BaseModel):
    """GET /api/membership/status 出参（服务端查库组包，前端不传任何数值）"""

    tier: int = Field(0, description="生效等级：0=免费 1=会员（过期惰性降级）")
    tier_name: str = Field("免费版", alias="tierName")
    expires_at: Optional[str] = Field(None, alias="expiresAt", description="到期 ISO 时间；免费为 null")
    benefits: dict = Field(..., description="权益矩阵（MEMBERSHIP_PLANS[tier] 原样下发）")
    usage: dict = Field(
        ...,
        description="{date, chat: UsageItem, analyze: UsageItem, bookkeeping: UsageItem}",
    )

    model_config = ConfigDict(populate_by_name=True)


class RedeemIn(BaseModel):
    """POST /api/membership/redeem 入参"""

    code: str = Field(
        ..., min_length=4, max_length=32,
        description="兑换码；服务端归一化（去空格/连字符、转大写）",
    )


class RedeemOut(BaseModel):
    """兑换/开通成功出参"""

    tier: int = 1
    expires_at: Optional[str] = Field(None, alias="expiresAt")

    model_config = ConfigDict(populate_by_name=True)


class MembershipCodeOut(OrmBase):
    """兑换码行出参（ORM 派生）"""

    id: int
    code: str = Field(..., description="16 位大写字母数字，去除 0/O/1/I 防歧义")
    days: int
    status: int = Field(0, description="0=未使用 1=已使用 2=已作废")
    batch_no: Optional[str] = Field(None, alias="batchNo")
    used_by: Optional[int] = Field(None, alias="usedBy")
    used_at: Optional[datetime] = Field(None, alias="usedAt")
    created_at: Optional[datetime] = Field(None, alias="createdAt")


class UserRedemptionOut(OrmBase):
    """GET /api/membership/redemptions 行出参（普通用户视角的兑换记录）

    刻意**不含** usedBy（就是本人）与 batchNo（运营内部批次号，对用户无意义），
    避免把管理侧字段泄漏到用户侧接口。
    """

    id: int
    code: str = Field(..., description="核销时使用的兑换码原文")
    days: int = Field(..., description="该码开通的会员天数")
    used_at: Optional[datetime] = Field(None, alias="usedAt", description="核销时间")
    created_at: Optional[datetime] = Field(None, alias="createdAt", description="兑换码生成时间")


class CodeGenerateIn(BaseModel):
    """POST /api/admin/membership/codes 入参"""

    count: int = Field(..., ge=1, le=500, description="生成数量，1-500")
    days: int = Field(..., ge=1, le=3650, description="每张兑换天数，1-3650")
    batch_no: Optional[str] = Field(
        None, alias="batchNo", max_length=32, description="批次号；缺省用生成时间戳"
    )

    model_config = ConfigDict(populate_by_name=True)


class CodeGenerateOut(BaseModel):
    """批量生成出参"""

    batch_no: Optional[str] = Field(None, alias="batchNo")
    codes: List[MembershipCodeOut] = Field(default_factory=list)

    model_config = ConfigDict(populate_by_name=True)


class GrantIn(BaseModel):
    """POST /api/admin/membership/grant 入参"""

    user_id: int = Field(..., alias="userId", ge=1, description="目标用户 ID")
    days: int = Field(..., ge=1, le=3650, description="叠加天数（从 max(NOW, 现有到期) 起算）")

    model_config = ConfigDict(populate_by_name=True)
