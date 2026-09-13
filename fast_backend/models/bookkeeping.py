"""AI 自然语言记账日志模型 — 对应 ai_bookkeeping_logs 表

字段与索引口径以 `sql/init_mysql.sql` 与 `docs/fastapi-backend/02-数据库设计.md` §3.5 为准。

一张表承担三件事：
1. **幂等去重** —— `client_msg_id` 强幂等（不过期）+ `dedup_hash` 5 分钟窗口弱幂等，
   保证同一条消息不会重复入账；
2. **追问草稿** —— 信息不全（如缺金额）时暂存半成品（`status=0`），
   用户补充后携带 `draft_id` 续写，30 分钟过期；
3. **审计与纠错样本** —— 记录「AI 记账 → 用户修改/撤销」的完整链路（`parent_id` 自关联）。

注意：
- `client_msg_id` 允许为 NULL：MySQL 唯一索引对多行 NULL 不冲突，
  这正是「未传幂等键时不触发强幂等」的预期行为，**勿改成 NOT NULL**；
- `session_id` / `parent_id` 的外键是 `ON DELETE SET NULL`（会话被清理后日志保留，
  仅断开引用），与 `user_id` 的 `CASCADE` 不同；
- `parse_json` / `record_ids` 是 JSON 列，**不能带默认值**（MySQL 限制）。
"""

from typing import Any

from sqlalchemy import (
    CHAR,
    JSON,
    BigInteger,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, IdMixin, TimestampMixin


class AiBookkeepingLog(Base, IdMixin, TimestampMixin):
    """AI 自然语言记账日志表（幂等 / 追问草稿 / 审计）"""
    __tablename__ = "ai_bookkeeping_logs"

    __table_args__ = (
        UniqueConstraint("request_id", name="uk_abk_request_id"),
        UniqueConstraint("user_id", "client_msg_id", name="uk_abk_client_msg"),
        Index("idx_abk_dedup", "user_id", "dedup_hash", "created_at"),
        Index("idx_abk_user_recent", "user_id", "created_at"),
        Index("idx_abk_session", "session_id", "id"),
        Index("idx_abk_parent", "parent_id"),
    )

    request_id: Mapped[str] = mapped_column(
        String(64), nullable=False, comment="对外请求 ID，格式 bk_{毫秒}_{随机}"
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        comment="发起用户 ID",
    )
    session_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("sessions.id", ondelete="SET NULL"),
        comment="关联的 AI 会话 ID，可为空",
    )
    message_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("messages.id", ondelete="SET NULL"),
        comment="关联的消息 ID，可为空",
    )
    client_msg_id: Mapped[str | None] = mapped_column(
        String(64), comment="客户端幂等键（UUID）；NULL 表示不启用强幂等"
    )
    dedup_hash: Mapped[str] = mapped_column(
        CHAR(64), nullable=False, comment="SHA256(user_id|归一化文本)，用于弱幂等窗口去重"
    )
    raw_text: Mapped[str] = mapped_column(String(500), nullable=False, comment="用户原始消息文本")
    intent: Mapped[str] = mapped_column(
        String(20), nullable=False,
        comment="意图：bookkeeping/amend/delete/query/chitchat",
    )
    action: Mapped[str] = mapped_column(
        String(20), nullable=False,
        comment="处理结果：created/clarify/ignored/duplicate/preview/amend/delete/error",
    )
    parse_json: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, comment="LLM 抽取出的原始解析结果（06 §11.1 结构）"
    )
    record_ids: Mapped[list[int] | None] = mapped_column(
        JSON, comment="本次入账的 records.id 数组，如 [128,129]"
    )
    error_msg: Mapped[str | None] = mapped_column(
        String(200), comment="失败原因（仅内部记录，不回显给前端）"
    )
    status: Mapped[int] = mapped_column(
        Integer, default=1, nullable=False,
        comment="状态：0=草稿待追问，1=已处理，2=已回滚",
    )
    parent_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("ai_bookkeeping_logs.id", ondelete="SET NULL"),
        comment="指向原日志 ID（追问续写 / 修改 / 撤销）",
    )

    def __repr__(self) -> str:
        return f"<AiBookkeepingLog(id={self.id}, action='{self.action}', status={self.status})>"
