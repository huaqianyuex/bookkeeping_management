"""用户模块路由 — /api/user"""
from datetime import datetime

from starlette import status

from crud import user
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from fastapi.params import Depends
from sqlalchemy.ext.asyncio import AsyncSession


from config.db_config import get_db
from schemas.users import (
    LoginRequest,
    PasswordChangeRequest,
    RegisterRequest,
    UserOut,
    UserUpdateRequest,
)
from utils import security
from utils.auth import get_current_user
from utils.response import success_response
from utils.upload import save_avatar, delete_old_avatar

router = APIRouter(prefix="/api/user", tags=["user"])


@router.post("/register")
async def register(data: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """用户注册"""
    # 逻辑：验证用户是否存在 -> 创建用户 -> 签发 JWT -> 响应结果
    existing = await user.get_user_by_username(db, data.username)
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="用户名已存在")

    # 创建用户（注册不签发令牌、不返回用户对象；前端注册成功后跳转登录页）
    await user.create_user(db, data)
    return success_response(message="注册成功，请登录")


@router.post("/login")
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    """用户登录"""
    # 查用户；不存在与密码错误统一文案，避免泄露用户是否存在
    user_obj = await user.get_user_by_username(db, data.username)
    if not user_obj or not security.verify_password(data.password, user_obj.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )
    # 禁用账号
    if user_obj.status != 1:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="账号已被禁用",
        )
    # 签发 JWT（无状态、不落库）
    token = await user.create_token(db, user_obj.id)
    # 记录最后登录时间
    user_obj.last_login_at = datetime.now()
    await db.commit()
    # 出参 data = {"token": ...}（见 API 文档 §2；用户信息由 GET /info 获取）
    return success_response(message="登录成功", data={"token": token})


@router.get("/info")
async def get_user_info(
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取当前用户信息"""
    user_info = await user.get_user_by_id(db, user_id)
    if not user_info:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    # UserOut 字段与 users 表对齐（含 role，前端靠 user.role === 1 判管理员）
    return success_response(message="获取成功", data=UserOut.model_validate(user_info))


# ⚠️ 路径必须是 /info：Web 端 api/user.js 里是
#    `request.put('/user/info', data)`，04 §1.4 与 10 §1.4 同样是 PUT /api/user/info。
#    原来写成 /update 会让「更新资料」直接 404。


@router.put("/info")
async def update_user(
    data: UserUpdateRequest,
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """更新当前用户信息（用户名/昵称/邮箱/手机号，按 JWT 中的用户 ID 更新）"""
    user_info = await user.update_user(db, user_id, data)
    return success_response(message="更新用户信息成功", data=UserOut.model_validate(user_info))


@router.put("/password")
async def change_password(
    data: PasswordChangeRequest,
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """修改密码"""
    await user.update_password(db, user_id, data)
    return success_response(message="密码修改成功")


@router.post("/avatar")
async def upload_avatar(
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    file: UploadFile = File(...),
):
    """上传/更换头像：校验 -> 落盘 -> 更新 users.avatar -> 删除旧物理文件"""
    if file is None or not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="请上传头像文件")

    # 1) 校验 + 落盘（类型/大小/扩展名），返回相对 URL
    avatar_url = await save_avatar(file)

    # 2) 读出旧头像 URL（删物理文件前需比对，防误删外部 URL）
    existing = await user.get_user_by_id(db, user_id)
    old_avatar = existing.avatar if existing else None

    # 3) 更新 users.avatar
    user_info = await user.update_avatar_url(db, user_id, avatar_url)

    # 4) 旧头像仅当落在本服务目录内才删物理文件
    if old_avatar and old_avatar != avatar_url:
        delete_old_avatar(old_avatar)

    return success_response(message="头像上传成功", data=UserOut.model_validate(user_info))
