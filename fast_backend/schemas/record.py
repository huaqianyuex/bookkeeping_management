"""记账记录相关 Pydantic 模型

⚠️ 字段命名规则（见 02 §0 / 03 §7）：
  Python 字段名用 snake_case，**对外 JSON 键用 camelCase**（靠 alias）。
  字段名必须与 ORM 属性名一致（`date`、`category_id`），否则 `model_validate(orm)` 取不到值。

日期字段固定用 `date`（ORM 属性名）+ `alias="recordDate"`：
  前端 Web（Records.jsx / AdminRecords.jsx）与 uni-app（records/index、records/add-edit）
  全部读 `recordDate`，**不能输出成 `date`**，否则列表日期列空白、uni-app 分组直接崩。
"""

import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from schemas.base import OrmBase

MAX_AMOUNT = Decimal("99999999.99")


class RecordCreate(BaseModel):
    """创建记账记录请求"""
    category_id: int = Field(..., alias="categoryId", description="分类ID")
    amount: Decimal = Field(..., gt=0, le=MAX_AMOUNT, description="金额")
    date: datetime.date = Field(..., alias="recordDate", description="日期")
    remark: Optional[str] = Field(None, max_length=200, description="备注")
    # 手工记账时前端不传 type，由所选分类的 type 推导；AI 记账会显式传
    type: Optional[int] = Field(None, description="类型：0支出 1收入；不传则由分类推导")

    model_config = ConfigDict(populate_by_name=True)


class RecordUpdate(BaseModel):
    """更新记账记录请求"""
    category_id: Optional[int] = Field(None, alias="categoryId", description="分类ID")
    amount: Optional[Decimal] = Field(None, gt=0, le=MAX_AMOUNT, description="金额")
    date: Optional[datetime.date] = Field(None, alias="recordDate", description="日期")
    remark: Optional[str] = Field(None, max_length=200, description="备注")
    type: Optional[int] = Field(None, description="类型：0支出 1收入；不传则由分类推导")

    model_config = ConfigDict(populate_by_name=True)


class RecordOut(OrmBase):
    """记账记录输出（RecordVO）

    字段名与 ORM 属性一一对应，序列化时由 alias 输出 camelCase：
    categoryName / categoryType 由 `record LEFT JOIN category` 得出，库表不冗余存储。
    """
    id: int
    user_id: int = Field(..., alias="userId")
    category_id: int = Field(..., alias="categoryId")
    category_name: Optional[str] = Field(None, alias="categoryName")
    category_type: Optional[int] = Field(None, alias="categoryType", description="0=支出 1=收入")
    type: int = Field(..., description="0支出 1收入")
    amount: Decimal = Field(..., description="金额，定点 2 位")
    date: datetime.date = Field(..., alias="recordDate")
    remark: Optional[str] = None
    created_at: Optional[datetime.datetime] = Field(None, alias="createTime")
    updated_at: Optional[datetime.datetime] = Field(None, alias="updateTime")
