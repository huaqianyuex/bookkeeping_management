"""统计相关 Pydantic 模型"""

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, computed_field


class MonthlyStatsOut(BaseModel):
    """月度收支汇总响应 — 对齐 API文档.md §四.1 / 04-业务接口规范.md §4.1

    金额用 Decimal 承载（响应序列化时由 jsonable_encoder 转数字）；
    balance 按文档口径在模型层派生，调用方无需重复计算。
    """
    year: int
    month: int
    total_income: Decimal = Field(0, alias="totalIncome")
    total_expense: Decimal = Field(0, alias="totalExpense")

    model_config = ConfigDict(populate_by_name=True)

    @computed_field(alias="balance")
    @property
    def balance(self) -> Decimal:
        return self.total_income - self.total_expense


class TrendItem(BaseModel):
    """趋势项"""
    date: str
    income: float = 0
    expense: float = 0


class CategoryStatisticsOut(BaseModel):
    """分类统计项 — 对齐 API文档.md §4.2 CategoryStatisticsVO

    字段口径：categoryId / categoryName / amount / percentage，
    percentage 由路由层计算（amount / 该类型总金额 * 100，保留一位小数）；
    金额用 Decimal 承载，响应时由 jsonable_encoder 转数字。
    """
    category_id: int = Field(..., alias="categoryId")
    category_name: str = Field(..., alias="categoryName")
    amount: Decimal = Field(0, alias="amount")
    percentage: float = 0

    model_config = ConfigDict(populate_by_name=True)
