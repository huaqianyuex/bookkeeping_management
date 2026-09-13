"""对话记忆管理 — 控制历史消息 token 数"""

# TODO: 实现见 06-AI模块.md


async def get_history_messages(session_id: str, max_tokens: int = 2000):
    from crud import ai as ai_crud
    from config.db_config import get_db  # 或把 db 会话传进来
    ...
    # 思路：list_messages 按时间升序取全量 → 从尾部往前累计
    # 估算 token：len(content) 即可近似（中文 1 字 ≈ 1 token 足够毕设用）
    # 超出 max_tokens 或超过 KEEP_RECENT_MESSAGES(6) 条就停