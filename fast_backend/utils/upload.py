"""头像上传校验与落盘 — 对齐 docs/fastapi-backend/03-通用组件.md §5

校验规则（与旧 Java `UserServicesImpl.validateAvatar` 一致，错误统一 HTTP 400）：
- 文件缺失 / 字段名不是 file -> 请上传头像文件
- Content-Type 或扩展名非 JPG/PNG -> 头像仅支持JPG/PNG格式
- 大小超过 MAX_AVATAR_SIZE（默认 2MB）-> 头像大小不能超过2MB
"""

import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile
from starlette import status

from config.settings import AVATAR_DIR, AVATAR_URL_PREFIX, MAX_AVATAR_SIZE

_ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png"}
_ALLOWED_EXTS = {".jpg", ".jpeg", ".png"}


def validate_avatar(file: UploadFile) -> None:
    """校验上传文件类型与扩展名（大小需读到内容后判断，见 save_avatar）"""
    if file is None or not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="请上传头像文件")

    ctype = (file.content_type or "").lower()
    if ctype not in _ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="头像仅支持JPG/PNG格式")

    name = (file.filename or "").lower()
    if not any(name.endswith(ext) for ext in _ALLOWED_EXTS):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="头像仅支持JPG/PNG格式")


async def save_avatar(file: UploadFile) -> str:
    """校验 + 落盘到 AVATAR_DIR，返回入库用的相对 URL（如 /uploads/avatars/xxx.png）"""
    validate_avatar(file)

    data = await file.read()
    if len(data) > MAX_AVATAR_SIZE:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="头像大小不能超过2MB")

    ext = Path(file.filename or "").lower().suffix
    if ext not in _ALLOWED_EXTS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="头像仅支持JPG/PNG格式")

    # 文件名用 uuid 防冲突（对齐 Java UUID.randomUUID() 去横线）
    filename = uuid.uuid4().hex + ext
    root = Path(AVATAR_DIR).resolve()
    root.mkdir(parents=True, exist_ok=True)
    target = (root / filename).resolve()
    if not target.is_relative_to(root):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="非法文件路径")

    # 2MB 内小文件同步写可接受
    target.write_bytes(data)
    return f"{AVATAR_URL_PREFIX}{filename}"


def delete_old_avatar(avatar_url: str | None) -> None:
    """删除旧头像物理文件 — 仅当 URL 以 AVATAR_URL_PREFIX 开头才删，防止误删外部 URL"""
    if not avatar_url or not avatar_url.startswith(AVATAR_URL_PREFIX):
        return
    filename = avatar_url[len(AVATAR_URL_PREFIX):]
    # 去掉路径分隔符，防止拼接出目录穿越
    if not filename or "/" in filename or "\\" in filename or ".." in filename:
        return
    path = (Path(AVATAR_DIR) / filename).resolve()
    if path.is_relative_to(Path(AVATAR_DIR).resolve()) and path.is_file():
        path.unlink()
