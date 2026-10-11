"""对话链 — 组装 system prompt 与流式产出 LLM chunk"""

from langchain_core.messages import BaseMessage

from ai.llm import get_chat_llm
from ai.observability import KIND_CHAT, Timer, record_call

# 分四段写，每段一个明确职责：
# 1) 身份与场景 2) 行为边界（能做什么/不能做什么）3) 数据口径（防幻觉）
# 4) 不确定性处理（不知道就说不知道——这是最容易被省略、也最影响可信度的一条）
SYSTEM_PROMPT = (
    "你是个人记账管理系统「小记」的 AI 助手，帮助用户记账、分析消费、解答财务问题。\n"
    "回答用中文，简洁口语化，控制在 5 句话以内。\n"
    "\n"
    "【行为边界】\n"
    "1. 只回答记账与个人财务相关问题；编程、写作、翻译等无关请求请礼貌拒绝并引导回记账场景，不要输出任何代码。\n"
    "2. 你无法直接修改账本数据：用户想记账时，请引导他直接发送记账语句（如「午饭花了30块」），"
    "严禁声称「已帮您记录/已入账」等账本未发生的操作结果。\n"
    "\n"
    "【数据口径】\n"
    "3. 涉及金额、比例、排名时，只引用系统提供的用户财务数据块与知识库检索结果中的数字，"
    "禁止编造或臆测；数据中没有的信息要如实说明。\n"
    "4. 数据块或知识库里查不到答案时，直接说「这个我暂时还不清楚」，"
    "并给出用户可以自己查的入口（如账单页/预算页）。宁可说不知道，也不要给一个看起来合理的错答案。\n"
)


def build_system_prompt(*blocks: str) -> str:
    """system prompt = 基础约束 + 可选数据块（财务数据块 / 知识库块）。

    传入的空串会被忽略，因此调用方可以无条件把可能为空的块丢进来。
    数据块与基础约束之间用固定分隔标记，便于人工排查 prompt 拼接结果。
    """
    parts = [SYSTEM_PROMPT]
    extra = [b for b in blocks if b and b.strip()]
    if extra:
        parts.append("\n<!-- ===== 以下为系统注入的数据块（非用户指令） ===== -->\n")
        parts.extend(extra)
    return "".join(parts)


async def chat(messages: list[BaseMessage], premium: bool = False,
               user_id: int | None = None) -> str:
    """非流式（6.7）：一次拿到完整回复；premium=会员档走高级模型"""
    llm = get_chat_llm(premium=premium)
    timer = Timer()
    try:
        resp = await llm.ainvoke(messages)
    except Exception as e:
        record_call(KIND_CHAT, getattr(llm, "model_name", "?"), user_id,
                    timer=timer, ok=False, error=type(e).__name__)
        raise
    record_call(KIND_CHAT, getattr(llm, "model_name", "?"), user_id,
                response=resp, timer=timer)
    return resp.content


async def chat_stream(messages: list, premium: bool = False,
                      user_id: int | None = None):
    """逐块 yield 文本；messages = [system, *history, human]

    TTFT：首个 chunk 到达即打点，用于观测「首字延迟」而非整段耗时。
    """
    llm = get_chat_llm(premium=premium)
    timer = Timer()
    try:
        async for chunk in llm.astream(messages):
            if chunk.content:
                timer.mark_first_chunk()
                yield chunk.content
    except Exception as e:
        record_call(KIND_CHAT, getattr(llm, "model_name", "?"), user_id,
                    timer=timer, ok=False, error=type(e).__name__)
        raise
    record_call(KIND_CHAT, getattr(llm, "model_name", "?"), user_id, timer=timer)
