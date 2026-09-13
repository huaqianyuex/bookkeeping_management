"""分类数据访问层 — 模板桩，业务逻辑由你后续实现"""
from fastapi import HTTPException
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from models.category import Category
from schemas.category import CategoryUpdate, CategoryCreate


async def get_categories_by_user(db: AsyncSession, user_id: int, type: int | None = None):
    """查询某用户的分类列表（含系统预设 user_id=NULL）
    
    归属过滤：user_id = 本人 OR user_id IS NULL（预设）
    类型过滤：可选，传了 type 就只看该类型
    """
    stmt = select(Category).where(
        (Category.user_id == user_id) | Category.user_id.is_(None)
    )
    if type is not None:
        stmt = stmt.where(Category.type == type)
    result = await db.execute(stmt)
    return result.scalars().all()


async def get_category_by_id(db: AsyncSession, category_id: int):
    """根据 ID 查询分类"""
    result = await db.execute(select(Category).where(Category.id == category_id))
    return result.scalar_one_or_none()


async def create_category(db: AsyncSession, data: CategoryCreate,user_id:int)->Category:
    """新增分类"""
    category = Category(user_id=user_id, **data.model_dump(exclude_unset=True))
    db.add(category)
    await db.commit()
    await db.refresh(category)
    return category


async def update_category(db: AsyncSession, category_id: int, data: CategoryUpdate, user_id: int):
    existing = await get_category_by_id(db, category_id)
    if not existing:
        raise HTTPException(status_code=404, detail="分类不存在")
    # 检查归属：预设分类（user_id is None）不允许修改
    if existing.user_id is None or existing.user_id != user_id:
        raise HTTPException(status_code=403, detail="无权修改此分类")
    values = data.model_dump(exclude_unset=True, exclude_none=True)
    if not values:
        raise HTTPException(status_code=400, detail="没有需要更新的内容")
    stmt = update(Category).where(Category.id == category_id).values(**values)
    await db.execute(stmt)
    await db.commit()
    return await get_category_by_id(db, category_id)


async def delete_category(db: AsyncSession, category_id: int,user_id:int):
    """删除分类"""
    existing = await get_category_by_id(db, category_id)
    if not existing:
        raise HTTPException(status_code=404, detail="分类不存在")
    # 预设分类不可删除
    if existing.user_id is None:
        raise HTTPException(status_code=403, detail="系统预设分类不可删除")
    # 检查归属
    if existing.user_id != user_id:
        raise HTTPException(status_code=403, detail="无权删除此分类")
    await db.delete(existing)
    await db.commit()