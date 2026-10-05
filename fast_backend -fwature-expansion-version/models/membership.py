"""会员模型 — 对应 user_membership / ai_usage_daily / membership_codes 表

字段与索引口径以 sql/init_mysql.sql 与 docs/fastapi-backend/02-数据库设计.md 为准（骨架阶段：
DDL 见 docs/membership-plan.md §2）。
约定延续项目风格：tier/status 整数标志位（0/1）、IdMixin/TimestampMixin、显式 Index；
金额不涉及；时间用 DATETIME（业务表口径，非 AI 表的毫秒 BIGINT）。
"""

from datetime import date, datetime

from sqlalchemy import (
    BigInteger, Date, DateTime, ForeignKey, Index, Integer, SmallInteger, String,
)
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, IdMixin, TimestampMixin


class UserMembership(Base, IdMixin, TimestampMixin):
    """用户会员表 — 每用户一行（uk_membership_user）；免费用户可以没有行"""

    __tablename__ = "user_membership"

    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        comment="用户 ID，1:1 唯一",
    )
    tier: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, default=0, comment="等级：0=免费 1=会员"
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime, comment="会员到期时间；NULL=永久（仅免费档可能出现）"
    )
    source: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, default=0, comment="开通来源：0=兑换码 1=管理员开通"
    )

    def __repr__(self) -> str:
        return f"<UserMembership(user_id={self.user_id}, tier={self.tier})>"


class AiUsageDaily(Base, IdMixin):
    """AI 每日用量表 — (user_id, usage_date) 唯一（uk_usage_user_date），upsert 累加，跨天自然归零"""

    __tablename__ = "ai_usage_daily"

    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        comment="用户 ID",
    )
    usage_date: Mapped[date] = mapped_column(Date, nullable=False, comment="统计日期")
    chat_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="当日 AI 对话次数"
    )
    analyze_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="当日分析次数（消费分析+预算规划）"
    )
    bookkeeping_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="当日智能记账解析次数"
    )

    __table_args__ = (
        Index("uk_usage_user_date", "user_id", "usage_date", unique=True),
    )


class MembershipCode(Base, IdMixin, TimestampMixin):
    """会员兑换码表"""

    __tablename__ = "membership_codes"

    code: Mapped[str] = mapped_column(
        String(16), nullable=False, unique=True,
        comment="兑换码（16 位大写字母数字，去除 0/O/1/I）",
    )
    days: Mapped[int] = mapped_column(Integer, nullable=False, comment="兑换天数")
    status: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, default=0, comment="状态：0=未使用 1=已使用 2=已作废"
    )
    batch_no: Mapped[str | None] = mapped_column(String(32), comment="批次号（默认生成时间戳）")
    used_by: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), comment="核销用户 ID"
    )
    used_at: Mapped[datetime | None] = mapped_column(DateTime, comment="核销时间")

    def __repr__(self) -> str:
        # 刻意不含 code：异常/日志场景打印 repr 不能泄漏兑换码明文
        return f"<MembershipCode(id={self.id}, days={self.days}, status={self.status})>"
