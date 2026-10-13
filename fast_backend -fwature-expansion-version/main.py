"""FastAPI 应用入口 — 对齐参考项目 toutiao_backend 的 main.py 风格

启动方式：
    uvicorn main:app --reload
"""

import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from config.settings import CORS_ORIGINS
from routers import admin, ai, category, membership, record, recharge, statistics, user
from utils.exception_handlers import register_exception_handlers
from utils.response import success_response

logger = logging.getLogger(__name__)

# 项目根（本文件所在目录）：uploads 相关路径一律锚定到这里，
# 之前用相对路径挂载/落盘，uvicorn 换个 CWD 启动就 404 或写错位置
BASE_DIR = Path(__file__).resolve().parent

# Windows 控制台默认 GBK，日志里的 emoji（📊 等）会触发 UnicodeEncodeError。
# 统一切到 UTF-8 且不可编码字符降级为占位符，保证日志永不中断业务流程。
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")


@asynccontextmanager
async def lifespan(_: FastAPI):
    # 启动兜底：FAQ 内存向量索引随进程重启清空，这里先装填关键词索引
    # （零 API 成本），语义索引仍由管理员调 /api/ai/faq/rebuild 全量重建。
    try:
        from ai import faq_retriever
        from config.db_config import AsyncSessionLocal
        from crud import ai as ai_crud

        async with AsyncSessionLocal() as session:
            rows = await ai_crud.list_faq(session)
            count = await faq_retriever.ensure_index(rows)
            logger.info("startup: FAQ keyword index loaded, %d rows", count)
    except Exception:
        logger.exception("startup: FAQ index preload failed (FAQ 检索暂不可用)")

    # 软删物理清理（可选依赖）：APScheduler 未安装时返回 False，仅少一项增强，
    # 不影响服务启动。
    try:
        from tasks.purge import start_scheduler

        if start_scheduler():
            logger.info("startup: purge scheduler enabled")
    except Exception:
        logger.exception("startup: purge scheduler 启动异常（不影响服务）")

    try:
        yield
    finally:
        try:
            from tasks.purge import stop_scheduler

            stop_scheduler()
        except Exception:
            logger.exception("shutdown: 停止 purge scheduler 失败")

        # 释放 STT provider 持有的 httpx 连接池（连接复用后需显式关闭，
        # 否则停机时会留 unclosed client 警告）。未启用 STT 时是空操作。
        try:
            from ai.stt import aclose_stt_provider

            await aclose_stt_provider()
        except Exception:
            logger.exception("shutdown: 关闭 STT 连接池失败（不影响停机）")


app = FastAPI(lifespan=lifespan)

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

# 静态资源（头像）：锚定 BASE_DIR，不随启动 CWD 变化
(BASE_DIR / "uploads").mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=BASE_DIR / "uploads"), name="uploads")


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
app.include_router(membership.router)         # /api/membership（用户侧）
app.include_router(membership.admin_router)   # /api/admin/membership（管理侧）
app.include_router(recharge.router)           # /api/recharge（用户侧 + 支付回调闸口）
app.include_router(recharge.admin_router)     # /api/admin/recharges（充值审批）
