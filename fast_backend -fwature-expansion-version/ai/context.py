"""用户财务上下文组装 — 查询 MySQL → UserFinanceContext"""

from datetime import date, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from crud.statistics import get_category_stats, get_summary
from schemas.ai import UserFinanceContext


async def build_user_context(db: AsyncSession, user_id: int) -> dict:
    """构建用户财务上下文，传给 LLM

    组包口径（06-AI模块.md）：
    - 当月收支汇总（get_summary，Decimal → float 仅用于 JSON 序列化展示）；
    - 当月支出 Top5 分类（get_category_stats，含占比）；
    - 上月总支出做环比（trend 由 LLM 在分析时引用）。
    """
    today = date.today()
    this_start = today.replace(day=1)
    last_end = this_start - timedelta(days=1)  # 上月最后一天
    last_start = last_end.replace(day=1)

    # 当月收支汇总
    this_income, this_expense = await get_summary(db, user_id, today.year, today.month)
    # 上月支出（环比用）
    _, last_expense = await get_summary(db, user_id, last_start.year, last_start.month)
    # 当月支出 Top5 分类
    cat_rows = await get_category_stats(db, user_id, today.year, today.month, stat_type=0)

    top = []
    for _, name, amount in cat_rows[:5]:
        amt = float(amount)
        pct = round(amt / float(this_expense) * 100, 1) if this_expense else 0.0
        top.append({"name": name, "amount": amt, "percentage": pct})

    return {
        "this_month": f"{today.year}-{today.month:02d}",
        "total_income": float(this_income),
        "total_expense": float(this_expense),
        "last_month_expense": float(last_expense),
        "top_categories": top,
    }


async def build_finance_block(db: AsyncSession, user_id: int) -> str:
    """构建对话用财务数据块（系统查库组包，供对话 LLM 引用）

    修复「账单分析查不到数据」：/chat 与 /chat/stream 原本只给模型
    system+历史+提问，模型对用户账单一无所知，只能自保式回答
    "没查到本月数据"。本块把真实查询结果拼进 system，模型据此分析。

    - 查询失败返回空串（不阻断对话，模型按无数据口径如实回答）；
    - 本月无记录时显式写明"暂无任何记账记录"，让模型如实回答而不是臆测。
    """
    try:
        ctx = await build_user_context(db, user_id)
    except Exception:
        # 数据不可用 ≠ 没有数据：返回空块，模型不再引用任何数字
        return ""
    income = float(ctx["total_income"])
    expense = float(ctx["total_expense"])

    if income == 0 and expense == 0:
        month_line = f"统计月份: {ctx['this_month']}（本月暂无任何记账记录）"
        top_line = "本月支出Top分类: （无）"
    else:
        month_line = f"统计月份: {ctx['this_month']}"
        top_line = "本月支出Top分类: " + (
            "、".join(
                f"{t['name']} ¥{t['amount']:.2f}（{t['percentage']}%）"
                for t in ctx["top_categories"]
            )
            or "（无）"
        )

    return (
        "\n\n[系统实时查询的用户财务数据（来自数据库，可信）]\n"
        "回答收支、消费分析、预算、储蓄类问题时，必须以下列数据为准并引用具体数字；"
        "禁止编造或臆测任何数据；数据中不存在的信息要如实说明。\n"
        f"{month_line}\n"
        f"本月总收入: ¥{income:.2f}\n"
        f"本月总支出: ¥{expense:.2f}\n"
        f"上月总支出: ¥{float(ctx['last_month_expense']):.2f}\n"
        f"{top_line}\n"
    )
