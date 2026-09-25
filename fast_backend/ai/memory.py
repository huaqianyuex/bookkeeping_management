"""对话记忆管理 — 控制历史消息 token 数"""
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

from sqlalchemy.ext.asyncio import AsyncSession

MAX_TOKENS = 2000  # 近似：中文 1 字 ≈ 1 token，毕设够用
KEEP_RECENT = 6  # 最近 N 条


async def build_history(db: AsyncSession, session_id: str) -> list[BaseMessage]:
    """取历史消息窗口：从尾部往前累计，超 token 或超条数即停"""
    from crud import ai as ai_crud

    msgs = await ai_crud.list_messages(db, session_id)  # 升序
    picked: list[BaseMessage] = []
    used = 0
    for m in reversed(msgs):
        used += len(m.content)
        if used > MAX_TOKENS or len(picked) >= KEEP_RECENT:
            break
        cls = HumanMessage if m.role == "user" else AIMessage
        picked.append(cls(content=m.content))
    picked.reverse()  # 恢复升序
    return picked
