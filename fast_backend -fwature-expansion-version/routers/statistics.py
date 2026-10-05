"""统计模块路由 — /api/statistics"""

from fastapi import APIRouter, Query
from fastapi.params import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from config.db_config import get_db
from crud import statistics
from schemas.statistics import CategoryStatisticsOut, MonthlyStatsOut
from utils.auth import get_current_user
from utils.response import success_response

router = APIRouter(prefix="/api/statistics", tags=["statistics"])


# ⚠️ 路径必须是 /monthly：Web 端与 uni-app 的 api/statistics.js 都调
#    `request.get('/statistics/monthly')`，04 §4.1 与 10 §四 也都是 /monthly。
#    原来写成 /summary 会让首页统计卡片直接 404。
@router.get("/monthly")
async def get_summary(
        year: int = Query(..., ge=2000, le=2100, description="年份"),
        month: int = Query(..., ge=1, le=12, description="月份 1-12"),
        user_id: int = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
):
    """月度收支汇总（API文档.md §四.1）"""
    total_income, total_expense = await statistics.get_summary(db, user_id, year, month)
    monthly = MonthlyStatsOut(
        year=year,
        month=month,
        total_income=total_income,
        total_expense=total_expense,
    )
    # python 模式 dump 保留 Decimal，由 success_response 的 jsonable_encoder
    # 统一转数字；mode="json" 会把 Decimal 变字符串，前端无法参与算术，勿用。
    return success_response(data=monthly.model_dump(by_alias=True))


# 注：原实现另有 `GET /trend`（收支趋势），04 §4 与 10 §四 只定义了
#     /monthly（月度汇总）与 /category（分类统计），前端也未调用，已移除。
#     如确需趋势图，请先补文档与前端再新增接口，避免接口面无限膨胀。


@router.get("/category")
async def get_category_stats(
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    year: int = Query(..., ge=2000, le=2100, description="年份"),
    month: int = Query(..., ge=1, le=12, description="月份 1-12"),
    type: int = Query(0, ge=0, le=1, description="0=支出 / 1=收入，默认 0"),
):
    """分类统计（API文档.md §4.2）：统计页的分类占比饼图 / 排行条形图"""
    rows = await statistics.get_category_stats(db, user_id, year, month, type)
    total = sum(amount for _, _, amount in rows)
    items = []
    for category_id, category_name, amount in rows:
        # 占比在 Python 层计算：amount / 该类型总金额 * 100，保留一位小数（§4.2）
        percentage = round(float(amount / total * 100), 1) if total else 0.0
        items.append(
            CategoryStatisticsOut(
                category_id=category_id,
                category_name=category_name,
                amount=amount,
                percentage=percentage,
            )
        )
    # python 模式 dump 保留 Decimal，由 success_response 的 jsonable_encoder
    # 统一转数字；mode="json" 会把 Decimal 变字符串，前端无法参与算术，勿用。
    return success_response(
        data=[item.model_dump(by_alias=True) for item in items]
    )
