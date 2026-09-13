"""应用配置 — 使用 os.getenv 读取 .env，对齐参考项目配置风格

参考项目用 os.getenv + 硬编码常量；这里统一用 os.getenv 承载更丰富的配置项。
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
JWT_SECRET = os.getenv("JWT_SECRET", "***REMOVED***")
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
DEBUG_MODE = os.getenv("DEBUG_MODE", "true").lower() == "true"
