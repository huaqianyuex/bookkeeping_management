"""充值模块模型 — 对应 recharge_orders / recharge_audit_logs 表

设计规格：docs/fastapi-backend/11-充值与审批模块.md；DDL 同步见 sql/init_mysql.sql 表 13/14。
约定延续项目风格：整数标志位、IdMixin/TimestampMixin、显式 Index；
金额用 DECIMAL(10,2) ↔ Python Decimal（全链路禁 float）；时间用 DATETIME、比较交给 DB NOW()。
状态机与防绕过链路见 crud/recharge.py 模块注释。
"""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger, DateTime, DECIMAL, ForeignKey, Index, Integer, SmallInteger, String, func,
)
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, IdMixin, TimestampMixin


class RechargeOrder(Base, IdMixin, TimestampMixin):
    """充值订单表 — 套餐直购模式下「钱 → 会员天数」的唯一凭证

    plan_name/days/amount 是下单时刻的快照：套餐目录（settings.RECHARGE_PLANS）后续
    调价不影响历史订单的金额与权益，对账以快照为准。
    """

    __tablename__ = "recharge_orders"

    order_no: Mapped[str] = mapped_column(
        String(32), nullable=False, unique=True,
        comment="业务订单号（RCH 前缀）；对外标识，支付回调/查询/审计都靠它",
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        comment="下单用户 ID",
    )
    plan_id: Mapped[str] = mapped_column(
        String(32), nullable=False, comment="套餐 ID（RECHARGE_PLANS 目录键快照）"
    )
    plan_name: Mapped[str] = mapped_column(
        String(64), nullable=False, comment="套餐名称快照"
    )
    days: Mapped[int] = mapped_column(Integer, nullable=False, comment="会员天数快照")
    amount: Mapped[Decimal] = mapped_column(
        DECIMAL(10, 2), nullable=False, comment="应收金额快照（元）；服务端定价，回调时核对"
    )
    status: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, default=0,
        comment="0=待支付 1=待审批 2=已支付 3=已拒绝 4=已取消 5=超时关闭",
    )
    pay_method: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, default=0,
        comment="支付方式：0=模拟支付（真实渠道需资质，本期预留抽象层）",
    )
    risk_flags: Mapped[str | None] = mapped_column(
        String(255), comment="支付时命中的风控规则（逗号分隔）；无命中为 NULL"
    )
    client_ip: Mapped[str | None] = mapped_column(
        String(45), comment="下单 IP（IPv6 最长 45）"
    )
    paid_at: Mapped[datetime | None] = mapped_column(
        DateTime, comment="支付成功时间（含待审批订单——钱已收，等放行）"
    )
    reviewed_by: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"),
        comment="审批管理员 ID；仅待审批订单的通过/拒绝会写入",
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, comment="审批时间")
    review_note: Mapped[str | None] = mapped_column(
        String(255), comment="审批备注（通过备注/拒绝原因，拒绝时必填）"
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime, comment="待支付有效期；超时由读/支付路径懒关闭（无定时任务）"
    )

    def __repr__(self) -> str:
        return f"<RechargeOrder(order_no={self.order_no}, status={self.status})>"


class RechargeAuditLog(Base, IdMixin):
    """充值审计日志 — append-only：任何状态流转一行，与流转同一事务写入

    无更新/删除端点、无 ondelete 之外的写路径；管理员删除用户后 actor_id 置 NULL
    （SET NULL），日志本身永不删除——这是「操作日志留痕」的最后防线。
    """

    __tablename__ = "recharge_audit_logs"

    order_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("recharge_orders.id", ondelete="CASCADE"),
        nullable=False,
        comment="订单 ID",
    )
    order_no: Mapped[str] = mapped_column(
        String(32), nullable=False, comment="订单号冗余（免 JOIN 即可读，也防订单被级联删后断链）"
    )
    actor_type: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, comment="操作方：0=用户 1=系统（风控/超时/回调） 2=管理员"
    )
    actor_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"),
        comment="操作人 ID；系统动作为 NULL",
    )
    action: Mapped[str] = mapped_column(
        String(32), nullable=False,
        comment="动作：CREATE/PAY_SUCCESS/PAY_FAIL/RISK_HOLD/APPROVE/REJECT/CANCEL/EXPIRE_CLOSE/EXTEND_MEMBERSHIP",
    )
    from_status: Mapped[int | None] = mapped_column(
        SmallInteger, comment="流转前状态；CREATE 时为 NULL"
    )
    to_status: Mapped[int] = mapped_column(SmallInteger, nullable=False, comment="流转后状态")
    detail: Mapped[str | None] = mapped_column(
        String(500), comment="详情：命中风控规则/支付失败原因/审批备注等"
    )
    ip: Mapped[str | None] = mapped_column(String(45), comment="操作 IP")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), comment="发生时间"
    )

    __table_args__ = (
        Index("idx_recharge_audit_order", "order_id", "id"),
        Index("idx_recharge_audit_created", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<RechargeAuditLog(order_no={self.order_no}, action={self.action})>"
