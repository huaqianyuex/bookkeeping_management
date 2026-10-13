"""上游 LLM 网关重试与错误分类 —— 429 / 5xx 指数退避（审查报告 P1-6）

背景
----
Agnes 网关在模型过载时返回 ``HTTP 429 + code 1305「该模型当前访问量过大，请稍后再试」``。
改造前只靠 ``LLM_MAX_RETRIES=1`` 让 SDK 重试一次（退避约 0.5s），对持续数秒的过载
实际等于不重试，于是：

- 记账链：429 被路由兜成「记账解析失败，请换个说法再试」——**用户白改说法**，
  真正的瓶颈在上游；
- 对话链：SSE 首字节前 429 直接以 error 事件结束。

本模块提供两件事：**能不能重试** 与 **等多久再试**，并单独回答
``is_upstream_busy``（上游过载）以便路由给出准确文案。

口径（勿随意放宽）
------------------
1. **只重试瞬时失败**：连接层错误 / 超时 / 429 / 5xx。
   4xx（400/401/403/404/422）是请求自身的问题，重试只会白跑并放大计费。
2. **指数退避 + 抖动**：默认 0.8s → 1.6s → 3.2s（单次上限 4s），叠加 ±25% 抖动，
   避免多个用户的重试在同一时刻同步打向已经过载的网关。
   若上游给了 ``Retry-After``，优先采纳（但仍受单次与总预算上限约束）。
3. **总耗时受限**：累计等待不超过 ``LLM_RETRY_TOTAL_BUDGET_SECONDS``（默认 8s）。
   超预算即放弃重试、把异常抛给调用方——宁可快速失败，也不要把用户请求拖过
   前端 timeout（记账 60s / 对话 120s），更不该一直占着 ai_concurrency 并发槽。
4. **只重试「未产出」的调用**：非流式调用天然满足；流式调用方必须自己保证
   「已向下游 yield 过内容就不再重试」，否则用户会看到重复文本、上游被重复计费。
5. **SDK 自带重试必须关掉**（``ai/llm.py`` 统一 ``max_retries=0``）：两层重试相乘
   会把一次用户请求放大成 N×M 次上游调用，这正是本模块要避免的。

⚠️ 边界：重试计数与退避都在进程内，不跨 worker 协调（与配额/并发/限流同生命周期约束）。
"""

from __future__ import annotations

import asyncio
import logging
import random
import time
from typing import Awaitable, Callable, TypeVar

import httpx
import openai

from config import settings

logger = logging.getLogger(__name__)

T = TypeVar("T")

# 值得重试的 HTTP 状态：408 超时 / 409 冲突 / 429 限流 / 5xx 服务端错误
RETRYABLE_STATUS = frozenset({408, 409, 429, 500, 502, 503, 504})

# 退避曲线（秒）：0.8 → 1.6 → 3.2，单次上限 4s
_BASE_DELAY = 0.8
_MAX_DELAY = 4.0
_JITTER = 0.25          # ±25%

# openai 的连接/超时异常类名在不同大版本间有差异，取不到就不参与判定
_CONN_EXC = tuple(
    c for c in (
        getattr(openai, "APITimeoutError", None),
        getattr(openai, "APIConnectionError", None),
    )
    if isinstance(c, type)
)


def _status_code(exc: Exception) -> int | None:
    """从异常上取 HTTP 状态码；非 HTTP 类异常返回 None"""
    code = getattr(exc, "status_code", None)
    return code if isinstance(code, int) else None


def is_retryable(exc: Exception) -> bool:
    """是否属于「再试一次有意义」的瞬时上游故障"""
    if _CONN_EXC and isinstance(exc, _CONN_EXC):
        return True
    code = _status_code(exc)
    if code is not None:
        return code in RETRYABLE_STATUS
    # 未经 openai SDK 包装的连接层异常（例如自定义 httpx 调用）
    return isinstance(exc, httpx.TransportError)


def is_upstream_busy(exc: Exception) -> bool:
    """上游过载：429（模型访问量过大）或网关 5xx。

    必须与「用户消息说法有问题」严格区分——过载时提示用户「稍后重试」，
    而非「换个说法」（改了说法也一样失败，只会让用户白试十遍）。
    """
    code = _status_code(exc)
    if code is None:
        return False
    return code == 429 or 500 <= code < 600


def _retry_after(exc: Exception) -> float | None:
    """读取上游 ``Retry-After`` 头（秒）；缺失或非法返回 None"""
    resp = getattr(exc, "response", None)
    headers = getattr(resp, "headers", None)
    if not headers:
        return None
    raw = headers.get("retry-after")
    if not raw:
        return None
    try:
        return max(0.0, float(raw))
    except (TypeError, ValueError):
        return None


def max_attempts() -> int:
    """总尝试次数 = 1 次首试 + LLM_MAX_RETRIES 次重试"""
    try:
        retries = int(settings.LLM_MAX_RETRIES)
    except (TypeError, ValueError):
        retries = 1
    return max(1, retries + 1)


def total_budget() -> float:
    """重试累计等待上限（秒）"""
    try:
        return max(0.0, float(settings.LLM_RETRY_TOTAL_BUDGET_SECONDS))
    except (TypeError, ValueError):
        return 8.0


def retry_delay(attempt: int, exc: Exception, *, elapsed: float,
                attempts: int | None = None,
                budget: float | None = None) -> float | None:
    """第 ``attempt`` 次失败后应等待的秒数；**None 表示不再重试**。

    None 的三种情形：次数用尽、异常不值得重试、等待会超出总预算。
    抽成独立函数是为了让流式调用方（``ai/chat_chain.chat_stream``）复用同一套
    曲线与预算，而不必把「已 yield 过内容」这一副作用塞进 :func:`with_retry`。
    """
    max_n = max_attempts() if attempts is None else attempts
    if attempt >= max_n or not is_retryable(exc):
        return None
    total = total_budget() if budget is None else budget
    delay = min(_BASE_DELAY * (2 ** (attempt - 1)), _MAX_DELAY)
    hinted = _retry_after(exc)
    if hinted is not None:
        delay = min(hinted, _MAX_DELAY)
    delay *= 1 + random.uniform(-_JITTER, _JITTER)
    if elapsed + delay > total:
        return None
    return delay


async def with_retry(
    fn: Callable[[], Awaitable[T]],
    *,
    attempts: int | None = None,
    budget: float | None = None,
) -> T:
    """执行 ``fn()``；对可重试的上游失败做指数退避重试，否则原样抛出。

    只适用于**整次调用可重放**的场景（非流式）。流式请用 :func:`retry_delay`
    自行控制，并且必须保证「已向下游 yield 过内容就不再重试」。
    """
    max_n = max_attempts() if attempts is None else attempts
    total = total_budget() if budget is None else budget
    started = time.monotonic()

    for attempt in range(1, max_n + 1):
        try:
            return await fn()
        except Exception as exc:
            # CancelledError / GeneratorExit 是 BaseException，不会走到这里，
            # 因此客户端中断不会被误当成上游故障重试。
            delay = retry_delay(attempt, exc, elapsed=time.monotonic() - started,
                                attempts=max_n, budget=total)
            if delay is None:
                raise
            logger.warning(
                "upstream retry %d/%d after %.2fs (%s)",
                attempt, max_n, delay, type(exc).__name__,
            )
            await asyncio.sleep(delay)

    raise AssertionError("unreachable")   # pragma: no cover - 循环必在内部 return/raise