"""分类模型 — 对应 categories 表

口径（见 `sql/init_mysql.sql` / 02 §2.3）：
- `user_id` 为 NULL 表示**系统预设分类**（所有用户可见、不可被用户删除）；
  旧 Java 库用 0 表示，但 0 不是 users 里存在的 id，建了外键就插不进去，因此改用 NULL。
- `type` 语义为 **0=支出 / 1=收入**（与 records.type 同一套）。
  这是**前端硬约束**：Web 端 `categories.filter(c => c.type === 0)` 取支出分类，
  `categoryType === 0 ? '-' : '+'` 判正负号；uni-app 同样按 0/1 过滤。改成 1/2 会让
  支出分类全被过滤掉、收支颜色与正负号全部反向。详见 02 §0。
"""

from sqlalchemy import BigInteger, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, IdMixin, TimestampMixin


class Category(Base, IdMixin, TimestampMixin):
    """收支分类表"""
    __tablename__ = "categories"

    __table_args__ = (
        Index("idx_categories_user_type", "user_id", "type"),
    )

    user_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        comment="归属用户 ID；NULL 表示系统预设分类",
    )
    name: Mapped[str] = mapped_column(String(50), nullable=False, comment="分类名称")
    type: Mapped[int] = mapped_column(Integer, nullable=False, comment="类型: 0支出 1收入")
    icon: Mapped[str | None] = mapped_column(String(50), comment="图标")
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="排序")
    status: Mapped[int] = mapped_column(Integer, default=1, nullable=False, comment="状态: 0禁用 1启用")

    def __repr__(self) -> str:
        return f"<Category(id={self.id}, name='{self.name}', type={self.type})>"
