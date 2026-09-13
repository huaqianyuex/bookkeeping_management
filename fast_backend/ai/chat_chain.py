"""对话链 — 处理用户聊天消息"""

# TODO: 实现见 06-AI模块.md


"""对话链 — 流式产出 LLM chunk"""
from langchain_core.messages import AIMessageChunk
from ai.llm import get_chat_llm

SYSTEM_PROMPT = "你是个人记账管理系统「小记」的 AI 助手……"

async def chat_stream(messages: list):
    """逐块 yield 文本；messages = [system, *history, human]"""
    async for chunk in get_chat_llm().astream(messages):
        if chunk.content:
            yield chunk.content