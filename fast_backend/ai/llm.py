
"""LLM 客户端构造"""
from langchain_openai import ChatOpenAI
from config.settings import (
    CHAT_MODEL, ANALYZE_MODEL, EMBEDDING_MODEL,
    OPENAI_BASE_URL, AGNES_API_KEY,
)

_chat_llm: ChatOpenAI | None = None   # 进程内单例，避免每次请求重建客户端

def get_chat_llm() -> ChatOpenAI:
    """对话 LLM：温度稍高，回答自然"""
    global _chat_llm
    if _chat_llm is None:
        _chat_llm = ChatOpenAI(
            model=CHAT_MODEL,
            api_key=AGNES_API_KEY,
            base_url=OPENAI_BASE_URL,
            temperature=0.7,
            streaming=True,          # /chat/stream 需要
        )
    return _chat_llm

def get_analyze_llm() -> ChatOpenAI:
    """分析 LLM：温度 0，输出稳定（配合 .with_structured_output 用）"""
    return ChatOpenAI(model=ANALYZE_MODEL, api_key=AGNES_API_KEY,
                      base_url=OPENAI_BASE_URL, temperature=0)

def get_embeddings():
    from langchain_openai import OpenAIEmbeddings
    return OpenAIEmbeddings(model=EMBEDDING_MODEL, api_key=AGNES_API_KEY,
                            base_url=OPENAI_BASE_URL)