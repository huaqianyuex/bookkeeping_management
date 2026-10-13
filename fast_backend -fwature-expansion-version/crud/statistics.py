"""统计数据访问层 — 实现收支汇总、趋势、分类统计等查询

口径：软删 Record.status=1 计入统计，对齐 crud/record.py
"""

from datetime import date
from decimal import Decimal
from sqlalchemy import func, select, and_, case
from sqlalchemy.ext.asyncio import AsyncSession

from models.bookkeeping import AiBookkeepingLog
from models.record import Record
from models.category import Category


async def get_summary(db: AsyncSession, user_id: int, year: int, month: int):
    """收支汇总：总收入、总支出、结余、记录数

    返回 (total_income, total_expense) 两个 Decimal

    审查报告 P1-8：收入/支出原先各发一条 SUM 查询，而本函数位于 /chat 首字延迟
    的串行路径上（ai/context.py 每次组包要算本月+上月 → 4 次往返）。合并为单条
    CASE WHEN 条件聚合，范围条件合并为一次 WHERE，语义与返回类型不变
    （无记录时 COALESCE 回 0）。

    ⚠️ 不要改成 asyncio.gather 并发两条查询：单个 AsyncSession 只持有一条连接，
    并发 execute 会互相抢占，属未定义行为。
    """
    start_date = date(year, month, 1)
    if month == 12:
        end_date = date(year + 1, 1, 1)
    else:
        end_date = date(year, month + 1, 1)

    stmt = select(
        func.coalesce(
            func.sum(case((Record.type == 1, Record.amount), else_=Decimal("0"))), Decimal("0")
        ),
        func.coalesce(
            func.sum(case((Record.type == 0, Record.amount), else_=Decimal("0"))), Decimal("0")
        ),
    ).where(
        Record.user_id == user_id,
        Record.status == 1,
        Record.date >= start_date,
        Record.date < end_date
    )
    total_income, total_expense = (await db.execute(stmt)).one()
    # COALESCE 已保证非 None，故不再做 is not None 兜底；显式 Decimal("0") 而非
    # 整数 0，避免 SQLite 等后端在空月返回 int 破坏返回类型契约。
    return (Decimal(total_income), Decimal(total_expense))


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
