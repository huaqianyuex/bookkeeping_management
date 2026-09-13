"""记账记录模型 — 对应 records 表

口径（见 `sql/init_mysql.sql` / 02 §2.4）：
- 日期列名为 `date`（旧 Java 库是 `record_date`）；
- `type` 语义为 **0=支出 / 1=收入**，与 categories.type 同一套（前端按此判断，
  见 02 §0；曾误写为 1/2，已改回）；
- `status` 为软删标记（0=已删除，1=正常），AI 记账的「撤销」走软删。

注意：排序字段为 Record.date（旧代码误用 Record.record_time，已修正）。
金额一律用 Decimal，禁止 float（02 §1「禁止 float/double 存钱」）。
"""

from datetime import date
from decimal import Decimal

from sqlalchemy import BigInteger, Date, ForeignKey, Index, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, IdMixin, TimestampMixin


class Record(Base, IdMixin, TimestampMixin):
    """记账记录表"""
    __tablename__ = "records"

    __table_args__ = (
        Index("idx_records_user_date", "user_id", "date"),
        Index("idx_records_category", "category_id"),
        Index("idx_records_user_status_date", "user_id", "status", "date"),
    )

    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        comment="用户 ID",
    )
    category_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("categories.id", ondelete="RESTRICT"),
        nullable=False,
        comment="分类 ID",
    )
    type: Mapped[int] = mapped_column(Integer, nullable=False, comment="类型: 0支出 1收入")
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, comment="金额")
    date: Mapped[date] = mapped_column(Date, nullable=False, comment="记账日期")
    remark: Mapped[str | None] = mapped_column(String(200), comment="备注")
    status: Mapped[int] = mapped_column(Integer, default=1, nullable=False, comment="状态: 0删除 1正常")

    def __repr__(self) -> str:
        return f"<Record(id={self.id}, type={self.type}, amount={self.amount})>"
