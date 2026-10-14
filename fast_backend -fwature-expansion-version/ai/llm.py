"""LLM 客户端构造 — 全部进程内单例，避免每请求重建 httpx 连接池"""
from langchain_openai import ChatOpenAI
from config.settings import (
    CHAT_MODEL, CHAT_MODEL_PREMIUM, ANALYZE_MODEL, EMBEDDING_MODEL,
    OPENAI_BASE_URL, AGNES_API_KEY,
    LLM_TIMEOUT_SECONDS,
    CHAT_MAX_TOKENS, ANALYZE_MAX_TOKENS,
)

_chat_llm: ChatOpenAI | None = None   # 进程内单例，避免每次请求重建客户端
_premium_chat_llm: ChatOpenAI | None = None
_analyze_llm: ChatOpenAI | None = None
_embeddings = None


def _new_chat_llm(model: str) -> ChatOpenAI:
    # timeout / max_retries / max_tokens 必须显式给：
    # - 无 timeout：网关挂起时请求长挂，占住 ai_concurrency 的进程内并发槽，
    #   表现为「并发已达上限」但其实上一条早已失联；
    # - max_retries **必须为 0**：重试统一由 ai/retry.with_retry 负责（指数退避 +
    #   总预算 + 只重试瞬时故障）。若这里再留 SDK 重试，两层相乘会把一次用户请求
    #   放大成 N×M 次上游调用与计费——这正是审查报告 P1-6 要避免的；
    # - 无 max_tokens：输出无界，异常情况下可烧掉大量 token 且全量落库。
    return ChatOpenAI(
        model=model,
        api_key=AGNES_API_KEY,
        base_url=OPENAI_BASE_URL,
        temperature=0.7,
        streaming=True,          # /chat/stream 需要
        max_tokens=CHAT_MAX_TOKENS,
        timeout=LLM_TIMEOUT_SECONDS,
        max_retries=0,
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
        # ANALYZE_MAX_TOKENS 比对话大：ExpenseAnalysis 要装 3 条洞察 + 3 条建议
        # + summary + risk_level，还要装 category_limits；给太小会被截断成非法
        # JSON，with_structured_output 直接抛异常。
        _analyze_llm = ChatOpenAI(model=ANALYZE_MODEL, api_key=AGNES_API_KEY,
                                  base_url=OPENAI_BASE_URL, temperature=0,
                                  max_tokens=ANALYZE_MAX_TOKENS,
                                  timeout=LLM_TIMEOUT_SECONDS,
                                  max_retries=0)   # 重试见 ai/retry.with_retry
    return _analyze_llm


def get_embeddings():
    global _embeddings
    if _embeddings is None:
        from langchain_openai import OpenAIEmbeddings
        # 审查 P2-5：Embedding 与 chat/analyze 同口径——显式 timeout + SDK 重试归零。
        # 无 timeout 时（SDK 默认约 600s）知识库 Embedding 挂起会长期占住
        # ai_concurrency 并发槽，/faq/rebuild 阻塞且 SDK 默认 2 次重试放大计费；
        # 瞬时失败由调用方降级处理（faq_retriever._embed_query 降级关键词检索）。
        _embeddings = OpenAIEmbeddings(model=EMBEDDING_MODEL, api_key=AGNES_API_KEY,
                                       base_url=OPENAI_BASE_URL,
                                       timeout=LLM_TIMEOUT_SECONDS,
                                       max_retries=0)
    return _embeddings
