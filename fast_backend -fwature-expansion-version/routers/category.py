"""分类模块路由 — /api/categories"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from config.db_config import get_db
from crud import category

from schemas.category import CategoryCreate, CategoryOut, CategoryUpdate
from utils.auth import get_current_user
from utils.response import success_response

router = APIRouter(prefix="/api/categories", tags=["category"])


@router.get("")
async def list_categories(
        user_id: int = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
        type_: int | None = Query(None, alias="type"),
):
    """获取分类列表"""
    res_data = await category.get_categories_by_user(db, user_id, type_)
    # 统一经 CategoryOut 序列化，保证键与契约一致（userId/sortOrder/createTime/updateTime）
    data = [CategoryOut.model_validate(x) for x in res_data]
    return success_response(message="获取成功", data=data)


@router.post("")
async def create_category(
    data: CategoryCreate,
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """新增分类"""
    await category.create_category(db,data,user_id)

    return success_response(message="创建成功")


@router.put("/{category_id}")
async def update_category(
    category_id: int,
    data: CategoryUpdate,
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """更新分类"""
    res_update = await category.update_category(db, category_id, data, user_id)
    return success_response(message="更新成功", data=CategoryOut.model_validate(res_update))


@router.delete("/{category_id}")
async def delete_category(
    category_id: int,
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """删除分类"""
    await category.delete_category(db, category_id, user_id)
    return success_response(message="删除成功")
