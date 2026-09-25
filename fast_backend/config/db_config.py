"""数据库连接配置 — SQLAlchemy 2.0 异步引擎 + 会话依赖

对齐参考项目 toutiao_backend 的 config/db_config.py 风格。
"""

import os

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

# 加载 .env 配置文件
load_dotenv()

# 数据库连接地址（可用 .env 覆盖）
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "mysql+aiomysql://root:***@localhost:3306/bookkeeping_fastapi?charset=utf8mb4",
)

# SQL 回显：默认关闭。开启后 SQLAlchemy 会把每条 SQL 连同参数打进日志，
# Windows GBK 控制台遇到参数里的 emoji（如 📊）会抛 UnicodeEncodeError；
# 需要调试 SQL 时在 .env 设 SQL_ECHO=true，并确保控制台为 UTF-8。
SQL_ECHO = os.getenv("SQL_ECHO", "false").lower() == "true"

# 创建异步数据库连接池
async_engine = create_async_engine(
    DATABASE_URL,
    echo=SQL_ECHO,
    pool_size=5,
    max_overflow=15,
)

# 创建异步会话工厂
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# FastAPI 依赖注入：给路由函数提供数据库会话
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
