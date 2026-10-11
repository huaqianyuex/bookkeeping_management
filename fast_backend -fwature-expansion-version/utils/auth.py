"""认证依赖 — 复刻参考项目 utils/auth.py 的 DI 结构

get_current_user / get_optional_current_user：读 Authorization 头 + Depends(get_db)，
失败抛 401。按既定决策保留 JWT 校验、不建 user_token 表，返回 user_id。

════════════════════════════════════════════════════════════════════════
角色与功能范围矩阵（本项目权限边界的唯一说明，改权限前先读这里）
════════════════════════════════════════════════════════════════════════

users.role 为 TINYINT：**0=普通用户，1=管理员**（见 docs/fastapi-backend/02-数据库设计.md §0）。

| 功能域 | 端点前缀 | 普通用户 role=0 | 管理员 role=1 |
|---|---|---|---|
| 记账（账单/分类/统计） | `/api/records` `/api/categories` `/api/statistics` | ✅ 可用 | ❌ 403 |
| AI 对话与分析 | `/api/ai/**`（除下方两处） | ✅ 可用 | ❌ 403 |
| AI 管理统计 / FAQ 重建 | `/api/ai/admin/stats` `/api/ai/faq/rebuild` | ❌ 403 | ✅ 可用 |
| 会员 / 充值 | `/api/membership/**` `/api/recharge/**` | ✅ 可用 | ✅ 可用 |
| 个人资料 / 改密 | `/api/user/**` | ✅ 可用 | ✅ 可用 |
| 管理后台 | `/api/admin/**` | ❌ 403 | ✅ 可用 |

设计口径：**管理员的职责在管理后台，不需要也不应产生个人记账与对话数据**。
因此用户侧业务端点（记账 + 对话）统一挂 `get_current_regular_user`，
管理员调用一律 403；而个人资料、会员、充值等「账号自身」功能对两种角色都开放。

三个角色依赖的分工：
- `get_current_user`         —— 只校验登录态，任何角色都通过（账号自身功能用它）；
- `get_current_regular_user` —— 登录态 + 拒绝管理员（用户侧业务端点用它）；
- `get_current_admin`        —— 登录态 + 必须是管理员（管理后台用它）。
"""

from fastapi import Header, HTTPException
from fastapi.params import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from config.db_config import get_db
from crud.user import get_user_by_id
from utils.security import decode_access_token


def _extract_bearer_token(authorization: str | None) -> str | None:
    """严格解析 `Bearer <token>`；缺失或前缀不符返回 None，不接受裸 token"""
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization.removeprefix("Bearer ").strip()
    return token or None


def _parse_sub(payload: dict) -> int | None:
    """取 JWT sub 并转 int；非数字返回 None（按无效令牌处理，而非 500）"""
    raw = payload.get("sub")
    if not raw:
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


async def get_current_user(
    authorization: str | None = Header(None, alias="Authorization"),
    db: AsyncSession = Depends(get_db),
) -> int:
    """解析 Bearer JWT，回查 users 表，返回 user_id；无效/已删除/已禁用抛 401

    缺 Authorization 头必须返回 401 而非 422：前端拦截器只对 401 清 token 跳登录。
    """
    token = _extract_bearer_token(authorization)
    if token is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "未提供认证令牌")
    try:
        payload = decode_access_token(token)
    except Exception:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "无效令牌")
    user_id = _parse_sub(payload)
    if user_id is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "无效令牌")
    user = await get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "用户不存在")
    # 禁用必须即时生效：这里用 401 而非 403，两端拦截器只对 401 清 token 并
    # 跳登录页；具体原因由下一次登录时的 403「账号已被禁用」呈现
    if user.status != 1:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "账号已被禁用")
    return user.id


async def get_current_regular_user(
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> int:
    """普通用户依赖：登录态之上再查 users.role，**管理员账号调用一律 403**。

    用途：用户侧业务端点（记账 / 分类 / 统计 / AI 对话与分析）的统一鉴权。
    管理员的职责在 `/api/admin/**` 管理后台，不需要记账与对话功能，
    也不应在业务表里产生个人数据；在此显式拒绝，而不是靠前端隐藏入口
    （前端隐藏只是体验优化，权限边界必须在服务端成立）。

    与 get_current_admin 的关系是**互补且互斥**的：
    - role == 1 走管理后台  → get_current_admin 放行、本依赖拒绝；
    - role == 0 走用户业务  → 本依赖放行、get_current_admin 拒绝。

    功能范围矩阵见模块 docstring。
    """
    user = await get_user_by_id(db, user_id)
    if user is None:
        # token 有效但用户已被删除（与 get_current_admin 同口径）
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "用户不存在")
    if user.role == 1:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "管理员账号无需使用该功能，请前往管理后台"
        )
    return user_id


async def get_optional_current_user(
    authorization: str = Header(None, alias="Authorization"),
    db: AsyncSession = Depends(get_db),
) -> int | None:
    """可选认证：无头、无效、已删除或已禁用返回 None（不抛异常）"""
    token = _extract_bearer_token(authorization)
    if token is None:
        return None
    try:
        payload = decode_access_token(token)
    except Exception:
        return None
    user_id = _parse_sub(payload)
    if user_id is None:
        return None
    user = await get_user_by_id(db, user_id)
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
