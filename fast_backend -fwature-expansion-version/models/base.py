"""SQLAlchemy 声明式基类 + 公共 mixin

所有 ORM 模型继承 Base + IdMixin + TimestampMixin 即可获得 id、created_at、updated_at。
统一 Base 优于参考项目每个文件各自声明 Base 的做法。
"""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """声明式基类"""
    pass


class IdMixin:
    """自增主键 mixin"""
    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
        comment="主键 ID",
    )


class TimestampMixin:
    """时间戳 mixin — 自动填充 created_at / updated_at"""
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        comment="创建时间",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        comment="更新时间",
    )
