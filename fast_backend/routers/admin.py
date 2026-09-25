"""管理后台路由 — /api/admin

鉴权：每个端点经 `Depends(get_current_admin)` 完成「登录 + role=1」校验
（依赖内部已链 get_current_user，勿再叠加）；返回值（登录管理员 id）本
模块用不到，按 10-实现骨架.md §五 惯例参数名写作 `_`。
"""

import re

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from config.db_config import get_db
from crud import admin, user
from models.chat import Faq
from schemas.admin import (
    AdminRecordOut,
    AdminUserOut,
    FaqIn,
    FaqOut,
    IdsIn,
    UserStatusUpdate,
)
from utils.auth import get_current_admin
from utils.response import success_response

router = APIRouter(prefix="/api/admin", tags=["admin"])

# month 参数格式预检（yyyy-MM），与 routers/record.py 同款
MONTH_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


def _page_data(rows: list, total: int, page: int, size: int) -> dict:
    """组包分页结构（records/total/pages/current/size），前端分页器全量读取"""
    return {
        "records": rows,
        "total": total,
        "pages": (total + size - 1) // size,
        "current": page,
        "size": size,
    }


def _admin_record_out(record_obj, category, username: str | None) -> AdminRecordOut:
    """(Record, Category | None, username) 组包成 AdminRecordOut

    ORM 对象不能直接进 success_response（jsonable_encoder 处理不了
    _sa_instance_state），必须过 Pydantic 模型；categoryName/categoryType
    来自 JOIN 结果，分类被物理删除时为 null。
    """
    out = AdminRecordOut.model_validate(record_obj)
    if category is not None:
        out.category_name = category.name
        out.category_type = category.type
    out.username = username
    return out


# ---------- 用户管理 ----------


@router.get("/users", summary="用户列表")
async def list_users(
    _: int = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(10, ge=1, le=100, description="每页条数"),
    keyword: str | None = Query(None, description="用户名模糊搜索"),
):
    """分页查询用户列表"""
    res = await admin.list_users(db, page=page, size=size, keyword=keyword)
    data = _page_data(
        [AdminUserOut.model_validate(u) for u in res["rows"]],
        res["total"], page, size,
    )
    return success_response(message="获取成功", data=data)


@router.get("/users/{user_id}", summary="用户详情")
async def get_user_detail(
    user_id: int,
    _: int = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """用户详情"""
    user_obj = await user.get_user_by_id(db, user_id)
    if user_obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    return success_response(message="获取成功", data=AdminUserOut.model_validate(user_obj))


@router.put("/users/{user_id}/status", summary="启用/禁用用户")
async def update_user_status(
    user_id: int,
    body: UserStatusUpdate,
    _: int = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """启用/禁用用户"""
    user_obj = await user.get_user_by_id(db, user_id)
    if user_obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    await admin.update_user_status(db, user_id, body.status)
    return success_response(message="操作成功")


@router.delete("/users/{user_id}", summary="删除用户")
async def delete_user(
    user_id: int,
    _: int = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """删除用户（级联清理其账单/分类/AI 数据，单事务）"""
    user_obj = await user.get_user_by_id(db, user_id)
    if user_obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    if user_obj.role == 1:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="不能删除管理员账户")
    await admin.delete_user_cascade(db, user_id)
    return success_response(message="删除成功")


@router.post("/users/batch-delete", summary="批量删除用户")
async def batch_delete_users(
    body: IdsIn,
    _: int = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """批量删除用户（不存在的 ID 跳过；命中管理员账户 400 并整体回滚）"""
    await admin.batch_delete_users(db, body.ids)
    return success_response(message="批量删除成功")


# ---------- 账单管理 ----------


@router.get("/records", summary="账单列表")
async def list_records(
    _: int = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(10, ge=1, le=100, description="每页条数"),
    type: int | None = Query(None, ge=0, le=1, description="0支出 1收入（按分类 type 过滤）"),
    month: str | None = Query(None, description="月份，格式 yyyy-MM"),
    userId: int | None = Query(None, description="指定用户 ID，缺省为全站"),
):
    """全站账单分页列表（type 过滤在 SQL 层完成，total 正确）"""
    if month is not None and not MONTH_RE.match(month):
        raise HTTPException(status_code=422, detail="month 格式应为 yyyy-MM，如 2026-06")

    res = await admin.get_all_records(
        db, page=page, size=size, type_=type, month=month, user_id=userId,
    )
    data = _page_data(
        [_admin_record_out(r, c, username) for r, c, username in res["rows"]],
        res["total"], page, size,
    )
    return success_response(message="获取成功", data=data)


@router.post("/records/batch-delete", summary="批量删除账单")
async def batch_delete_records(
    body: IdsIn,
    _: int = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """批量删除账单（未命中的 id 静默忽略）"""
    await admin.batch_delete_records(db, body.ids)
    return success_response(message="批量删除成功")


# ---------- 系统概览 ----------


@router.get("/statistics/overview", summary="系统概览")
async def overview(
    _: int = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """管理后台首页统计卡片（用户数/账单数/分类数/全站收支）"""
    return success_response(message="获取成功", data=await admin.get_overview(db))


# ---------- FAQ 管理 ----------


@router.get("/faq", summary="FAQ 列表")
async def list_faq(
    _: int = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """FAQ 全量列表（知识库条目少，不分页）"""
    rows = await admin.list_faq(db)
    return success_response(
        message="获取成功", data=[FaqOut.model_validate(r) for r in rows]
    )


@router.post("/faq", summary="新增 FAQ")
async def create_faq(
    body: FaqIn,
    _: int = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """新增 FAQ（三字段必填校验在 Pydantic 层完成）"""
    if not (body.question and body.answer and body.category):
        raise HTTPException(status_code=422, detail="question/answer/category 均必填")
    faq = await admin.create_faq(
        db, Faq(question=body.question, answer=body.answer, category=body.category)
    )
    await db.commit()
    return success_response(message="创建成功", data=FaqOut.model_validate(faq))


@router.put("/faq/{faq_id}", summary="修改 FAQ")
async def update_faq(
    faq_id: int,
    body: FaqIn,
    _: int = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """修改 FAQ（仅更新传入字段）"""
    fields = body.model_dump(exclude_none=True)
    if not fields:
        raise HTTPException(status_code=422, detail="缺少修改内容")
    faq = await admin.update_faq(db, faq_id, **fields)
    if faq is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="FAQ 不存在")
    await db.commit()
    return success_response(message="更新成功", data=FaqOut.model_validate(faq))


@router.delete("/faq/{faq_id}", summary="删除 FAQ")
async def delete_faq(
    faq_id: int,
    _: int = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """删除 FAQ（物理删除）"""
    if not await admin.delete_faq(db, faq_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="FAQ 不存在")
    await db.commit()
    return success_response(message="删除成功")
