"""对话记忆管理 — 控制历史消息 token 数"""
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

from sqlalchemy.ext.asyncio import AsyncSession

from ai import security as ai_security
from config.settings import KEEP_RECENT_MESSAGES, MAX_HISTORY_TOKENS

# 历史 bug：这两个常量原先在本文件里硬编码（MAX_TOKENS=2000 / KEEP_RECENT=6），
# 而 config/settings.py 同时定义了 MAX_HISTORY_TOKENS / KEEP_RECENT_MESSAGES 并
# 支持环境变量覆盖——两份定义，改 .env 不生效。现统一读 settings，单一口径。
MAX_TOKENS = MAX_HISTORY_TOKENS   # 近似：中文 1 字 ≈ 1 token，毕设够用
KEEP_RECENT = KEEP_RECENT_MESSAGES  # 最近 N 条


async def build_history(db: AsyncSession, session_id: str) -> list[BaseMessage]:
    """取历史消息窗口：从尾部往前累计，超 token 或超条数即停。

    只从库里取最后 KEEP_RECENT 条（crud.list_messages_tail，走
    idx_messages_session_ts 索引），而不是把整个会话读进来再切片。
    """
    from crud import ai as ai_crud

    if KEEP_RECENT <= 0:
        return []

    msgs = await ai_crud.list_messages_tail(db, session_id, KEEP_RECENT)  # 已升序
    picked: list[BaseMessage] = []
    used = 0
    for m in reversed(msgs):
        used += len(m.content)
        if used > MAX_TOKENS or len(picked) >= KEEP_RECENT:
            break
        cls = HumanMessage if m.role == "user" else AIMessage
        # 审查 P1-2：历史消息此前原样进 LLM，脱敏/注入过滤只盖住当前消息，
        # 历史里的手机号/卡号/身份证/邮箱会绕过安全管道上云，注入话术也能借
        # 历史进入上下文。这里对 user 消息套与当前消息同一套 sanitize
        # （routers/ai.py::_safe_user_text 同口径：上云脱敏，落库仍存原文）。
        content = ai_security.sanitize(m.content) if m.role == "user" else m.content
        picked.append(cls(content=content))
    picked.reverse()  # 恢复升序
    return picked
