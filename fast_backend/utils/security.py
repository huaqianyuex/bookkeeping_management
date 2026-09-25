"""安全工具 — bcrypt 密码哈希 + JWT 令牌

对齐参考项目 utils/security.py（仅 bcrypt），并按既定决策保留 JWT。
bcrypt 使用 $2a$ 前缀，兼容旧 Spring BCryptPasswordEncoder 数据。
"""

from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from config.settings import JWT_EXPIRE_SECONDS, JWT_SECRET

ALGORITHM = "HS256"


def hash_password(plain: str) -> str:
    """bcrypt 哈希，$2a$ 前缀兼容旧数据"""
    salt = bcrypt.gensalt(rounds=10, prefix=b"2a")
    return bcrypt.hashpw(plain.encode(), salt).decode()


def verify_password(plain: str, hashed: str) -> bool:
    """校验密码"""
    try:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except ValueError:
        return False


def create_access_token(subject, expires_delta: timedelta | None = None) -> str:
    """签发 JWT，subject 写入 sub"""
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(seconds=JWT_EXPIRE_SECONDS)
    )
    payload = {"sub": str(subject), "exp": expire}
    return jwt.encode(payload, JWT_SECRET, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict:
    """解码并校验 JWT，失败抛异常"""
    return jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])


def escape_like(keyword: str) -> str:
    r"""转义 LIKE/ILIKE 中的元字符：\% 、\_ 以及 \ 自身。

    使用方式：`Model.col.like(f"%{escape_like(kw)}%", escape="\\")`。
    不转义时，用户输入 `%` 会命中全部行、`_` 会命中任意单字符，
    导致过滤失效或与预期不符。
    """
    if not keyword:
        return ""
    return (
        keyword.replace("\\", "\\\\")
        .replace("%", "\\%")
        .replace("_", "\\_")
    )
