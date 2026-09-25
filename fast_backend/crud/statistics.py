"""统计数据访问层 — 实现收支汇总、趋势、分类统计等查询

口径：软删 Record.status=1 计入统计，对齐 crud/record.py
"""

from datetime import date
from decimal import Decimal
from sqlalchemy import func, select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from models.bookkeeping import AiBookkeepingLog
from models.record import Record
from models.category import Category


async def get_summary(db: AsyncSession, user_id: int, year: int, month: int):
    """收支汇总：总收入、总支出、结余、记录数
    
    返回 (total_income, total_expense) 两个 Decimal
    """
    start_date = date(year, month, 1)
    if month == 12:
        end_date = date(year + 1, 1, 1)
    else:
        end_date = date(year, month + 1, 1)
    
    # 总收入
    income_stmt = select(func.sum(Record.amount)).where(
        Record.user_id == user_id,
        Record.type == 1,
        Record.status == 1,
        Record.date >= start_date,
        Record.date < end_date
    )
    total_income = (await db.execute(income_stmt)).scalar_one() or Decimal('0')
    
    # 总支出
    expense_stmt = select(func.sum(Record.amount)).where(
        Record.user_id == user_id,
        Record.type == 0,
        Record.status == 1,
        Record.date >= start_date,
        Record.date < end_date
    )
    total_expense = (await db.execute(expense_stmt)).scalar_one() or Decimal('0')
    
    return total_income, total_expense


async def get_trend(db: AsyncSession, user_id: int, year: int, month: int):
    """收支趋势：按日期聚合收入/支出"""
    # TODO: 后续实现
    ...


async def get_category_stats(db: AsyncSession, user_id: int, year: int, month: int, stat_type: int = 0):
    """分类统计：每个分类的金额、笔数、占比
    
    返回 [(category_id, category_name, amount), ...] 列表
    stat_type: 0=支出，1=收入，默认 0 (routers 传参名为 type，ai/context 传参名为 stat_type，以 stat_type 为准)
    """
    from sqlalchemy import text
    
    start_date = date(year, month, 1)
    if month == 12:
        end_date = date(year + 1, 1, 1)
    else:
        end_date = date(year, month + 1, 1)
    
    # 按分类聚合
    stmt = select(
        Record.category_id,
        func.coalesce(Category.name, '其他').label('category_name'),
        func.sum(Record.amount).label('total_amount'),
        func.count(Record.id).label('record_count')
    ).outerjoin(Category, Category.id == Record.category_id).where(
        Record.user_id == user_id,
        Record.type == stat_type,
        Record.status == 1,
        Record.date >= start_date,
        Record.date < end_date
    ).group_by(Record.category_id, Category.name).order_by(func.sum(Record.amount).desc())
    
    results = (await db.execute(stmt)).all()
    return [(r.category_id, r.category_name, r.total_amount) for r in results]
