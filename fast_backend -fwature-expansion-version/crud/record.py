"""记账记录数据访问层

注意：排序字段为 Record.date（旧代码误用 Record.record_time，已修正）。
"""

from datetime import date

from fastapi import HTTPException
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from models.category import Category
from models.record import Record
from schemas.record import RecordCreate

# 修复 B2: 移除了 delete 导入 —— 删除一律走软删 status=0，不允许物理删行


async def _get_validated_category(db: AsyncSession, category_id: int, user_id: int) -> Category:
    """校验并返回可用分类（新增/改分类共用）

    修复 A3: 之前 router 直接把 RecordCreate 传给 create_record，没有分类校验。
    口径（API 文档「新增账单」业务规则）：分类不存在/禁用/不属于本人且非系统预设
    （user_id IS NULL）统一 404「分类不存在」。
    """
    result = await db.execute(
        select(Category).where(Category.id == category_id, Category.status == 1)
    )
    category = result.scalar_one_or_none()
    # 修复 B1 同源: 预设分类（user_id IS NULL）所有人可用；私有分类仅本人可用
    if category is None or (category.user_id is not None and category.user_id != user_id):
        raise HTTPException(status_code=404, detail="分类不存在")
    return category


async def get_records_by_user(
    db: AsyncSession,
    user_id: int,
    page: int = 1,
    size: int = 10,
    category_id: int | None = None,
    type_: int | None = None,
    month: str | None = None,
):
    """分页查询用户记账记录（按 date 倒序）

    修复 C2: ①新增 categoryId/type/month 可选筛选（API 文档列表接口参数表）
    ②LEFT JOIN categories 带出 categoryName/categoryType（库表不冗余存这两个字段，
    前端列表直接读 categoryName）③同时返回 total 供分页。
    返回 {"rows": [(Record, Category | None), ...], "total": int}
    """
    conditions = [Record.user_id == user_id, Record.status == 1]
    if category_id is not None:
        conditions.append(Record.category_id == category_id)
    if type_ is not None:
        conditions.append(Record.type == type_)
    # month 格式 yyyy-MM（router 已做正则预检），转成该月 [1号, 次月1号) 半开区间
    if month is not None:
        year, m = month.split("-")
        start = date(int(year), int(m), 1)
        end = date(int(year) + 1, 1, 1) if int(m) == 12 else date(int(year), int(m) + 1, 1)
        conditions.append(Record.date >= start)
        conditions.append(Record.date < end)

    # 修复 C2②: total 与列表用同一组筛选条件，先查总数
    total = (
        await db.execute(select(func.count(Record.id)).where(*conditions))
    ).scalar_one()

    result = await db.execute(
        select(Record, Category)
        .outerjoin(Category, Record.category_id == Category.id)
        .where(*conditions)
        # 修复 D2: 加 id desc 次级排序，同一天的多条记录分页顺序才稳定
        .order_by(Record.date.desc(), Record.id.desc())
        .offset((page - 1) * size)
        .limit(size)
    )
    return {"rows": result.all(), "total": total}


async def get_records_count(db: AsyncSession, user_id: int):
    """查询用户记账记录总数（未软删）"""
    result = await db.execute(
        select(func.count(Record.id)).where(Record.user_id == user_id, Record.status == 1)
    )
    return result.scalar_one()


async def get_record_by_id(db: AsyncSession, record_id: int):
    """根据 ID 查询记账记录"""
    result = await db.execute(select(Record).where(Record.id == record_id))
    return result.scalar_one_or_none()


async def get_record_with_category(db: AsyncSession, record_id: int):
    """按 ID 查单条记录 + LEFT JOIN 分类（详情接口用）

    返回 (Record | None, Category | None)；分类被物理删除时 category 为 None，
    categoryName 序列化为 null（API 文档分类模块业务规则），记录仍正常返回。
    """
    result = await db.execute(
        select(Record, Category)
        .outerjoin(Category, Record.category_id == Category.id)
        .where(Record.id == record_id)
    )
    row = result.one_or_none()
    if row is None:
        return None, None
    record, category = row
    return record, category


async def create_record(db: AsyncSession, data: RecordCreate, user_id: int) -> Record:
    """新增记账记录

    修复 A3: 签名改为 (db, data: RecordCreate, user_id)——原桩期望 ORM Record，
    router 却把 Pydantic 对象传进来，且 user_id 从未落库。现在在这里统一做
    分类校验 + type 推导 + 构造 ORM 实体。
    """
    category = await _get_validated_category(db, data.category_id, user_id)

    # type 未显式传时由所选分类的 type 推导（RecordCreate.type 的约定，AI 记账才显式传）
    record = Record(
        user_id=user_id,
        category_id=data.category_id,
        type=data.type if data.type is not None else category.type,
        amount=data.amount,
        date=data.date,
        remark=data.remark,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)  # 回读自增 id 和 created_at/updated_at
    return record


async def update_record(db: AsyncSession, record_id: int, user_id: int, **fields) -> Record:
    """按需更新记账记录（仅更新 fields 里出现的列）

    修复 B1: 更新前先校验记录存在、未软删且属于当前用户，
    否则任何登录用户都能改别人的账单（越权），不满足统一 404「记录不存在」。
    """
    result = await db.execute(select(Record).where(Record.id == record_id))
    record = result.scalar_one_or_none()
    if record is None or record.status != 1 or record.user_id != user_id:
        raise HTTPException(status_code=404, detail="记录不存在")

    new_category_id = fields.get("category_id")
    if new_category_id is not None:
        category = await _get_validated_category(db, new_category_id, user_id)
        # 改了分类且未显式传 type：沿用新分类的类型，保证收支归类一致
        if fields.get("type") is None:
            fields["type"] = category.type

    # 修复 A4 配套: fields 为空 dict 时直接返回现值，不发无效 UPDATE
    if fields:
        # updated_at 由 TimestampMixin 的 onupdate=func.now() 对 Core update 同样生效，无需手动填
        await db.execute(update(Record).where(Record.id == record_id).values(**fields))
        await db.commit()
        result = await db.execute(select(Record).where(Record.id == record_id))
        record = result.scalar_one()
    return record


async def soft_delete_record(db: AsyncSession, record_id: int, user_id: int):
    """软删除记账记录（status=0）

    修复 B2: 原实现是 delete(Record) 物理删行，违背项目软删口径
    （API 文档删除接口业务规则；统计/AI 撤销都依赖软删过滤）。
    修复 B1: 补归属校验，防止删别人的账单。
    """
    result = await db.execute(select(Record).where(Record.id == record_id))
    record = result.scalar_one_or_none()
    if record is None or record.status != 1 or record.user_id != user_id:
        raise HTTPException(status_code=404, detail="记录不存在")

    await db.execute(update(Record).where(Record.id == record_id).values(status=0))
    await db.commit()
