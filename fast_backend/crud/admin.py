"""管理后台数据访问层

口径说明（10-实现骨架.md §五）：
- 管理端删除用户/账单是**物理删除**（区别于用户侧账单软删 status=0 的 B2 口径——
  那条规则约束的是用户自己的删除接口；管理端清理账号/违规流水按规格物理删行）；
- 删用户按「records → categories → users」顺序先子表后主表（records.category_id
  是 RESTRICT 外键，必须先清账单）；sessions/messages/feedback/ai_bookkeeping_logs/
  user_token 对 users.id 均为 ON DELETE CASCADE，随 users 行由数据库级联清理；
- 全站统计一律过滤软删（status=1），与 crud/statistics.py 口径一致。
"""

from datetime import date
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import case, delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from models.chat import Faq
from models.category import Category
from models.record import Record
from models.user import User
from utils.security import escape_like


async def list_users(db: AsyncSession, page: int = 1, size: int = 20, keyword: str | None = None):
    """分页查询用户列表（username 模糊搜索，created_at 倒序）

    返回 {"rows": [User, ...], "total": int}
    """
    conditions = []
    if keyword and keyword.strip():
        # 转义 LIKE 通配符，防用户输入 % / _ 导致全量匹配（P2-4.2）
        kw = f"%{escape_like(keyword.strip())}%"
        conditions.append(User.username.like(kw, escape="\\"))

    total = (
        await db.execute(select(func.count(User.id)).where(*conditions))
    ).scalar_one()
    result = await db.execute(
        select(User)
        .where(*conditions)
        .order_by(User.created_at.desc(), User.id.desc())
        .offset((page - 1) * size)
        .limit(size)
    )
    return {"rows": result.scalars().all(), "total": total}


async def update_user_status(db: AsyncSession, user_id: int, status: int):
    """启用/禁用用户（status: 0=禁用 1=启用）"""
    stmt = update(User).where(User.id == user_id).values(status=status)
    result = await db.execute(stmt)
    await db.commit()
    return result.rowcount > 0


async def get_all_records(
    db: AsyncSession,
    page: int = 1,
    size: int = 10,
    type_: int | None = None,
    month: str | None = None,
    user_id: int | None = None,
):
    """全站账单分页列表（联 users / categories）

    修复 B6：type 过滤在 SQL 层完成（旧 Java 分页后内存过滤导致 total 失真）；
    month 转半开日期区间 [当月1号, 次月1号)，可命中 idx_records_user_date。
    返回 {"rows": [(Record, Category | None, username | None), ...], "total": int}
    """
    conditions = [Record.status == 1]
    if type_ is not None:
        conditions.append(Category.type == type_)
    if user_id is not None:
        conditions.append(Record.user_id == user_id)
    if month is not None:
        year, m = month.split("-")
        start = date(int(year), int(m), 1)
        end = date(int(year) + 1, 1, 1) if int(m) == 12 else date(int(year), int(m) + 1, 1)
        conditions.append(Record.date >= start)
        conditions.append(Record.date < end)

    total = (
        await db.execute(
            select(func.count(Record.id))
            .select_from(Record)
            .outerjoin(Category, Record.category_id == Category.id)
            .where(*conditions)
        )
    ).scalar_one()

    result = await db.execute(
        select(Record, Category, User.username)
        .select_from(Record)
        .outerjoin(Category, Record.category_id == Category.id)
        .outerjoin(User, Record.user_id == User.id)
        .where(*conditions)
        .order_by(Record.date.desc(), Record.id.desc())
        .offset((page - 1) * size)
        .limit(size)
    )
    return {"rows": result.all(), "total": total}


async def delete_user_cascade(db: AsyncSession, user_id: int) -> None:
    """删除用户及其全部业务数据（单事务，先子表后主表）"""
    await db.execute(delete(Record).where(Record.user_id == user_id))
    await db.execute(delete(Category).where(Category.user_id == user_id))
    await db.execute(delete(User).where(User.id == user_id))
    await db.commit()


async def batch_delete_users(db: AsyncSession, ids: list[int]) -> int:
    """批量删除用户

    语义（对齐 10 §5.4）：不存在的 ID 跳过；命中管理员账户立即抛错，
    不产生任何删除（先全量校验再统一执行，等价于"已处理的删除随事务回滚"）。
    返回实际删除的用户数。
    """
    rows = (await db.execute(select(User).where(User.id.in_(ids)))).scalars().all()
    by_id = {u.id: u for u in rows}

    to_delete: list[int] = []
    for uid in dict.fromkeys(ids):  # 去重且保持请求顺序
        u = by_id.get(uid)
        if u is None:
            continue
        if u.role == 1:
            raise HTTPException(status_code=400, detail=f"不能删除管理员账户: {u.username}")
        to_delete.append(uid)

    if not to_delete:
        return 0
    await db.execute(delete(Record).where(Record.user_id.in_(to_delete)))
    await db.execute(delete(Category).where(Category.user_id.in_(to_delete)))
    await db.execute(delete(User).where(User.id.in_(to_delete)))
    await db.commit()
    return len(to_delete)


async def batch_delete_records(db: AsyncSession, ids: list[int]) -> int:
    """批量物理删除账单（未命中的 id 静默忽略），返回删除条数"""
    result = await db.execute(delete(Record).where(Record.id.in_(ids)))
    await db.commit()
    return result.rowcount


async def get_overview(db: AsyncSession) -> dict:
    """系统概览：三个 COUNT + 一次 LEFT JOIN 聚合收支（10 §5.7，共 4 条 SQL）

    收支只统计未软删记录；无数据时 SUM 为 NULL，COALESCE 兜底为 0；
    COALESCE 落到 0 字面量时驱动可能返回 int，统一转 Decimal（禁止 float 算钱）。
    """
    total_users = (await db.execute(select(func.count(User.id)))).scalar_one()
    total_records = (
        await db.execute(select(func.count(Record.id)).where(Record.status == 1))
    ).scalar_one()
    total_categories = (await db.execute(select(func.count(Category.id)))).scalar_one()

    result = await db.execute(
        select(
            func.coalesce(func.sum(case((Category.type == 1, Record.amount), else_=0)), 0),
            func.coalesce(func.sum(case((Category.type == 0, Record.amount), else_=0)), 0),
        )
        .select_from(Record)
        .outerjoin(Category, Record.category_id == Category.id)
        .where(Record.status == 1)
    )
    total_income, total_expense = result.one()
    return {
        "totalUsers": total_users,
        "totalRecords": total_records,
        "totalCategories": total_categories,
        "totalIncome": Decimal(str(total_income)),
        "totalExpense": Decimal(str(total_expense)),
    }


async def list_all_categories(db: AsyncSession):
    """查询所有分类（含系统预设）"""
    result = await db.execute(select(Category))
    return result.scalars().all()


async def list_faq(db: AsyncSession):
    """查询 FAQ 全量列表（faq 表无 status 列，物理删除）"""
    result = await db.execute(select(Faq))
    return result.scalars().all()


async def create_faq(db: AsyncSession, faq: Faq):
    """新增 FAQ"""
    db.add(faq)
    await db.flush()
    return faq


async def update_faq(db: AsyncSession, faq_id: int, **fields):
    """更新 FAQ（fields 仅含调用方传入的非空字段）"""
    faq = await db.get(Faq, faq_id)
    if faq is None:
        return None
    for key, value in fields.items():
        setattr(faq, key, value)
    await db.flush()
    return faq


async def delete_faq(db: AsyncSession, faq_id: int):
    """物理删除 FAQ（faq 表无 status 列，D32 口径在此为物理删），返回是否命中"""
    faq = await db.get(Faq, faq_id)
    if faq is None:
        return False
    await db.delete(faq)
    await db.flush()
    return True
