"""应用配置 — 使用 os.getenv 读取 .env，对齐参考项目配置风格

参考项目用 os.getenv + 硬编码常量；这里统一用 os.getenv 承载更丰富的配置项。

安全提醒：
- DEBUG_MODE 默认 false，生产环境不该将 traceback/内部路径暴露给调用方；
- JWT_SECRET 为必填项（且不再是仓库中公开的默认值），缺失时启动即报错；
- 设 JWT_SECRET_INSECURE_OK=1 可以跳过检查，仅用于本地开发。
"""

import os

from dotenv import load_dotenv

# 加载 .env 配置文件
load_dotenv()

# ---- 服务 ----
APP_HOST = os.getenv("APP_HOST", "0.0.0.0")
APP_PORT = int(os.getenv("APP_PORT", "8080"))
# CORS 允许的来源（逗号分隔，仅允许前端开发服务器）
CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
    if origin.strip()
]

# ---- 上传（头像）----
AVATAR_DIR = os.getenv("AVATAR_DIR", "uploads/avatars")
AVATAR_URL_PREFIX = os.getenv("AVATAR_URL_PREFIX", "/uploads/avatars/")
MAX_AVATAR_SIZE = int(os.getenv("MAX_AVATAR_SIZE", str(2 * 1024 * 1024)))

# ---- JWT ----
# JWT_SECRET 为必填项，不提供仓库中公开的默认值；
# 原默认 ***REMOVED*** 已去除，避免仓库访问者伪造任意 token。
JWT_SECRET = os.getenv("JWT_SECRET", "")
JWT_EXPIRE_SECONDS = int(os.getenv("JWT_EXPIRE_SECONDS", "86400"))

# ---- AI ----
AGNES_API_KEY = os.getenv("AGNES_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://apihub.agnes-ai.com/v1")
CHAT_MODEL = os.getenv("CHAT_MODEL", "agnes-2.5-flash")
ANALYZE_MODEL = os.getenv("ANALYZE_MODEL", "agnes-2.0-flash")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")

# ---- 对话记忆 ----
MAX_HISTORY_TOKENS = int(os.getenv("MAX_HISTORY_TOKENS", "2000"))
KEEP_RECENT_MESSAGES = int(os.getenv("KEEP_RECENT_MESSAGES", "6"))

# ---- FAQ 检索 ----
FAQ_TOP_K = int(os.getenv("FAQ_TOP_K", "3"))
FAQ_SIMILARITY_THRESHOLD = float(os.getenv("FAQ_SIMILARITY_THRESHOLD", "0.5"))

# ---- 清理任务 ----
PURGE_INTERVAL_HOURS = int(os.getenv("PURGE_INTERVAL_HOURS", "6"))
PURGE_DELAY_DAYS = int(os.getenv("PURGE_DELAY_DAYS", "7"))

# ---- 调试 ----
# 生产部署默认 false；设为 true 后 500 响应会携带 traceback / 内部路径，
# 仅供本地调试使用。开发环境可 .env 中显式 DEBUG_MODE=true。
DEBUG_MODE = os.getenv("DEBUG_MODE", "false").lower() == "true"


# ---- 启动后安全校验 ----
def _validate_security() -> None:
    """JWT_SECRET 缺失/过短/使用仓库公开默认值 → 启动即报错。

    开发环境如需跳过校验，设置环境变量 JWT_SECRET_INSECURE_OK=1。
    """
    insecure_ok = os.getenv("JWT_SECRET_INSECURE_OK", "").lower() in ("1", "true", "yes")
    weak_defaults = {
        "***REMOVED***",
        "secret",
        "changeme",
    }
    if not JWT_SECRET:
        if insecure_ok:
            os.environ.setdefault("JWT_SECRET", "dev-insecure-secret-please-change-me")
            return
        raise RuntimeError(
            "JWT_SECRET 未设置：请在 .env 中提供一个至少 32 位的随机字符串。\n"
            "开发环境如需跳过检查，设置环境变量 JWT_SECRET_INSECURE_OK=1。"
        )
    if JWT_SECRET in weak_defaults or len(JWT_SECRET) < 32:
        if not insecure_ok:
            raise RuntimeError(
                "JWT_SECRET 强度不足：不允许使用仓库公开默认值或小于 32 位的字符串。\n"
                "开发环境如需跳过检查，设置环境变量 JWT_SECRET_INSECURE_OK=1。"
            )


_validate_security()
