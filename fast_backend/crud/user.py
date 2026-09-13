"""用户数据访问层 — 模板桩，业务逻辑由你后续实现"""

from fastapi import HTTPException
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from models.user import User, UserToken
from schemas.users import PasswordChangeRequest, RegisterRequest, UserUpdateRequest
from utils import security


async def get_user_by_id(db: AsyncSession, user_id: int):
    """根据 ID 查询用户"""
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def get_user_by_username(db: AsyncSession, username: str):
    """根据用户名查询用户"""
    result = await db.execute(select(User).where(User.username == username))
    return result.scalar_one_or_none()


async def create_user(db: AsyncSession, data: RegisterRequest) -> User:
    """新增用户

    修正点（原实现有三处会直接报错/丢数据）：
    1. `User(user.username, hash)` 这种位置参数写法在 SQLAlchemy 2.0 声明式模型上不成立，
       会抛 TypeError —— 必须全部用关键字参数；
    2. 原实现少了 `db.add(user)`，commit 时没有任何待写入对象，用户根本存不进库；
    3. `security.get_password_hash` 不存在，`utils/security.py` 里叫 `hash_password`。
    """
    user = User(
        username=data.username,
        password=security.hash_password(data.password),
        nickname=data.nickname,
        role=0,      # 0=普通用户，1=管理员（前端按 role === 1 判管理员，见 02 §0）
        status=1,
    )
    db.add(user)
    await db.commit()
    # 回读主键与 DB 侧默认值（created_at / updated_at 由 DDL 填充）
    await db.refresh(user)
    return user


async def update_user(db: AsyncSession, user_id: int, user_data: UserUpdateRequest):
    """更新用户信息（按用户 ID 更新，不依赖用户名）"""
    existing = await get_user_by_id(db, user_id)
    if not existing:
        raise HTTPException(status_code=404, detail="用户不存在")

    values = user_data.model_dump(exclude_unset=True, exclude_none=True)
    if not values:
        raise HTTPException(status_code=400, detail="没有需要更新的内容")

    stmt = update(User).where(User.id == user_id).values(**values)
    await db.execute(stmt)
    await db.commit()
    # 回读更新后的用户
    updated_user = await get_user_by_id(db, user_id)
    return updated_user


async def update_avatar_url(db: AsyncSession, user_id: int, avatar_url: str) -> User:
    """更新头像 URL：写库前先读出旧 avatar，供路由层删旧物理文件"""
    existing = await get_user_by_id(db, user_id)
    if not existing:
        raise HTTPException(status_code=404, detail="用户不存在")

    stmt = update(User).where(User.id == user_id).values(avatar=avatar_url)
    await db.execute(stmt)
    await db.commit()
    return await get_user_by_id(db, user_id)


async def create_token(db: AsyncSession, user_id: int) -> str:
    """签发访问令牌（**无状态 JWT**，`sub` = userId，不落库）。

    项目采用无状态 JWT 鉴权：`utils/auth.py::get_current_user` 只做 JWT 解码、
    不查库（见计划文档 §七「对参考项目的有意偏离」与 API 文档决策 D8
    「统一『无效令牌』，不查库」）。因此签发端只负责用 `JWT_SECRET` 签发
    HS256 JWT，不在 `user_token` 表留痕。

    `user_token` 表保留为后续「令牌吊销 / 多端管理」的扩展位，当前未启用；
    启用时需同步改造 `get_current_user` 增加查库校验。
    """
    return security.create_access_token(user_id)



# 更新密码
async def update_password(db: AsyncSession, user_id: int, user_data: PasswordChangeRequest):
    """修改密码：校验旧密码 -> bcrypt 哈希新密码 -> 按用户 ID 更新"""
    existing = await get_user_by_id(db, user_id)
    if not existing:
        raise HTTPException(status_code=404, detail="用户不存在")

    # 旧密码校验：与登录一致，错误文案不区分「用户不存在/密码错误」以外的信息泄露
    if not security.verify_password(user_data.old_password, existing.password):
        raise HTTPException(status_code=400, detail="旧密码错误")

    stmt = (
        update(User)
        .where(User.id == user_id)
        .values(password=security.hash_password(user_data.new_password))
    )
    await db.execute(stmt)
    await db.commit()