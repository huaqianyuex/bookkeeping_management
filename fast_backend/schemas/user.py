"""用户相关 Pydantic 模型"""

import re
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from schemas.base import OrmBase

# 与前端表单约束一致：用户名 2-20 位中英文或数字；密码 6 位数字
USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9\u4e00-\u9fa5]{2,20}$")
PASSWORD_PATTERN = re.compile(r"^\d{6}$")


def normalize_username(v: str) -> str:
    """用户名规范化：去除首尾空白（前端输入常见空格；统一 DB 存储与查询口径）"""
    return v.strip()


class RegisterRequest(BaseModel):
    """注册请求"""
    username: str = Field(min_length=2, max_length=20)
    password: str = Field(min_length=6, max_length=6)
    nickname: Optional[str] = Field(None, max_length=50, description="昵称")

    @field_validator("username")
    @classmethod
    def _check_username(cls, v: str) -> str:
        v = normalize_username(v)
        if not USERNAME_PATTERN.match(v):
            raise ValueError("用户名需为2-20位中英文或数字组合")
        return v

    @field_validator("password")
    @classmethod
    def _check_password(cls, v: str) -> str:
        v = v.strip()
        if not PASSWORD_PATTERN.match(v):
            raise ValueError("密码需为6位数字")
        return v


class LoginRequest(BaseModel):
    """登录请求"""
    username: str = Field(min_length=1, max_length=100, description="用户名（限长防恶意超长输入）")
    password: str = Field(min_length=1, max_length=100, description="密码")

    @field_validator("username")
    @classmethod
    def _check_username(cls, v: str) -> str:
        # 只规范化、不校验格式：格式合法与否由「用户不存在」统一 401 兜住，避免探测用户名
        return normalize_username(v)

    @field_validator("password")
    @classmethod
    def _check_password(cls, v: str) -> str:
        return v.strip()


class UserUpdateRequest(BaseModel):
    """更新用户信息请求"""
    username: Optional[str] = Field(None, max_length=20, description="用户名")
    nickname: Optional[str] = Field(None, max_length=50, description="昵称")
    email: Optional[str] = Field(None, max_length=100, description="邮箱")
    phone: Optional[str] = Field(None, max_length=20, description="手机号")

    @field_validator("username")
    @classmethod
    def _check_username(cls, v: Optional[str]) -> Optional[str]:
        # 与注册同口径：先规范化再校验 pattern，保证落库值一致
        if v is None:
            return v
        v = normalize_username(v)
        if not USERNAME_PATTERN.match(v):
            raise ValueError("用户名需为2-20位中英文或数字组合")
        return v


class PasswordChangeRequest(BaseModel):
    """修改密码请求"""
    old_password: str = Field(..., alias="oldPassword", description="旧密码")
    new_password: str = Field(..., min_length=6, max_length=6, alias="newPassword", description="新密码，需为 6 位数字（与注册同口径）")

    model_config = ConfigDict(populate_by_name=True)

    @field_validator("new_password")
    @classmethod
    def _check_new_password(cls, v: str) -> str:
        if not PASSWORD_PATTERN.match(v):
            raise ValueError("新密码需为6位数字")
        return v


class UserOut(OrmBase):
    """用户信息输出（字段与 users 表对齐，供 GET /info 与 admin 用户列表使用）"""
    id: int
    username: str
    nickname: Optional[str] = None
    avatar: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    role: int = Field(0, description="角色：0=普通用户，1=管理员")
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
