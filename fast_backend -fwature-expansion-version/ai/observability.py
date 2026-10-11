"""LLM 调用可观测性 — Token 用量、首字延迟(TTFT)、按功能维度聚合（方案 §3.2 / Week2-5）

背景
----
改造前全项目**没有任何** token 计量与延迟打点，导致：

- 无法核算单个用户的真实 LLM 成本，会员配额（`daily_chat` 等）只能按「次数」
  粗粒度限流，高消耗用户与低消耗用户一视同仁；
- 流式对话首字延迟不可观测，用户抱怨「卡」时无法区分是模型慢还是我们慢；
- 模型替换（换更贵/更便宜的模型）没有数据支撑决策。

本模块提供两件事：

1. :func:`record_call` —— 每次 LLM 调用落一条结构化记录（写日志 + 进程内聚合）；
2. :class:`UsageRecorder` —— 进程内按 ``kind``/``user_id`` 聚合，供管理端报表与测试断言。

⚠️ 边界说明：聚合是**进程内存态**，与 ``utils/throttle`` / ``ai_concurrency`` 同一
生命周期约束（单 worker）。多 worker 部署时单进程只覆盖一部分流量；要跨进程
精确核算需落库（``ai_usage_daily`` 已有配额表，可扩列存 token）。当前实现的定位
是「排障与调优的即时可见性」，不是财务级账单。
"""

import logging
import time
from collections import defaultdict
from dataclasses import asdict, dataclass, field

logger = logging.getLogger(__name__)

# 功能维度：与 MEMBERSHIP_PLANS 的配额 kind 对齐，便于报表下钻
KIND_CHAT = "chat"
KIND_ANALYZE = "analyze"
KIND_BOOKKEEPING = "bookkeeping"
KIND_EMBEDDING = "embedding"


@dataclass
class LLMUsage:
    """单次 LLM 调用的计量记录"""

    kind: str                      # KIND_* 之一
    model: str                     # 实际使用的模型名
    user_id: int | None = None
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_ms: int = 0            # 端到端耗时
    ttft_ms: int | None = None     # 首字延迟；仅流式有值
    ok: bool = True
    error: str | None = None
    # 备用网关接管时为 True，便于统计容灾命中率
    failover: bool = False

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


class UsageRecorder:
    """进程内 Token / 延迟聚合器。

    聚合键为 ``(kind, user_id)``；``snapshot()`` 返回可直接 JSON 化的 dict。
    """

    def __init__(self, capacity: int = 5000):
        # 记录明细环形保留，防止长跑进程内存无限增长
        self._records: list[LLMUsage] = []
        self._capacity = capacity
        self._agg: dict[tuple[str, int | None], dict] = defaultdict(
            lambda: {"calls": 0, "prompt_tokens": 0, "completion_tokens": 0,
                     "latency_ms_sum": 0, "ttft_ms_sum": 0, "ttft_count": 0,
                     "errors": 0, "failovers": 0}
        )

    def record(self, usage: LLMUsage) -> None:
        self._records.append(usage)
        if len(self._records) > self._capacity:
            # 丢最旧的；聚合值已累加进 _agg，不受影响
            self._records.pop(0)
        a = self._agg[(usage.kind, usage.user_id)]
        a["calls"] += 1
        a["prompt_tokens"] += usage.prompt_tokens
        a["completion_tokens"] += usage.completion_tokens
        a["latency_ms_sum"] += usage.latency_ms
        if usage.ttft_ms is not None:
            a["ttft_ms_sum"] += usage.ttft_ms
            a["ttft_count"] += 1
        if not usage.ok:
            a["errors"] += 1
        if usage.failover:
            a["failovers"] += 1

    def snapshot(self) -> dict:
        """按 ``(kind, user_id)`` 输出均值化报表"""
        out: dict = {}
        for (kind, user_id), a in self._agg.items():
            calls = a["calls"] or 1
            out.setdefault(kind, {})[str(user_id)] = {
                "calls": a["calls"],
                "promptTokens": a["prompt_tokens"],
                "completionTokens": a["completion_tokens"],
                "totalTokens": a["prompt_tokens"] + a["completion_tokens"],
                "avgLatencyMs": round(a["latency_ms_sum"] / calls, 1),
                "avgTtftMs": (round(a["ttft_ms_sum"] / a["ttft_count"], 1)
                              if a["ttft_count"] else None),
                "errors": a["errors"],
                "failovers": a["failovers"],
            }
        return out

    def total_tokens(self) -> int:
        """累计 token 总数。

        取自**聚合值**而非明细列表：明细受 ``capacity`` 环形裁剪，
        长跑进程里 ``_records`` 只保留最近若干条，直接 sum 明细会漏掉历史。
        """
        return sum(a["prompt_tokens"] + a["completion_tokens"]
                   for a in self._agg.values())

    def reset(self) -> None:
        self._records.clear()
        self._agg.clear()


# 全局单例
recorder = UsageRecorder()


def extract_tokens(response) -> tuple[int, int]:
    """从 LangChain 返回对象里取 (prompt_tokens, completion_tokens)。

    langchain-core 把用量放在 ``usage_metadata``（AIMessage）或
    ``response_metadata['token_usage']``；两者都没有时返回 (0, 0)——
    部分第三方网关不返回用量，**不得因此抛异常**打断主流程。
    """
    meta = getattr(response, "usage_metadata", None)
    if isinstance(meta, dict):
        return (int(meta.get("input_tokens") or 0),
                int(meta.get("output_tokens") or 0))
    rm = getattr(response, "response_metadata", None) or {}
    tu = rm.get("token_usage") if isinstance(rm, dict) else None
    if isinstance(tu, dict):
        return (int(tu.get("prompt_tokens") or 0),
                int(tu.get("completion_tokens") or 0))
    return 0, 0


class Timer:
    """计时器：同时测总耗时与首字延迟

    用法::

        t = Timer()
        async for chunk in llm.astream(msgs):
            t.mark_first_chunk()      # 仅首个 chunk 调用
            ...
        t.elapsed_ms, t.ttft_ms
    """

    def __init__(self):
        self._start = time.perf_counter()
        self._first: float | None = None

    def mark_first_chunk(self) -> None:
        if self._first is None:
            self._first = time.perf_counter()

    @property
    def elapsed_ms(self) -> int:
        return round((time.perf_counter() - self._start) * 1000)

    @property
    def ttft_ms(self) -> int | None:
        if self._first is None:
            return None
        return round((self._first - self._start) * 1000)


def record_call(kind: str, model: str, user_id: int | None, *,
                response=None, timer: Timer | None = None,
                ok: bool = True, error: str | None = None,
                failover: bool = False) -> LLMUsage:
    """记录一次调用：写日志 + 进聚合器。**任何内部异常都不外抛。**"""
    try:
        pt, ct = extract_tokens(response) if response is not None else (0, 0)
        usage = LLMUsage(
            kind=kind,
            model=model,
            user_id=user_id,
            prompt_tokens=pt,
            completion_tokens=ct,
            latency_ms=timer.elapsed_ms if timer else 0,
            ttft_ms=timer.ttft_ms if timer else None,
            ok=ok,
            error=error,
            failover=failover,
        )
        recorder.record(usage)
        logger.info(
            "llm_call kind=%s model=%s user=%s pt=%d ct=%d latency_ms=%d ttft_ms=%s ok=%s failover=%s",
            kind, model, user_id, pt, ct, usage.latency_ms, usage.ttft_ms, ok, failover,
        )
        return usage
    except Exception:  # pragma: no cover - 计量失败绝不能影响业务
        logger.exception("record_call failed kind=%s model=%s", kind, model)
        return LLMUsage(kind=kind, model=model, user_id=user_id, ok=False)


def usage_to_dict(usage: LLMUsage) -> dict:
    return asdict(usage)