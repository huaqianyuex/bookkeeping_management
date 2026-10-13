"""登录频率限制 —— 防在线爆破的兜底措施（P2-4.1）

设计口径：
- 单进程内存字典（`{username|ip: (fails, last_ts)}`），过期窗口自动重置；
- 触发阈值后返回 retry_after 秒，路由据此抛 429；
- 多 worker 部署时，各进程各自计数——生产环境应改接 Redis（本仓库当前
  单 worker 运行，先保证 6 位 PIN 不被脚本无限刷）。

调用侧：
    from utils.throttle import login_throttle
    ...
    locked, remain = login_throttle.is_locked(key)
    if locked:
        raise HTTPException(429, f"尝试过于频繁，请 {remain} 秒后再试")
    if not password_ok:
        login_throttle.record_fail(key)
    else:
        login_throttle.reset(key)
"""

from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import dataclass

from config.settings import VOICE_RATE_LIMIT_PER_MIN


@dataclass
class _Bucket:
    fails: int
    first_ts: float


class LoginThrottle:
    """滑动窗口计数器：同 key 在 window 秒内累计 max_fails 次失败即锁 throttle_seconds 秒"""

    def __init__(
        self,
        max_fails: int = 5,
        window: int = 300,           # 失败计数窗口：5 分钟
        throttle_seconds: int = 900,  # 触发阈值后锁定：15 分钟
        gc_interval: int = 600,       # 桶清理间隔
    ) -> None:
        self.max_fails = max_fails
        self.window = window
        self.throttle_seconds = throttle_seconds
        self.gc_interval = gc_interval
        self._buckets: dict[str, _Bucket] = {}
        self._locked: dict[str, float] = {}  # key -> 解锁时间戳
        self._last_gc = time.time()
        self._lock = threading.Lock()

    def _gc_if_needed(self) -> None:
        now = time.time()
        if now - self._last_gc < self.gc_interval:
            return
        cutoff = now - max(self.window, self.throttle_seconds)
        self._buckets = {k: v for k, v in self._buckets.items() if v.first_ts > cutoff}
        self._locked = {k: v for k, v in self._locked.items() if v > now}
        self._last_gc = now

    def is_locked(self, key: str) -> tuple[bool, int]:
        """返回 (是否被锁, 剩余秒数)；剩余秒数为 0 表示未锁"""
        with self._lock:
            self._gc_if_needed()
            until = self._locked.get(key, 0)
            now = time.time()
            if until > now:
                return True, int(until - now) + 1
            if until:
                # 已过期，清理
                self._locked.pop(key, None)
                self._buckets.pop(key, None)
            return False, 0

    def record_fail(self, key: str) -> None:
        with self._lock:
            self._gc_if_needed()
            now = time.time()
            bucket = self._buckets.get(key)
            if bucket is None or now - bucket.first_ts > self.window:
                self._buckets[key] = _Bucket(fails=1, first_ts=now)
                return
            bucket.fails += 1
            if bucket.fails >= self.max_fails:
                self._locked[key] = now + self.throttle_seconds
                self._buckets.pop(key, None)

    def reset(self, key: str) -> None:
        """登录成功时清空计数与锁，避免正常用户被误伤"""
        with self._lock:
            self._buckets.pop(key, None)
            self._locked.pop(key, None)


login_throttle = LoginThrottle()

# IP 维度兜底：`ip|username` 键换用户名即重置计数，分布式撞库 6 位数字口令
# 可以在每个用户名下都只失败 4 次。纯 IP 桶阈值更高（校内/公司 NAT 出口共享 IP，
# 太低会误锁一整片正常用户），只拦"同 IP 高频扫不同用户名"的脚本。
login_ip_throttle = LoginThrottle(max_fails=20, window=300, throttle_seconds=900)


class SlidingWindowRateLimiter:
    """滑动窗口放行计数：window 秒内同 key 最多 max_calls 次。

    与 LoginThrottle 的区别：这里是「成功也计数」的放行限流，
    不涉及锁定与失败累积，用于高频调用的外部服务入口（如语音转写）。
    """

    def __init__(self, max_calls: int = 5, window: int = 60, gc_interval: int = 300) -> None:
        self.max_calls = max_calls
        self.window = window
        self.gc_interval = gc_interval
        self._hits: dict[str, deque[float]] = {}
        self._last_gc = time.time()
        self._lock = threading.Lock()

    def _gc_if_needed(self, now: float) -> None:
        if now - self._last_gc < self.gc_interval:
            return
        cutoff = now - self.window
        self._hits = {k: v for k, v in self._hits.items() if v and v[-1] > cutoff}
        self._last_gc = now

    def allow(self, key: str) -> tuple[bool, int]:
        """返回 (是否放行, 还需等待秒数)；放行时等待秒数为 0"""
        with self._lock:
            now = time.time()
            self._gc_if_needed(now)
            dq = self._hits.setdefault(key, deque())
            cutoff = now - self.window
            while dq and dq[0] <= cutoff:
                dq.popleft()
            if len(dq) >= self.max_calls:
                return False, int(dq[0] + self.window - now) + 1
            dq.append(now)
            return True, 0

    def refund(self, key: str) -> None:
        """退还一次占位：外部调用**失败**时调用，撤销本次 allow 记下的命中。

        为什么是「先占后还」而不是「成功才记」
        ------------------------------------
        早先的实现是 check()（只查）+ record()（只记），两次各自加锁、中间隔着
        一次 await 外部调用。单事件循环下 N 个并发请求可以全部通过 check（发生在
        任何一次 record 落地之前）再依次执行，限流额度被放大 N 倍——而并发刷量
        恰恰是限流要防的攻击形态，等于护栏在真正需要时失效。

        现在改为 allow()（原子「查 + 记」）+ 失败时 refund()：
        占位发生在进入临界区时，不再有 check→await→record 的窗口；失败路径退还，
        既保证「失败不消耗成本额度」的原有语义，又不会把并发放行量放大。
        """
        with self._lock:
            dq = self._hits.get(key)
            if dq:
                dq.pop()
                if not dq:
                    self._hits.pop(key, None)


# 语音转写按用户限流：ASR 是按次计费的外部调用，先于配额闸门发生，需独立成本防护
voice_rate_limiter = SlidingWindowRateLimiter(
    max_calls=VOICE_RATE_LIMIT_PER_MIN, window=60
)
