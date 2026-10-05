"""统一响应封装 — {code, message, data} 信封

对齐参考项目 toutiao_backend 的 utils/response.py。
"""

from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse


def success_response(message: str = "success", data=None):
    """成功响应：固定 code=200，data 可为 ORM/Pydantic 对象"""
    content = {"code": 200, "message": message, "data": data}
    return JSONResponse(content=jsonable_encoder(content))
