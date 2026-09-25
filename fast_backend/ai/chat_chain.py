"""对话链 — 处理用户聊天消息"""

# TODO: 实现见 06-AI模块.md


"""对话链 — 流式产出 LLM chunk"""



from langchain_core.messages import AIMessage, BaseMessage

from ai.llm import get_chat_llm

SYSTEM_PROMPT = "你是个人记账管理系统「小记」的 AI 助手，帮助用户记账、分析消费、解答财务问题。回答用中文，简洁口语化。仅回答记账与个人财务相关问题；编程、写作、翻译等无关请求请礼貌拒绝并引导回记账场景，不要输出任何代码"


async def chat(messages: list[BaseMessage]) -> str:
    """非流式（6.7）：一次拿到完整回复"""
    return (await get_chat_llm().ainvoke(messages)).content

async def chat_stream(messages: list):
    """逐块 yield 文本；messages = [system, *history, human]"""
    async for chunk in get_chat_llm().astream(messages):
        if chunk.content:
            yield chunk.content
