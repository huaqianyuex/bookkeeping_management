"""全局异常处理器 — 统一 {code, message, data} 信封 + 真实 HTTP 状态码

对齐参考项目 toutiao_backend 的 utils/exception.py：handler 函数、DEBUG_MODE、
子类在前父类在后的注册顺序。新增 RequestValidationError handler 让参数校验
错误也走统一信封。
"""

import traceback

from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from starlette import status

from config.settings import DEBUG_MODE


async def http_exception_handler(request: Request, exc: HTTPException):
    """业务异常：透传状态码"""
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": exc.status_code, "message": exc.detail, "data": None},
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """参数校验异常：拼接错误信息"""
    errors = "; ".join(
        f"{'.'.join(map(str, e['loc']))}: {e['msg']}" for e in exc.errors()
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"code": 422, "message": errors, "data": None},
    )


async def integrity_error_handler(request: Request, exc: IntegrityError):
    """数据完整性约束冲突"""
    error_msg = str(exc.orig)
    if "Duplicate entry" in error_msg or "username" in error_msg:
        detail = "数据已存在，请检查唯一约束"
    elif "FOREIGN KEY" in error_msg:
        detail = "关联数据不存在"
    else:
        detail = "数据约束冲突，请检查输入"
    error_data = None
    if DEBUG_MODE:
        error_data = {
            "error_type": "IntegrityError",
            "error_detail": error_msg,
            "path": str(request.url),
        }
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"code": 400, "message": detail, "data": error_data},
    )


async def sqlalchemy_error_handler(request: Request, exc: SQLAlchemyError):
    """数据库操作异常"""
    error_data = None
    if DEBUG_MODE:
        error_data = {
            "error_type": type(exc).__name__,
            "error_detail": str(exc),
            "traceback": traceback.format_exc(),
            "path": str(request.url),
        }
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"code": 500, "message": "数据库操作失败，请稍后重试", "data": error_data},
    )


async def general_exception_handler(request: Request, exc: Exception):
    """兜底异常"""
    error_data = None
    if DEBUG_MODE:
        error_data = {
            "error_type": type(exc).__name__,
            "error_detail": str(exc),
            "traceback": traceback.format_exc(),
            "path": str(request.url),
        }
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"code": 500, "message": "服务器内部错误", "data": error_data},
    )
