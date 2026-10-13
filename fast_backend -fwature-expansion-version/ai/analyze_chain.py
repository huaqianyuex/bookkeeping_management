"""分析链 — 消费分析与预算建议（LLM 结构化输出）"""

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from ai.llm import get_analyze_llm
from ai.observability import KIND_ANALYZE, Timer, record_call
from schemas.ai import BudgetPlan, ExpenseAnalysis

ANALYZE_SYSTEM = (
    "你是个人记账管理系统「小记」的财务分析师。基于给定的用户财务数据做消费分析，"
    "输出 JSON：summary（一句话总结）、insights（洞察，正好 3 条）、suggestions（建议，正好 3 条）、"
    "risk_level（必须从「低/一般/高」三选一）。"
    "total_expense / savings_rate / top_categories 由系统计算填入，你不用输出。"
    "只输出 JSON，不要多余文字。用中文。"
)

BUDGET_SYSTEM = (
    "你是个人记账管理系统「小记」的预算规划师。基于用户月收入、储蓄目标和历史消费结构制定预算，"
    "输出 JSON：monthly_budget（建议月总预算，必须小于用户月收入）、"
    "category_limits（数组，每项含 category 名称、"
    "limit 预算上限、reason 一句理由，最多 6 个分类；各分类 limit 之和不得超过 monthly_budget）、"
    "savings_target（月储蓄目标）、"
    "alerts（提醒，数组，可为空）。只输出 JSON，不要多余文字。用中文。"
)


class _ExpenseInsightPart(BaseModel):
    """LLM 负责的文本子集（数值字段一律由系统计算，不让模型碰）

    提到模块级：原先定义在 analyze_expense() 函数体内，每次请求都要重新构造
    Pydantic 模型并重新生成 JSON Schema 随请求下发。
    """
    summary: str = Field(description="一句话总结")
    insights: list[str] = Field(description="洞察，正好3条")
    suggestions: list[str] = Field(description="建议，正好3条")
    risk_level: str = Field(description="低/一般/高 三选一")


# 预算兜底上限：月总预算硬性不得超过月收入的这个比例。
# 历史缺口：monthly_budget 完全信任 LLM，月收入 5000 也可能输出「建议月总预算 8000」，
# 而前端会把它当建议直接展示（savings_target 当时被系统覆盖了，monthly_budget 没有）。
_BUDGET_INCOME_CAP = 0.9
# 各分类 limit 之和相对 monthly_budget 的容忍度，超出则按比例缩放
_CATEGORY_SUM_TOLERANCE = 1.05


def _sanitize_budget(plan: BudgetPlan, monthly_income: float) -> BudgetPlan:
    """预算数值一致性校验——把 LLM 的自由发挥夹回经济上说得通的区间。

    三道夹逼：
    1. monthly_budget 必须 > 0 且 ≤ 月收入 * _BUDGET_INCOME_CAP；
    2. 各分类 limit 归一到非负；
    3. 各分类 limit 之和 ≤ monthly_budget * _CATEGORY_SUM_TOLERANCE，
       超出按比例缩放（缩到容忍线内），避免「分类加起来远大于总预算」的
       自相矛盾建议。
    """
    cap = round(monthly_income * _BUDGET_INCOME_CAP, 2)
    if not plan.monthly_budget or plan.monthly_budget <= 0:
        plan.monthly_budget = cap
    elif plan.monthly_budget > cap:
        plan.monthly_budget = cap

    limits: list[dict] = []
    for item in plan.category_limits or []:
        try:
            limit = float(item.get("limit") or 0)
        except (TypeError, ValueError):
            limit = 0.0
        if limit < 0:
            limit = 0.0
        new_item = dict(item)
        new_item["limit"] = round(limit, 2)
        limits.append(new_item)
    plan.category_limits = limits

    total = sum(x["limit"] for x in limits)
    ceiling = plan.monthly_budget * _CATEGORY_SUM_TOLERANCE
    if total > ceiling > 0:
        ratio = ceiling / total
        for x in limits:
            x["limit"] = round(x["limit"] * ratio, 2)
    return plan


async def analyze_expense(ctx: dict, query: str | None = None,
                          user_id: int | None = None) -> ExpenseAnalysis:
    """消费分析（6.9）：ctx = build_user_context 的财务数据

    结构化输出：把 ExpenseAnalysis 交给 with_structured_output，
    LLM 只填 summary/insights/suggestions/risk_level，数值字段由系统计算补齐。

    query：用户自然语言诉求（ExpenseAnalyzeIn.query）。历史 bug 是该字段
    定义了、API 文档写了、前端传了，服务端却硬编码「请分析我的消费情况」
    并丢弃入参——于是「为什么餐饮涨了」和「随便分析」得到完全相同的分析。

    观测口径（审查报告 P0-1）：分析链此前直接 ainvoke，无 Timer 无 record_call，
    /admin/stats 的 usage 报表缺整个 analyze 场景。此处对齐 chat/bookkeeping 链：
    成功传 response（结构化对象无 usage_metadata，extract_tokens 兜底记 0）、
    失败记 ok=False，均按 user_id 落点。
    """
    demand = (query or "").strip() or "请分析我的消费情况"

    base_llm = get_analyze_llm()
    llm = base_llm.with_structured_output(_ExpenseInsightPart)
    prompt = (
        f"统计月份: {ctx['this_month']}\n"
        f"当月总收入: {ctx['total_income']}\n"
        f"当月总支出: {ctx['total_expense']}\n"
        f"上月总支出: {ctx['last_month_expense']}\n"
        f"当月支出Top分类: {ctx['top_categories']}\n"
        f"用户诉求: {demand}"
    )
    timer = Timer()
    try:
        part: _ExpenseInsightPart = await llm.ainvoke(
            [SystemMessage(content=ANALYZE_SYSTEM), HumanMessage(content=prompt)]
        )
    except Exception as e:
        record_call(KIND_ANALYZE, getattr(base_llm, "model_name", "?"), user_id,
                    timer=timer, ok=False, error=type(e).__name__)
        raise
    record_call(KIND_ANALYZE, getattr(base_llm, "model_name", "?"), user_id,
                response=part, timer=timer)

    income = float(ctx["total_income"])
    expense = float(ctx["total_expense"])
    rate = round((income - expense) / income * 100, 1) if income > 0 else 0.0

    return ExpenseAnalysis(
        summary=part.summary,
        total_expense=expense,
        top_categories=ctx["top_categories"],
        insights=part.insights,
        suggestions=part.suggestions,
        savings_rate=rate,
        risk_level=part.risk_level,
    )


async def plan_budget(monthly_income: float, savings_goal: float | None, ctx: dict,
                      user_id: int | None = None) -> BudgetPlan:
    """预算规划（6.10）：不传 savings_goal 时按 50/30/20 法则推导（储蓄=收入的20%）

    观测口径同 analyze_expense（审查报告 P0-1）：Timer + record_call 对齐。
    """
    target = savings_goal if savings_goal else round(monthly_income * 0.2, 2)

    base_llm = get_analyze_llm()
    llm = base_llm.with_structured_output(BudgetPlan)
    prompt = (
        f"用户月收入: {monthly_income}\n"
        f"月储蓄目标: {target}\n"
        f"上月总支出: {ctx.get('last_month_expense', 0)}\n"
        f"当月支出Top分类: {ctx.get('top_categories', [])}\n"
        f"请制定下月预算。"
    )
    timer = Timer()
    try:
        plan: BudgetPlan = await llm.ainvoke(
            [SystemMessage(content=BUDGET_SYSTEM), HumanMessage(content=prompt)]
        )
    except Exception as e:
        record_call(KIND_ANALYZE, getattr(base_llm, "model_name", "?"), user_id,
                    timer=timer, ok=False, error=type(e).__name__)
        raise
    record_call(KIND_ANALYZE, getattr(base_llm, "model_name", "?"), user_id,
                response=plan, timer=timer)
    plan.savings_target = target  # 储蓄目标以系统计算为准
    return _sanitize_budget(plan, monthly_income)
