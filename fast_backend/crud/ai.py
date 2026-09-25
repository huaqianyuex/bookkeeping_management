"""AI 对话数据访问层 — 骨架桩，业务逻辑由你实现

⚠️ 口径（models/chat.py 头注释 / 10-实现骨架.md §六）：
- 四张 AI 表（sessions/messages/feedback/faq）**没有 status 列**，会话软删用
  `deleted_at`（0=未删，>0=删除毫秒）——旧桩里的 `ChatSession.status == 1` 是错的；
- 主键是业务字符串 ID：`session_/msg_/feedback_ {毫秒}_{随机≤9位}`，用 `new_id()` 生成；
- 时间列均为 BIGINT 毫秒。

自然语言记账日志（ai_bookkeeping_logs）的访问函数也集中在本文件，
幂等去重逻辑（§6.15 第 3 步）依赖 `find_log_by_client_msg` / `find_recent_by_dedup`。
"""

import random
import string
import time
from datetime import datetime, timedelta

from sqlalchemy import func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from models.bookkeeping import AiBookkeepingLog
from models.chat import ChatMessage, ChatSession, Faq, Feedback
from models.record import Record
from utils.security import escape_like


def new_id(prefix: str) -> str:
    """生成业务字符串 ID：{prefix}_{毫秒}_{随机≤9位}（对齐旧 Express substring(2,11)）"""
    rand = "".join(random.choices(string.ascii_lowercase + string.digits, k=9))
    return f"{prefix}_{int(time.time() * 1000)}_{rand}"


def now_ms() -> int:
    """当前毫秒时间戳——AI 表时间列统一用这个，不要用 datetime"""
    return int(time.time() * 1000)


# ── 会话 sessions ──────────────────────────────────────────────────────

async def get_session(db: AsyncSession, session_id: str) -> ChatSession | None:
    """按 ID 查会话（不过滤软删；是否可用由调用方判断 deleted_at）"""
    # TODO: 实现
    result = await db.execute(select(ChatSession).where(ChatSession.id == session_id))
    return result.scalar_one_or_none()


async def get_user_session(db: AsyncSession, session_id: str, user_id: int) -> ChatSession | None:
    """按 ID 查**本人未删除**的会话（6.3 重命名 / 6.7 对话 / 6.15 记账的归属校验都用它）"""
    # TODO: 实现（WHERE id=:sid AND user_id=:uid AND deleted_at=0）
    result=await db.execute(select(ChatSession).where(
        ChatSession.id==session_id,
        ChatSession.user_id==user_id,
        ChatSession.deleted_at==0
    ))
    return result.scalar_one_or_none()

async def list_sessions(
    db: AsyncSession,
    user_id: int,
    keyword: str = "",
    sort: str = "updated",   # 仅 updated / created
    order: str = "desc",     # 仅 asc / desc
    page: int = 1,
    size: int = 20,
):
        """会话列表（6.2）：仅 deleted_at=0 AND user_id=:uid，返回 (rows, total)"""
        # 1) 参数夹取与白名单（也可放路由层，但放这里保证仓储自身安全）
        sort_col = ChatSession.updated_at if sort == "updated" else ChatSession.created_at
        order_col = sort_col.desc() if order == "desc" else sort_col.asc()
        page = max(page, 1)
        size = min(max(size, 1), 100)

        # 2) 基础条件
        cond = [ChatSession.user_id == user_id, ChatSession.deleted_at == 0]
        if keyword:
            kw = f"%{escape_like(keyword)}%"
            # title 命中 或 该会话下任一消息 content 命中（EXISTS，不产生重复行）
            # 使用 escape='\\' 避免 % / _ 被当通配符（P2-4.2）
            cond.append(or_(
                ChatSession.title.like(kw, escape="\\"),
                select(ChatMessage.id).where(
                    ChatMessage.session_id == ChatSession.id,
                    ChatMessage.content.like(kw, escape="\\"),
                ).exists(),
            ))

        # 3) 计数（与列表同条件）
        total = (await db.execute(
            select(func.count()).select_from(ChatSession).where(*cond)
        )).scalar_one()

        # 4) 每会话末条消息（preview）与消息数：一次 JOIN 子查询聚合，避免 N+1
        msg_agg = (
            select(
                ChatMessage.session_id,
                func.count().label("message_count"),
                func.max(ChatMessage.timestamp).label("last_ts"),
            )
            .group_by(ChatMessage.session_id)
            .subquery()
        )
        # preview 取末条 content 与 role：会话量小（page≤100）用相关子查询即可
        last_msg = (
            select(ChatMessage.content)
            .where(ChatMessage.session_id == ChatSession.id)
            .order_by(ChatMessage.timestamp.desc())
            .limit(1)
            .correlate(ChatSession)
            .scalar_subquery()
        )
        last_role = (
            select(ChatMessage.role)
            .where(ChatMessage.session_id == ChatSession.id)
            .order_by(ChatMessage.timestamp.desc())
            .limit(1)
            .correlate(ChatSession)
            .scalar_subquery()
        )

        rows = (await db.execute(
            select(
                ChatSession,
                last_msg.label("preview_content"),
                last_role.label("preview_role"),
                func.coalesce(msg_agg.c.message_count, 0).label("message_count"),
            )
            .outerjoin(msg_agg, msg_agg.c.session_id == ChatSession.id)
            .where(*cond)
            .order_by(order_col,
                      ChatSession.id.desc())  # 恒追加 id DESC 保证稳定
            .offset((page - 1) * size)
            .limit(size)
        )).all()

        return rows, total





async def create_session(db: AsyncSession, user_id: int, title: str = "新对话") -> ChatSession:
    """新建会话（6.1）：id=new_id("session")，auto_title=1，created_at=updated_at=now_ms()"""
    # TODO: 实现
    session = ChatSession(
        id=new_id("session"),
        user_id=user_id,
        title=title[:50],
        auto_title=1,
        created_at=now_ms(),
        updated_at=now_ms(),
        deleted_at=0,
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session


async def rename_session(db: AsyncSession, session_id: str, user_id: int, title: str):
    """重命名会话（6.3）：title + auto_title=0（锁定，AI 不再自动改标题）+ updated_at=now_ms()

    返回更新后的 ChatSession；会话不存在/非本人/已删返回 None。
    """
    # TODO: 实现
    stmt=update(ChatSession)\
        .where(ChatSession.id==session_id,
               ChatSession.user_id==user_id,
               ChatSession.deleted_at==0
               ).values(title=title, auto_title=0, updated_at=now_ms())

    result=await db.execute(stmt)
    await db.commit()
    if result.rowcount==0:
        return None

    return await get_user_session(db,session_id,user_id)



async def soft_delete_session(db: AsyncSession, session_id: str, user_id: int) -> bool:
    """软删单个会话（6.4）：UPDATE ... SET deleted_at=now_ms() WHERE id & user_id & deleted_at=0

    返回是否真的删了（rowcount>0）；勿物理 DELETE。
    """
    stmt=update(ChatSession)\
        .where(ChatSession.id==session_id,
               ChatSession.user_id==user_id,
               ChatSession.deleted_at==0
               ).values(deleted_at=now_ms())


    result=await db.execute(stmt)
    await db.commit()
    return result.rowcount>0


async def batch_soft_delete_sessions(db: AsyncSession, user_id: int, ids: list[str]) -> int:
    """批量软删会话（6.5）：返回实际删除条数（仅本人且未删的计入）"""
    if not ids:
        return 0

    stmt=update(ChatSession)\
        .where(
                ChatSession.user_id==user_id,
               ChatSession.id.in_(ids),
               ChatSession.deleted_at==0
               ).values(deleted_at=now_ms())
    result=await db.execute(stmt)
    await db.commit()
    return result.rowcount


# ── 消息 messages ──────────────────────────────────────────────────────

async def list_messages(db: AsyncSession, session_id: str):
    """会话消息列表（6.6）：按 timestamp 升序"""
    # TODO: 实现
    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.timestamp.asc())
    )
    return result.scalars().all()


async def add_message(db: AsyncSession, session_id: str, role: str, content: str) -> ChatMessage:
    """新增消息（6.7/6.8/6.15 落库用）：id=new_id("msg")，timestamp=now_ms()

    TODO: 插入后顺带 UPDATE sessions.updated_at=now_ms()（会话列表按它排序）
    """
    # TODO: 实现
    msg = ChatMessage(id=new_id("msg"), session_id=session_id,
                      role=role, content=content, timestamp=now_ms())
    db.add(msg)
    await db.execute(update(ChatSession).where(ChatSession.id == session_id)
                     .values(updated_at=now_ms()))  # 顺带刷新会话排序时间
    await db.commit()
    return msg




# ── 反馈 feedback ──────────────────────────────────────────────────────

async def create_feedback(
    db: AsyncSession, user_id: int, message_id: str, rating: int, comment: str | None,
):
    """保存反馈（6.13）：id=new_id("feedback")，timestamp=now_ms()

    user_id 为反馈人（feedback.user_id 已补列），支持按用户隔离/统计。
    """
    feedback = Feedback(
        id=new_id("feedback"),
        user_id=user_id,
        message_id=message_id,
        rating=rating,
        comment=comment,
        timestamp=now_ms(),
    )
    db.add(feedback)
    await db.flush()
    return feedback


async def check_message_owner(db: AsyncSession, message_id: str, user_id: int) -> bool:
    """消息归属校验：messages -> sessions.user_id"""
    result = await db.execute(
        select(ChatMessage.id)
        .join(ChatSession, ChatSession.id == ChatMessage.session_id)
        .where(ChatMessage.id == message_id, ChatSession.user_id == user_id)
    )
    return result.scalar_one_or_none() is not None









# ── 统计（6.14 /api/ai/admin/stats）────────────────────────────────────

async def ai_stats(db: AsyncSession) -> dict:
    """AI 使用统计：全站会话/消息/反馈总数 + 平均评分

    口径（6.14）：全量 COUNT，不过滤 deleted_at；无数据时 averageRating 回 0。
    """
    sessions = await db.scalar(select(func.count()).select_from(ChatSession))
    messages = await db.scalar(select(func.count()).select_from(ChatMessage))
    feedback = await db.scalar(select(func.count()).select_from(Feedback))
    avg = await db.scalar(select(func.avg(Feedback.rating)))

    return {
        "totalSessions": sessions or 0,
        "totalMessages": messages or 0,
        "totalFeedback": feedback or 0,
        "averageRating": round(float(avg), 1) if avg is not None else 0,
    }






# ── FAQ faq ────────────────────────────────────────────────────────────

async def list_faq(db: AsyncSession) -> list[Faq]:
    """全量 FAQ（ai/faq_retriever.py 启动建索引、6.12 重建用）"""
    result = await db.execute(select(Faq))
    return result.scalars().all()


# ── 记账日志 ai_bookkeeping_logs（6.15-6.17）────────────────────────────

async def get_records_by_ids(db: AsyncSession, ids: list[int], user_id: int | None = None) -> list:
    """按 ID 数组查本人记账记录（duplicate 回显用）

    传 user_id 时额外做归属过滤（防后续 调用者传入外部 ID 数组时越权）。
    未传时仅返回未删行（历史行为，仅供内部可信调用点使用）。
    """
    if not ids:
        return []
    conds = [Record.id.in_(ids), Record.status == 1]
    if user_id is not None:
        conds.append(Record.user_id == user_id)
    result = await db.execute(select(Record).where(*conds))
    return list(result.scalars().all())


async def create_bookkeeping_log(db: AsyncSession, **fields) -> AiBookkeepingLog:
    """写一条记账日志：调用方负责 request_id=new_id("bk")、dedup_hash、intent/action

    修复提示（§6.15）：幂等靠 uk_abk_client_msg 唯一键冲突兜底——
    捕获 IntegrityError 后回查首次记录返回 duplicate，**禁止先 SELECT 再 INSERT**。
    """
    log = AiBookkeepingLog(**fields)
    db.add(log)
    try:
        await db.flush()
        return log
    except IntegrityError:
        # 唯一键冲突（uk_abk_client_msg）：并发重发同一 client_msg_id 时兜底，
        # 回滚本次插入，由调用方回查首次日志走 duplicate 分支
        await db.rollback()
        raise


async def find_log_by_client_msg(db: AsyncSession, user_id: int, client_msg_id: str):
    """强幂等查询：本人 + 同 client_msg_id 的首次成功日志（status=1 且 record_ids 非空）"""
    result = await db.execute(
        select(AiBookkeepingLog)
        .where(
            AiBookkeepingLog.user_id == user_id,
            AiBookkeepingLog.client_msg_id == client_msg_id,
            AiBookkeepingLog.status == 1,
            AiBookkeepingLog.record_ids.isnot(None),
        )
        .order_by(AiBookkeepingLog.id.asc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def find_recent_by_dedup(db: AsyncSession, user_id: int, dedup_hash: str, window_seconds: int = 300):
    """弱幂等查询：window_seconds（默认 300 秒）内同 dedup_hash 的首次成功日志

    时间列 created_at 是 DATETIME，比较用 datetime.now() - timedelta(seconds=window_seconds)。
    """
    since = datetime.now() - timedelta(seconds=window_seconds)
    result = await db.execute(
        select(AiBookkeepingLog)
        .where(
            AiBookkeepingLog.user_id == user_id,
            AiBookkeepingLog.dedup_hash == dedup_hash,
            AiBookkeepingLog.status == 1,
            AiBookkeepingLog.record_ids.isnot(None),
            AiBookkeepingLog.created_at >= since,
        )
        .order_by(AiBookkeepingLog.id.asc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def get_bookkeeping_log(db: AsyncSession, log_id: int):
    """按 ID 查记账日志（draft_id 续写 / 修改链路回溯用）"""
    result = await db.execute(select(AiBookkeepingLog).where(AiBookkeepingLog.id == log_id))
    return result.scalar_one_or_none()


async def update_bookkeeping_log(db: AsyncSession, log_id: int, **fields):
    """回写日志：record_ids / parse_json / action / status（0草稿 1已处理 2已回滚）"""
    if not fields:
        return None
    await db.execute(
        update(AiBookkeepingLog).where(AiBookkeepingLog.id == log_id).values(**fields)
    )
    return await get_bookkeeping_log(db, log_id)
