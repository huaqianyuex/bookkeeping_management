"""AI 对话相关模型 — 对应 sessions / messages / feedback / faq 表

口径（见 `sql/init_mysql.sql` / 02 §3）：
- 表名为**单数**（随旧 Express/sql.js 与 05 接口文档），不是 chat_sessions 等复数形式；
- 主键是**业务字符串 ID**（`session_{ms}_{rand}` / `msg_...` / `feedback_...`），不是自增；
- 时间列是 **BIGINT 毫秒时间戳**（前端 `Date.now()` 直接比对），**不是 DATETIME**；
- `deleted_at = 0` 表示未删除，`> 0` 存删除时的毫秒值（软删）。

因此这四张表**不使用** IdMixin / TimestampMixin，显式声明每一列。
"""

from sqlalchemy import BigInteger, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base


class ChatSession(Base):
    """AI 对话会话表（软删）"""
    __tablename__ = "sessions"

    __table_args__ = (
        Index("idx_sessions_user", "user_id", "deleted_at", "updated_at"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True, comment="会话ID，session_{毫秒}_{随机}")
    user_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        comment="归属用户；NULL=历史遗留无主数据",
    )
    title: Mapped[str] = mapped_column(String(50), nullable=False, default="新对话", comment="会话标题")
    auto_title: Mapped[int] = mapped_column(Integer, nullable=False, default=1,
                                            comment="1=AI可覆盖标题 0=用户已重命名锁定")
    created_at: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="创建时间（毫秒）")
    updated_at: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="更新时间（毫秒）")
    deleted_at: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0,
                                            comment="0未删；>0=软删毫秒")

    def __repr__(self) -> str:
        return f"<ChatSession(id={self.id}, user_id={self.user_id})>"


class ChatMessage(Base):
    """AI 对话消息表"""
    __tablename__ = "messages"

    __table_args__ = (
        Index("idx_messages_session_ts", "session_id", "timestamp"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True, comment="消息ID，msg_{毫秒}_{随机}")
    session_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
        comment="会话 ID",
    )
    role: Mapped[str] = mapped_column(String(16), nullable=False, comment="角色: user/assistant")
    content: Mapped[str] = mapped_column(Text, nullable=False, comment="消息内容")
    timestamp: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="毫秒时间戳")

    def __repr__(self) -> str:
        return f"<ChatMessage(id={self.id}, role='{self.role}')>"


class Feedback(Base):
    """AI 回复反馈表

    user_id 已补（反馈人，关联 users.id），支持按用户维度隔离/统计反馈。
    """
    __tablename__ = "feedback"

    __table_args__ = (
        Index("idx_feedback_message", "message_id"),
        Index("idx_feedback_user", "user_id"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True, comment="反馈ID，feedback_{毫秒}_{随机}")
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        comment="反馈人 ID",
    )
    message_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("messages.id", ondelete="CASCADE"),
        nullable=False,
        comment="关联消息 ID",
    )
    rating: Mapped[int] = mapped_column(Integer, nullable=False, comment="评分 1~5")
    comment: Mapped[str | None] = mapped_column(Text, comment="反馈内容")
    timestamp: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="毫秒时间戳")

    def __repr__(self) -> str:
        return f"<Feedback(id={self.id}, rating={self.rating})>"


class Faq(Base):
    """FAQ 知识库表

    默认不建 embedding 列，向量在服务启动时内存构建（02 §3.4）。
    若需持久化向量，在此处补 `embedding: Mapped[str | None] = mapped_column(Text)` 并同步建表语句。
    """
    __tablename__ = "faq"

    __table_args__ = (
        Index("idx_faq_category", "category"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="主键")
    question: Mapped[str] = mapped_column(Text, nullable=False, comment="问题")
    answer: Mapped[str] = mapped_column(Text, nullable=False, comment="回答")
    category: Mapped[str] = mapped_column(String(50), nullable=False, comment="分类标签")

    def __repr__(self) -> str:
        return f"<Faq(id={self.id}, category='{self.category}')>"
