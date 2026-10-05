"""异常处理器注册 — 对齐参考项目 utils/exception_handlers.py

注册全局异常处理器：子类在前，父类在后；具体在前，抽象在后。
"""

from fastapi import HTTPException
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from utils.exception import (
    general_exception_handler,
    http_exception_handler,
    integrity_error_handler,
    sqlalchemy_error_handler,
    validation_exception_handler,
)


def register_exception_handlers(app):
    """注册全局异常处理器：子类在前，父类在后；具体在前，抽象在后"""
    app.add_exception_handler(RequestValidationError, validation_exception_handler)  # 参数校验
    app.add_exception_handler(HTTPException, http_exception_handler)  # 业务
    app.add_exception_handler(IntegrityError, integrity_error_handler)  # 数据完整性约束
    app.add_exception_handler(SQLAlchemyError, sqlalchemy_error_handler)  # 数据库
    app.add_exception_handler(Exception, general_exception_handler)  # 兜底
