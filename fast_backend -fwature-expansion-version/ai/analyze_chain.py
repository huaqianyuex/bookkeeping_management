"""分析链 — 消费分析与预算建议（LLM 结构化输出）"""

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from ai.llm import get_analyze_llm
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
    "输出 JSON：monthly_budget（建议月总预算）、category_limits（数组，每项含 category 名称、"
    "limit 预算上限、reason 一句理由，最多 6 个分类）、savings_target（月储蓄目标）、"
    "alerts（提醒，数组，可为空）。只输出 JSON，不要多余文字。用中文。"
)


async def analyze_expense(ctx: dict) -> ExpenseAnalysis:
    """消费分析（6.9）：ctx = build_user_context 的财务数据

    结构化输出：把 ExpenseAnalysis 交给 with_structured_output，
    LLM 只填 summary/insights/suggestions/risk_level，数值字段由系统计算补齐。
    """
    # LLM 只负责文本字段的结构子集
    class _LLMPart(BaseModel):
        summary: str = Field(description="一句话总结")
        insights: list[str] = Field(description="洞察，正好3条")
        suggestions: list[str] = Field(description="建议，正好3条")
        risk_level: str = Field(description="低/一般/高 三选一")

    llm = get_analyze_llm().with_structured_output(_LLMPart)
    prompt = (
        f"统计月份: {ctx['this_month']}\n"
        f"当月总收入: {ctx['total_income']}\n"
        f"当月总支出: {ctx['total_expense']}\n"
        f"上月总支出: {ctx['last_month_expense']}\n"
        f"当月支出Top分类: {ctx['top_categories']}\n"
        f"用户诉求: 请分析我的消费情况"
    )
    part: _LLMPart = await llm.ainvoke([SystemMessage(content=ANALYZE_SYSTEM), HumanMessage(content=prompt)])

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


async def plan_budget(monthly_income: float, savings_goal: float | None, ctx: dict) -> BudgetPlan:
    """预算规划（6.10）：不传 savings_goal 时按 50/30/20 法则推导（储蓄=收入的20%）"""
    target = savings_goal if savings_goal else round(monthly_income * 0.2, 2)

    llm = get_analyze_llm().with_structured_output(BudgetPlan)
    prompt = (
        f"用户月收入: {monthly_income}\n"
        f"月储蓄目标: {target}\n"
        f"上月总支出: {ctx.get('last_month_expense', 0)}\n"
        f"当月支出Top分类: {ctx.get('top_categories', [])}\n"
        f"请制定下月预算。"
    )
    plan: BudgetPlan = await llm.ainvoke([SystemMessage(content=BUDGET_SYSTEM), HumanMessage(content=prompt)])
    plan.savings_target = target  # 储蓄目标以系统计算为准
    return plan
