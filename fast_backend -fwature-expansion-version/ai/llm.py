"""LLM 客户端构造 — 全部进程内单例，避免每请求重建 httpx 连接池"""
from langchain_openai import ChatOpenAI
from config.settings import (
    CHAT_MODEL, CHAT_MODEL_PREMIUM, ANALYZE_MODEL, EMBEDDING_MODEL,
    OPENAI_BASE_URL, AGNES_API_KEY,
)

_chat_llm: ChatOpenAI | None = None   # 进程内单例，避免每次请求重建客户端
_premium_chat_llm: ChatOpenAI | None = None
_analyze_llm: ChatOpenAI | None = None
_embeddings = None


def _new_chat_llm(model: str) -> ChatOpenAI:
    return ChatOpenAI(
        model=model,
        api_key=AGNES_API_KEY,
        base_url=OPENAI_BASE_URL,
        temperature=0.7,
        streaming=True,          # /chat/stream 需要
    )


def get_chat_llm(premium: bool = False) -> ChatOpenAI:
    """对话 LLM：温度稍高，回答自然。premium=True 且配置了 CHAT_MODEL_PREMIUM 时走会员模型"""
    global _chat_llm, _premium_chat_llm
    if premium and CHAT_MODEL_PREMIUM:
        if _premium_chat_llm is None:
            _premium_chat_llm = _new_chat_llm(CHAT_MODEL_PREMIUM)
        return _premium_chat_llm
    if _chat_llm is None:
        _chat_llm = _new_chat_llm(CHAT_MODEL)
    return _chat_llm


def get_analyze_llm() -> ChatOpenAI:
    """分析 LLM：温度 0，输出稳定（配合 .with_structured_output 用）"""
    global _analyze_llm
    if _analyze_llm is None:
        _analyze_llm = ChatOpenAI(model=ANALYZE_MODEL, api_key=AGNES_API_KEY,
                                  base_url=OPENAI_BASE_URL, temperature=0)
    return _analyze_llm


def get_embeddings():
    global _embeddings
    if _embeddings is None:
        from langchain_openai import OpenAIEmbeddings
        _embeddings = OpenAIEmbeddings(model=EMBEDDING_MODEL, api_key=AGNES_API_KEY,
                                       base_url=OPENAI_BASE_URL)
    return _embeddings
