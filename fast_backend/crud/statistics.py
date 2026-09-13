"""统计数据访问层 — 统计模块的聚合查询"""

from datetime import date
from decimal import Decimal

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.category import Category
from models.record import Record


async def get_summary(db: AsyncSession, user_id: int, year: int, month: int):
    """月度收支汇总：返回 (当月总收入, 当月总支出)

    统计口径（10-实现骨架.md §4.1）：
    - 收入/支出由 category.type 判定（1=收入、0=支出），金额取自 record.amount；
    - 仅统计未软删记录（status=1），软删口径见 crud/record.py 修复 B2；
    - 日期用半开区间 [当月1号, 次月1号)，可命中 idx_records_user_date
      （避免 YEAR()/MONTH() 函数包裹列导致索引失效，见 10 §四性能提示）；
    - 金额全程 Decimal 运算；无数据时 SUM 为 NULL，COALESCE 兜底为 0（非 null）。
    """
    month_start = date(year, month, 1)
    next_month_start = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)

    result = await db.execute(
        select(
            func.coalesce(
                func.sum(case((Category.type == 1, Record.amount), else_=0)), 0
            ),
            func.coalesce(
                func.sum(case((Category.type == 0, Record.amount), else_=0)), 0
            ),
        )
        .select_from(Record)
        .outerjoin(Category, Record.category_id == Category.id)
        .where(
            Record.user_id == user_id,
            Record.status == 1,
            Record.date >= month_start,
            Record.date < next_month_start,
        )
    )
    total_income, total_expense = result.one()
    # COALESCE 落到 0 字面量时驱动可能返回 int，统一转 Decimal（禁止 float 存钱/算钱）
    total_income = Decimal(str(total_income))
    total_expense = Decimal(str(total_expense))
    return total_income, total_expense


async def get_trend(db: AsyncSession, user_id: int):
    """收支趋势：按日期聚合收入/支出"""
    # TODO: 实现
    ...


async def get_category_stats(
    db: AsyncSession, user_id: int, year: int, month: int, stat_type: int
):
    """分类统计：按 stat_type（0=支出 / 1=收入）聚合各分类金额（API文档.md §4.2）

    统计口径与 get_summary 一致：未软删（status=1）、半开日期区间可命中
    idx_records_user_date（避免 YEAR()/MONTH() 包裹列导致索引失效）；
    c.type 过滤放 WHERE，无分类的记录本来就会被排除，与文档的 LEFT JOIN 等价。
    按金额降序返回 [(category_id, category_name, Decimal 金额), ...]；
    COALESCE 兜底后驱动可能返回 int，统一转 Decimal（禁止 float 存钱/算钱）。
    """
    month_start = date(year, month, 1)
    next_month_start = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)

    result = await db.execute(
        select(
            Category.id,
            Category.name,
            func.coalesce(func.sum(Record.amount), 0),
        )
        .select_from(Record)
        .join(Category, Record.category_id == Category.id)
        .where(
            Record.user_id == user_id,
            Record.status == 1,
            Record.date >= month_start,
            Record.date < next_month_start,
            Category.type == stat_type,
        )
        .group_by(Category.id, Category.name)
        .order_by(func.sum(Record.amount).desc())
    )
    rows = result.all()
    return [(rid, name, Decimal(str(amount))) for rid, name, amount in rows]
