"""APScheduler 定时任务 — 物理清除过期软删数据

背景
----
AI 会话是**软删**（``sessions.deleted_at > 0``），消息、反馈、记账日志也都带
软删/回滚语义。此前本模块是空桩，导致：

- 被删除的会话与它的 messages **永久堆积**，AI 相关表体积只增不减；
- ``settings.PURGE_INTERVAL_HOURS`` / ``PURGE_DELAY_DAYS`` 定义了却无人读取。

口径（07 §1）
------------
- 每 ``PURGE_INTERVAL_HOURS`` 小时跑一次；
- 只清理**删除时间早于 ``PURGE_DELAY_DAYS`` 天**的记录，给用户留反悔窗口
  （也避免删掉正在被 ``draft_id`` 追问续写引用的草稿）；
- ``messages`` 通过 ``ON DELETE CASCADE`` 随会话一起消失，无需单独删；
- ``feedback`` 的外键指向 ``messages``，同样级联。

依赖
----
APScheduler 为**可选依赖**（``requirements.txt`` 里默认注释）。未安装时
:func:`start_scheduler` 返回 ``False`` 并只记一条 warning——**绝不因为缺可选
依赖而让服务起不来**。安装：``pip install apscheduler>=3.10``。
"""

import logging
import time

from config.settings import PURGE_DELAY_DAYS, PURGE_INTERVAL_HOURS

logger = logging.getLogger(__name__)

# 软删阈值（毫秒）。deleted_at 存的是毫秒时间戳，0 表示未删。
def _cutoff_ms() -> int:
    return int((time.time() - PURGE_DELAY_DAYS * 86400) * 1000)


async def purge_expired_sessions(db) -> dict:
    """物理删除「删除时间超过 PURGE_DELAY_DAYS 天」的软删会话，返回清理条数。

    调用方负责事务与关闭；这里只做删除与计数，不 commit。
    """
    from sqlalchemy import delete, func, select

    from models.chat import ChatMessage, ChatSession

    cutoff = _cutoff_ms()

    # 先算条数用于日志/监控，再删——两条 SQL 都带 deleted_at > 0，
    # 绝不会误删未删除的会话。
    deleted = await db.execute(
        delete(ChatSession).where(
            ChatSession.deleted_at > 0,
            ChatSession.deleted_at < cutoff,
        )
    )
    session_count = deleted.rowcount or 0

    # 兜底清理孤儿消息：sessions 已删但 messages 因历史原因残留
    # （正常由 CASCADE 处理，这里防御性执行，正常情况下应为 0）
    msg_deleted = await db.execute(
        delete(ChatMessage).where(
            ChatMessage.session_id.notin_(select(ChatSession.id))
        )
    )
    orphan_count = msg_deleted.rowcount or 0

    await db.commit()
    result = {"sessions": session_count, "orphanMessages": orphan_count}
    if session_count or orphan_count:
        logger.info("purge expired sessions: %s", result)
    return result


async def _purge_job() -> None:
    """调度器回调：自己开一个会话，跑完即关。任何异常都吞掉，
    避免一次失败导致 APScheduler 停止后续调度。"""
    from config.db_config import AsyncSessionLocal

    try:
        async with AsyncSessionLocal() as session:
            await purge_expired_sessions(session)
    except Exception:
        logger.exception("purge job failed（本次跳过，等待下一轮）")


# 调度器实例的模块级引用。
# 不用 ``AsyncIOScheduler.get_instance()``：该类方法并非在所有 APScheduler
# 版本上都存在（实测当前环境直接抛 AttributeError），且模块级引用更可控。
_scheduler = None


def start_scheduler():
    """启动定时调度器。

    返回 True=已启动；False=未启动（APScheduler 未安装 / 无运行中的事件循环 / 启动异常）。
    调用方**不应**因返回 False 而中断应用启动——这是可选增强，不是硬依赖。

    ⚠️ 必须在**运行中的事件循环内**调用（AsyncIOScheduler 依赖它）。本项目由
    ``main.lifespan`` 调用，满足条件；同步上下文调用会返回 False 并记日志。
    """
    global _scheduler
    try:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        from apscheduler.triggers.interval import IntervalTrigger
    except ImportError:
        logger.warning(
            "APScheduler 未安装，软删清理任务未启动（会话数据将持续堆积）。"
            "需要清理请执行：pip install apscheduler>=3.10"
        )
        return False

    if _scheduler is not None and _scheduler.running:
        return True

    scheduler = AsyncIOScheduler(timezone="Asia/Shanghai")
    scheduler.add_job(
        _purge_job,
        trigger=IntervalTrigger(hours=PURGE_INTERVAL_HOURS),
        id="purge_expired_sessions",
        replace_existing=True,
        max_instances=1,          # 上一轮没跑完就不叠加
        coalesce=True,            # 积压的多次触发合并成一次
    )
    try:
        scheduler.start()
    except RuntimeError as e:
        # 最常见原因：无运行中的事件循环（从同步上下文调用）。属用法问题，降级为 warning
        logger.warning("purge scheduler 未启动（需在事件循环内调用）: %s", e)
        return False
    except Exception:
        logger.exception("APScheduler 启动失败，软删清理任务未启用")
        return False

    _scheduler = scheduler
    logger.info(
        "purge scheduler started: every %sh, retain %sd",
        PURGE_INTERVAL_HOURS, PURGE_DELAY_DAYS,
    )
    return True


def stop_scheduler():
    """停止定时调度器（应用关闭时调用）。任何异常都吞掉，不影响应用退出。"""
    global _scheduler
    try:
        if _scheduler is not None and _scheduler.running:
            _scheduler.shutdown(wait=False)
            logger.info("purge scheduler stopped")
        _scheduler = None
    except Exception:
        logger.exception("停止 purge scheduler 失败")
        _scheduler = None