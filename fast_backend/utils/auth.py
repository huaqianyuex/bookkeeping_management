"""认证依赖 — 复刻参考项目 utils/auth.py 的 DI 结构

get_current_user / get_optional_current_user：读 Authorization 头 + Depends(get_db)，
失败抛 401。按既定决策保留 JWT 校验、不建 user_token 表，返回 user_id。
"""

from fastapi import Header, HTTPException
from fastapi.params import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from config.db_config import get_db
from crud.user import get_user_by_id
from utils.security import decode_access_token


async def get_current_user(
    authorization: str = Header(..., alias="Authorization"),
    db: AsyncSession = Depends(get_db),
) -> int:
    """解析 Bearer JWT，回查 users 表，返回 user_id；无效/已删除/已禁用抛 401"""
    token = authorization.replace("Bearer ", "")
    try:
        payload = decode_access_token(token)
    except Exception:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "无效令牌")
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "无效令牌")
    user = await get_user_by_id(db, int(user_id))
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "用户不存在")
    # 禁用必须即时生效：这里用 401 而非 403，两端拦截器只对 401 清 token 并
    # 跳登录页；具体原因由下一次登录时的 403「账号已被禁用」呈现
    if user.status != 1:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "账号已被禁用")
    return user.id


async def get_optional_current_user(
    authorization: str = Header(None, alias="Authorization"),
    db: AsyncSession = Depends(get_db),
) -> int | None:
    """可选认证：无头、无效、已删除或已禁用返回 None（不抛异常）"""
    if not authorization:
        return None
    token = authorization.replace("Bearer ", "")
    try:
        payload = decode_access_token(token)
    except Exception:
        return None
    user_id = payload.get("sub")
    if not user_id:
        return None
    user = await get_user_by_id(db, int(user_id))
    if user is None or user.status != 1:
        return None
    return user.id


async def get_current_admin(
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> int:
    """管理员依赖：登录校验（get_current_user）之上再查 users.role，非管理员抛 403

    ⚠️ `role` 是 **TINYINT 0/1**（0=普通用户，1=管理员），不是字符串。
    前端 `AdminRoute.jsx` 用 `user.role !== 1` 拦管理后台、`AdminUsers.jsx` 用
    `record.role === 1` 渲染标签，定稿口径见 `docs/fastapi-backend/02-数据库设计.md` §0。
    """
    user = await get_user_by_id(db, user_id)
    if user is None:
        # token 有效但用户已被删除（10-实现骨架.md 依赖清单：用户不存在 → 401）
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "用户不存在")
    if user.role != 1:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "无管理员权限")
    return user_id
