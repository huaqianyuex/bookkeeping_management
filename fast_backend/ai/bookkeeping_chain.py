"""自然语言记账解析链 — LLM 结构化抽取（06 §11）

用分析 LLM（温度 0，ai/llm.py 的 get_analyze_llm）+ with_structured_output
把口语化消息解析成 Parsed 结构；金额/日期的清洗兜底交给 ai/normalizers.py，
分类映射交给 ai/category_alias.py。本模块只做「抽取与意图判定」。

口径（05 §6.2）：
- 金额无法从原文确定时 amount=None，绝不猜测 → 上层触发 clarify 追问；
- 非消费类消息（闲聊/查询）items 为空、intent 标注 query/chitchat；
- 多笔消费逐条拆分（上层限制单条消息最多 10 笔）。
"""
from datetime import date

from pydantic import BaseModel, Field

from ai.llm import get_analyze_llm


class ParsedItem(BaseModel):
    """单笔消费的抽取结果"""
    amount: float | None = Field(None, description="金额；原文无法确定则为 null，绝不猜测")
    amount_raw: str | None = Field(None, description="原文中的金额片段，如「79块」")
    type: int = Field(1, description="0=支出 1=收入（records 口径）")
    category_name: str | None = Field(None, description="分类名（优先用系统已有分类的叫法）")
    date_expr: str | None = Field(None, description="原文日期词，如「昨天」「上周三」；无则 null")
    date: str | None = Field(None, description="按今天推算的 yyyy-MM-dd；推不出则 null")
    remark: str | None = Field(None, description="备注（消费内容摘要）")
    confidence: float = Field(0.0, description="抽取置信度 0~1")
    is_expense_related: bool = Field(True, description="是否消费相关")


class Parsed(BaseModel):
    """整条消息的解析结果"""
    intent: str = Field("bookkeeping", description="bookkeeping/amend/delete/query/chitchat")
    items: list[ParsedItem] = Field(default_factory=list, description="消费条目（非消费类为空）")


_PROMPT = """你是记账解析器。今天是 {today}。
用户消息："{message}"
系统已有分类：{categories}

要求：
1. 逐条抽取消费/收入条目；金额无法从原文确定时 amount 填 null，绝不猜测；
2. 相对日期（今天/昨天/前天/大前天/N天前/本周三/上周三/M月D号）按今天推算为 yyyy-MM-dd，
   无日期词 date 与 date_expr 均为 null；
3. 分类优先用「系统已有分类」中的叫法，匹配不上再给口语词；
4. 非消费类消息（闲聊/查询/指令）items 返回空数组，intent 标 query 或 chitchat；
5. 一条消息含多笔消费时拆成多个条目。"""


async def parse_bookkeeping(message: str, today: str, category_names: list[str]) -> Parsed:
    """解析口语化消息为 Parsed；LLM 失败时向上抛异常（路由兜底 ai_error）"""
    llm = get_analyze_llm()
    structured_llm = llm.with_structured_output(Parsed)
    prompt = _PROMPT.format(
        today=today or date.today().isoformat(),
        message=message,
        categories="、".join(category_names) if category_names else "（无，自行归类）",
    )
    result = await structured_llm.ainvoke(prompt)
    return result if isinstance(result, Parsed) else Parsed.model_validate(result)
