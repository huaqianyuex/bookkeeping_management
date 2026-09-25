"""管理后台相关 Pydantic 模型

字段命名规则与 schemas/record.py 一致：Python 字段名 snake_case，
对外 JSON 键 camelCase（靠 alias），*Out 类继承 OrmBase。
"""

import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, Field

from schemas.base import OrmBase


class UserStatusUpdate(BaseModel):
    """用户状态更新"""
    status: int = Field(..., ge=0, le=1, description="0=禁用 1=启用")


class IdsIn(BaseModel):
    """批量删除请求体（用户 / 账单共用，10-实现骨架.md §5.4/§5.6）"""
    ids: List[int] = Field(..., min_length=1, description="主键数组，单次建议 ≤ 50")


class AdminUserOut(OrmBase):
    """管理端用户出参（UserVO）"""
    id: int
    username: str
    avatar: Optional[str] = Field(None, alias="avatarUrl")
    role: int = Field(0, description="0=普通用户 1=管理员")
    status: int = Field(1, description="0=禁用 1=启用")
    created_at: Optional[datetime.datetime] = Field(None, alias="createTime")
    updated_at: Optional[datetime.datetime] = Field(None, alias="updateTime")


class FaqIn(BaseModel):
    """FAQ 新增/更新请求体（更新时字段可省略）"""
    question: Optional[str] = Field(None, min_length=1, description="问题")
    answer: Optional[str] = Field(None, min_length=1, description="回答")
    category: Optional[str] = Field(None, min_length=1, max_length=50, description="分类标签")


class FaqOut(OrmBase):
    """FAQ 出参"""
    id: int
    question: str
    answer: str
    category: str


class AdminRecordOut(OrmBase):
    """管理端账单出参（AdminRecordVO）

    与用户侧 RecordOut 的差异：多 `username`（联表 users 得出）、无 `updateTime`。
    """
    id: int
    user_id: int = Field(..., alias="userId")
    username: Optional[str] = Field(None, description="联表 users.username")
    category_id: int = Field(..., alias="categoryId")
    category_name: Optional[str] = Field(None, alias="categoryName")
    category_type: Optional[int] = Field(None, alias="categoryType", description="0=支出 1=收入")
    type: int = Field(..., description="0=支出 1=收入")
    amount: Decimal = Field(..., description="金额，定点 2 位")
    date: datetime.date = Field(..., alias="recordDate")
    remark: Optional[str] = None
    created_at: Optional[datetime.datetime] = Field(None, alias="createTime")
