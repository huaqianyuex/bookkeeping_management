"""分类相关 Pydantic 模型"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from schemas.base import OrmBase


class CategoryCreate(BaseModel):
    """创建分类请求"""
    name: str = Field(..., max_length=50, description="分类名称")
    type: int = Field(...,ge=0,le=1, description="类型：0支出 1收入")
    icon: Optional[str] = Field(None, max_length=50, description="图标")
    sort_order: int = Field(0, alias="sortOrder", description="排序")

    model_config = ConfigDict(populate_by_name=True)


class CategoryUpdate(BaseModel):
    """更新分类请求"""
    name: Optional[str] = Field(None, max_length=50, description="分类名称")
    type: Optional[int] = Field(None, description="类型：0支出 1收入")
    icon: Optional[str] = Field(None, max_length=50, description="图标")
    sort_order: Optional[int] = Field(None, alias="sortOrder", description="排序")

    model_config = ConfigDict(populate_by_name=True)


class CategoryOut(OrmBase):
    """分类输出（对齐 10-实现骨架.md §2.1 响应契约）"""
    id: int
    user_id: Optional[int] = Field(None, alias="userId", description="归属用户模块；null=系统预设")
    name: str
    type: int = Field(..., description="0=支出，1=收入")
    icon: Optional[str] = None
    sort_order: int = Field(0, alias="sortOrder")
    created_at: Optional[datetime] = Field(None, alias="createTime")
    updated_at: Optional[datetime] = Field(None, alias="updateTime")
