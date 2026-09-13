"""用户模型 — 对应 users / user_token 表

字段与索引口径以 `sql/init_mysql.sql` 与 `docs/fastapi-backend/02-数据库设计.md` §2 为准。
主键统一由 IdMixin 提供（BIGINT），**子类不要重复声明 id**，否则外键两侧类型会不一致，
MySQL 建表时会报 errno 3780。
"""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, IdMixin, TimestampMixin


class User(Base, IdMixin, TimestampMixin):
    """用户表"""
    __tablename__ = "users"

    __table_args__ = (
        Index("idx_users_status", "status"),
    )

    username: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, comment="用户名，登录账号")
    password: Mapped[str] = mapped_column(String(100), nullable=False, comment="密码哈希（BCrypt）")
    nickname: Mapped[str | None] = mapped_column(String(50), comment="昵称")
    avatar: Mapped[str | None] = mapped_column(String(200), comment="头像相对路径")
    email: Mapped[str | None] = mapped_column(String(100), comment="邮箱")
    phone: Mapped[str | None] = mapped_column(String(20), unique=True, comment="手机号")
    role: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="角色: 0普通用户 1管理员")
    status: Mapped[int] = mapped_column(Integer, default=1, nullable=False, comment="状态: 0禁用 1启用")
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime, comment="最后登录时间")

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username='{self.username}')>"


class UserToken(Base, IdMixin):
    """用户令牌表 — 支持令牌吊销与多端登录管理"""
    __tablename__ = "user_token"

    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        comment="用户ID",
    )
    token: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, comment="令牌值")
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, comment="过期时间")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False, comment="创建时间"
    )

    def __repr__(self) -> str:
        return f"<UserToken(id={self.id}, user_id={self.user_id})>"
