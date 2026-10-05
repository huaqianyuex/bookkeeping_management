"""记账记录路由 — /api/records"""

import re

# 修复 D 级: Depends 改从 fastapi 顶层导入（fastapi.params 是内部模块，能用但不规范）
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from config.db_config import get_db
from crud import record
from schemas.record import RecordCreate, RecordOut, RecordUpdate
from utils.auth import get_current_user
from utils.response import success_response

router = APIRouter(prefix="/api/records", tags=["record"])

# 修复 C2: month 参数格式预检（yyyy-MM），非法直接 422，不让坏格式漏进日期运算
MONTH_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


def _record_out(record_obj, category) -> RecordOut:
    """把 (Record, Category) 组包成 RecordOut

    修复 C2④: ORM 对象不能直接进 success_response（jsonable_encoder 处理不了
    _sa_instance_state），必须过 RecordOut；categoryName/categoryType 来自 JOIN 结果。
    """
    out = RecordOut.model_validate(record_obj)
    if category is not None:
        out.category_name = category.name
        out.category_type = category.type
    return out


@router.get("")
async def list_records(
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    # 修复 C2①: 接收分页与筛选查询参数（API 文档列表接口参数表）
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(10, ge=1, le=100, description="每页条数"),
    categoryId: int | None = Query(None, description="按分类筛选"),
    type: int | None = Query(None, ge=0, le=1, description="0支出 1收入"),
    month: str | None = Query(None, description="按月份筛选，格式 yyyy-MM"),
):
    """分页查询记账记录"""
    if month is not None and not MONTH_RE.match(month):
        raise HTTPException(status_code=422, detail="month 格式应为 yyyy-MM，如 2026-06")

    # 修复 A1: 补 await（你已加），这里同时把分页/筛选参数传下去
    res = await record.get_records_by_user(
        db, user_id, page=page, size=size,
        category_id=categoryId, type_=type, month=month,
    )
    # 修复 C2③④: 列表经 RecordOut 序列化（camelCase + JOIN 出的 categoryName），
    # 不再多套一层；total 用真实查询结果，不再写死 0
    data = {
        "records": [_record_out(r, c) for r, c in res["rows"]],
        "total": res["total"],
    }
    return success_response(message="获取成功", data=data)


@router.post("")
async def create_record(
    data: RecordCreate,
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """新增记账记录"""
    # 修复 C1: 删除「用户存在」检查——无状态 JWT（决策 D8），token 有效即用户有效
    # 修复 A3: crud 签名改为 (db, data, user_id)，内部完成分类校验/type 推导/构造 ORM
    await record.create_record(db, data, user_id)
    # 按文档契约创建成功 data 为 null；直接返回 ORM 对象会序列化失败（C4）
    return success_response(message="记账成功")


# 修复 C3: 补充 API 文档「建议补充」的账单详情接口
@router.get("/{record_id}")
async def get_record(
    record_id: int,
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取账单详情"""
    record_obj, category = await record.get_record_with_category(db, record_id)
    # 修复 B1 同口径: 详情也做归属校验，别人的账单/已软删的统一 404
    if record_obj is None or record_obj.status != 1 or record_obj.user_id != user_id:
        raise HTTPException(status_code=404, detail="记录不存在")
    return success_response(message="获取成功", data=_record_out(record_obj, category))


# 修复 D1: docstring 挪回函数体第一行（写在中间只是普通字符串表达式）
@router.put("/{record_id}")
async def update_record(
    record_id: int,
    data: RecordUpdate,
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """更新记账记录"""
    # 修复 C1: 同上，删除冗余的用户存在检查
    # 修复 A4: **fields 不能按位置传 Pydantic 对象——先 model_dump(exclude_unset=True)
    # 只保留用户显式传的字段（部分更新语义），再用 ** 展开成关键字参数
    values = data.model_dump(exclude_unset=True)
    record_obj = await record.update_record(db, record_id, user_id, **values)
    # 修复 C4: 经 RecordOut 序列化（camelCase 别名），不直接返回 ORM 对象
    return success_response(message="更新成功", data=RecordOut.model_validate(record_obj))


@router.delete("/{record_id}")
async def delete_record(
    record_id: int,
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """删除记账记录（软删除）"""
    # 修复 C1: 删除冗余的用户存在检查
    # 修复 A1（你漏了这处 await）+ B1/B2: await 调用，crud 内部做归属校验并软删 status=0
    await record.soft_delete_record(db, record_id, user_id)
    return success_response(message="删除成功")
