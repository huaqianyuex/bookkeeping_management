"""应用配置 — 使用 os.getenv 读取 .env，对齐参考项目配置风格

参考项目用 os.getenv + 硬编码常量；这里统一用 os.getenv 承载更丰富的配置项。

安全提醒：
- DEBUG_MODE 默认 false，生产环境不该将 traceback/内部路径暴露给调用方；
- JWT_SECRET 为必填项（且不再是仓库中公开的默认值），缺失时启动即报错；
- 设 JWT_SECRET_INSECURE_OK=1 可以跳过检查，仅用于本地开发。
"""

import hashlib
import os
from pathlib import Path

from dotenv import load_dotenv

# 加载 .env 配置文件
load_dotenv()

# 项目根（config/ 的上一级）：相对上传路径统一锚定到这里，避免随启动 CWD 漂移
_BASE_DIR = Path(__file__).resolve().parent.parent


def _anchored_path(raw: str) -> str:
    p = Path(raw)
    return str(p if p.is_absolute() else _BASE_DIR / p)

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
AVATAR_DIR = _anchored_path(os.getenv("AVATAR_DIR", "uploads/avatars"))
AVATAR_URL_PREFIX = os.getenv("AVATAR_URL_PREFIX", "/uploads/avatars/")
MAX_AVATAR_SIZE = int(os.getenv("MAX_AVATAR_SIZE", str(2 * 1024 * 1024)))

# ---- JWT ----
# JWT_SECRET 为必填项，不提供仓库中公开的默认值；
# 早期版本曾内置固定默认密钥（现已从仓库历史清除），启动校验会按指纹拒绝。
JWT_SECRET = os.getenv("JWT_SECRET", "")

# 早期版本内置默认密钥的 SHA-256 指纹（刻意不重现明文），用于启动校验拒绝该已作废值
_BURNED_JWT_SECRET_SHA256 = (
    "307db649133770dc57dfa40ac63c8b861e1c7fe1274d45d06b903e558a1766ba"
)
JWT_EXPIRE_SECONDS = int(os.getenv("JWT_EXPIRE_SECONDS", "86400"))

# ---- AI ----
AGNES_API_KEY = os.getenv("AGNES_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://apihub.agnes-ai.com/v1")
CHAT_MODEL = os.getenv("CHAT_MODEL", "agnes-2.5-flash")
ANALYZE_MODEL = os.getenv("ANALYZE_MODEL", "agnes-2.0-flash")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")

# ---- AI 调用护栏 ----
# 之前 ChatOpenAI / OpenAIEmbeddings 全部不设上限：输出无界、单请求无超时、
# 失败不重试，配额闸门只能限「次数」限不住「单次烧多少」，且网关挂起时会
# 长时间占住并发槽（concurrency 是进程内槽位，占住即对用户限流）。
LLM_TIMEOUT_SECONDS = float(os.getenv("LLM_TIMEOUT_SECONDS", "60"))
LLM_MAX_RETRIES = int(os.getenv("LLM_MAX_RETRIES", "1"))
# 按用途分档：对话要说人话给上限，结构化抽取输出短，超限会被截断成非法 JSON。
CHAT_MAX_TOKENS = int(os.getenv("CHAT_MAX_TOKENS", "1024"))
ANALYZE_MAX_TOKENS = int(os.getenv("ANALYZE_MAX_TOKENS", "1536"))

# ---- 语音转写（STT）----
# 放在 AI 块之后：STT_BASE_URL / STT_API_KEY 引用上面的 OPENAI_BASE_URL / AGNES_API_KEY。
# Provider 可替换（ai/stt.py 注册表）：agnes 网关若不支持 /audio/transcriptions，
# 在 .env 中改 STT_BASE_URL 指向 OpenAI 官方或自建 faster-whisper 即可，代码零改动。
STT_ENABLED = os.getenv("STT_ENABLED", "true").lower() == "true"
STT_PROVIDER = os.getenv("STT_PROVIDER", "openai_whisper")
STT_MODEL = os.getenv("STT_MODEL", "whisper-1")
STT_BASE_URL = os.getenv("STT_BASE_URL", OPENAI_BASE_URL)   # 可独立覆盖
STT_API_KEY = os.getenv("STT_API_KEY", AGNES_API_KEY)       # 可独立覆盖
STT_TIMEOUT_SECONDS = int(os.getenv("STT_TIMEOUT_SECONDS", "30"))
STT_MAX_SECONDS = int(os.getenv("STT_MAX_SECONDS", "60"))       # 客户端录音上限（recorder.duration）
STT_MAX_SIZE_MB = int(os.getenv("STT_MAX_SIZE_MB", "5"))
STT_LOW_CONFIDENCE = float(os.getenv("STT_LOW_CONFIDENCE", "0.4"))  # 低于该值前端提示「请核对」
VOICE_RATE_LIMIT_PER_MIN = int(os.getenv("VOICE_RATE_LIMIT_PER_MIN", "5"))

# ---- 会员 ----
# 会员对话走的高级模型；未配置时回退 CHAT_MODEL（以 Agnes 平台实际可用模型为准），
# 在 .env 中按需开启：CHAT_MODEL_PREMIUM=agnes-2.5-pro
CHAT_MODEL_PREMIUM = os.getenv("CHAT_MODEL_PREMIUM", "")

# 权益矩阵：数值即口径，前端权益表从 GET /api/membership/status 动态取，不硬编码。
# tier 为生效等级（0=免费 1=会员）；会员过期由查询时惰性降级（docs/membership-plan.md §0）。
MEMBERSHIP_PLANS = {
    0: {
        "name": "免费版",
        "daily_chat": 10,
        "concurrency": 1,
        "daily_analyze": 2,
        "daily_bookkeeping": 5,
        "premium_model": False,
    },
    1: {
        "name": "会员",
        "daily_chat": 100,
        "concurrency": 3,
        "daily_analyze": 30,
        "daily_bookkeeping": 50,
        "premium_model": True,
    },
}

# ---- 充值/审批 ----
# 套餐目录：服务端唯一定价源，客户端只传套餐 ID（杜绝金额篡改）。
# price 用字符串承载 Decimal（金额全链路禁 float）；days 与会员兑换码同口径（叠加语义）。
RECHARGE_PLANS = {
    "month":   {"name": "月卡", "days": 30,  "price": "18.00"},
    "quarter": {"name": "季卡", "days": 90,  "price": "45.00"},
    "year":    {"name": "年卡", "days": 365, "price": "158.00"},
}
# 待支付订单有效期（秒）：超时由读/支付路径懒关闭，无定时任务（与会员惰性降级同思路）
RECHARGE_ORDER_TTL_SECONDS = int(os.getenv("RECHARGE_ORDER_TTL_SECONDS", "900"))
# 风控阈值：单笔金额 ≥ 单笔阈值，或当日累计（已支付+待审批）≥ 累计阈值 → 支付后转人工审批。
# 阈值不下发前端（防止探测后拆单绕过），用户端只展示"大额订单需人工审核"的通用文案。
RECHARGE_MANUAL_REVIEW_AMOUNT = os.getenv("RECHARGE_MANUAL_REVIEW_AMOUNT", "100")
RECHARGE_DAILY_REVIEW_AMOUNT = os.getenv("RECHARGE_DAILY_REVIEW_AMOUNT", "200")
# 幂等/防刷：同一用户进行中（待支付）订单上限；创建订单频率；模拟支付连续失败冷却
RECHARGE_MAX_PENDING_ORDERS = int(os.getenv("RECHARGE_MAX_PENDING_ORDERS", "1"))
RECHARGE_RATE_MAX_CREATE = int(os.getenv("RECHARGE_RATE_MAX_CREATE", "3"))
RECHARGE_RATE_WINDOW_SECONDS = int(os.getenv("RECHARGE_RATE_WINDOW_SECONDS", "60"))
RECHARGE_PAY_FAIL_LIMIT = int(os.getenv("RECHARGE_PAY_FAIL_LIMIT", "5"))
RECHARGE_PAY_FAIL_COOLDOWN_SECONDS = int(os.getenv("RECHARGE_PAY_FAIL_COOLDOWN_SECONDS", "900"))
# 支付回调 HMAC 密钥：回调是充值链路唯一能推进订单到「已支付/待审批」的闸口，
# 密钥只在服务端（客户端拿不到 → 无法伪造"支付成功"）。未配置时从 JWT_SECRET 派生
# （每个部署唯一、不入仓库）；生产环境建议在 .env 中显式设置独立随机值。
RECHARGE_CALLBACK_SECRET = os.getenv("RECHARGE_CALLBACK_SECRET", "")

# ---- 对话记忆 ----
MAX_HISTORY_TOKENS = int(os.getenv("MAX_HISTORY_TOKENS", "2000"))
KEEP_RECENT_MESSAGES = int(os.getenv("KEEP_RECENT_MESSAGES", "6"))

# ---- FAQ 检索 ----
FAQ_TOP_K = int(os.getenv("FAQ_TOP_K", "3"))
# ⚠️ 口径：这是**原始余弦**阈值（值域 [-1,1]，实际有效区间约 0.2~0.9），不是归一化值。
# 历史 bug：_cosine() 返回 (cos+1)/2 归一化到 [0,1]，而阈值也写 0.5，等价于
# 「原始余弦 ≥ 0 即通过」，过滤形同虚设、top_k 退化成「任意 3 条」。
# 现已改为用原始余弦比较，此处默认值 0.45 对应归一化 0.725。
FAQ_SIMILARITY_THRESHOLD = float(os.getenv("FAQ_SIMILARITY_THRESHOLD", "0.45"))
# query→向量 的进程内 LRU 缓存条目数：FAQ 问题重复率极高（"怎么记账"会被反复问），
# 命中即省一次 Embedding 调用（真金白银），进程内即可，索引重建后自然失效。
FAQ_QUERY_CACHE_SIZE = int(os.getenv("FAQ_QUERY_CACHE_SIZE", "256"))
# 对话链路是否把 FAQ 命中注入 system prompt（见 ai/faq_retriever.build_knowledge_block）。
FAQ_INJECT_ENABLED = os.getenv("FAQ_INJECT_ENABLED", "true").lower() == "true"
# GET /faq/search 的 per-user 滑动窗口限流（次/分钟）：cache miss 即一次 Embedding 计费，
# 认证用户可无限刷 /faq/search 放大成本（审查报告 P0-4），需独立成本防护（口径同语音限流）。
FAQ_RATE_LIMIT_PER_MIN = int(os.getenv("FAQ_RATE_LIMIT_PER_MIN", "30"))
# 低于该 confidence 的记账条目在响应里给出「请核对」提示（不阻断入账）
BK_LOW_CONFIDENCE = float(os.getenv("BK_LOW_CONFIDENCE", "0.5"))

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
    global JWT_SECRET
    insecure_ok = os.getenv("JWT_SECRET_INSECURE_OK", "").lower() in ("1", "true", "yes")
    weak_defaults = {"secret", "changeme", "dev-insecure-secret-please-change-me"}
    if not JWT_SECRET:
        if insecure_ok:
            # 必须直接给模块常量赋值：JWT_SECRET 在模块导入时已读取为空串，
            # 仅回写 os.environ 不会生效，security.py 会用空密钥签发 token。
            JWT_SECRET = "dev-insecure-secret-please-change-me"
            return
        raise RuntimeError(
            "JWT_SECRET 未设置：请在 .env 中提供一个至少 32 位的随机字符串。\n"
            "开发环境如需跳过检查，设置环境变量 JWT_SECRET_INSECURE_OK=1。"
        )
    burned_fingerprint = hashlib.sha256(JWT_SECRET.encode("utf-8")).hexdigest()
    if (
        JWT_SECRET in weak_defaults
        or len(JWT_SECRET) < 32
        or burned_fingerprint == _BURNED_JWT_SECRET_SHA256
    ):
            if not insecure_ok:
                raise RuntimeError(
                    "JWT_SECRET 强度不足：不允许使用仓库公开默认值或小于 32 位的字符串。\n"
                    "开发环境如需跳过检查，设置环境变量 JWT_SECRET_INSECURE_OK=1。"
                )


_validate_security()

# ---- 充值回调密钥兜底（必须在 _validate_security() 之后）----
# JWT_SECRET 可能在上面的启动校验里才被赋予开发兜底值，派生放在这里才能拿到最终值；
# 显式配置了 RECHARGE_CALLBACK_SECRET 的部署不受影响。
if not RECHARGE_CALLBACK_SECRET:
    RECHARGE_CALLBACK_SECRET = f"recharge-callback:{JWT_SECRET}"
