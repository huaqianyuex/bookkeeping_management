"""FastAPI 应用入口 — 对齐参考项目 toutiao_backend 的 main.py 风格

启动方式：
    uvicorn main:app --reload
"""

import os
import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from config.settings import CORS_ORIGINS
from routers import admin, ai, category, record, statistics, user
from utils.exception_handlers import register_exception_handlers
from utils.response import success_response

# Windows 控制台默认 GBK，日志里的 emoji（📊 等）会触发 UnicodeEncodeError。
# 统一切到 UTF-8 且不可编码字符降级为占位符，保证日志永不中断业务流程。
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

app = FastAPI()

# 注册全局异常处理器
register_exception_handlers(app)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,  # 允许的前端来源
    allow_credentials=True,  # 允许携带 cookie
    allow_methods=["*"],  # 允许所有请求方法
    allow_headers=["*"],  # 允许所有请求头
)

# 静态资源（头像）
os.makedirs("uploads", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")


# 健康检查
@app.get("/api/health")
async def health():
    return success_response(data={"status": "ok", "version": "1.0.0"})


# 挂载路由（每个 router 自带 prefix="/api/<resource>" 与 tags）
app.include_router(user.router)
app.include_router(category.router)
app.include_router(record.router)
app.include_router(statistics.router)
app.include_router(admin.router)
app.include_router(ai.router)
