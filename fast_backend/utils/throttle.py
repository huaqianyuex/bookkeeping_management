"""登录频率限制 —— 防在线爆破的兜底措施（P2-4.1）

设计口径：
- 单进程内存字典（`{username|ip: (fails, last_ts)}`），过期窗口自动重置；
- 触发阈值后返回 retry_after 秒，路由据此抛 429；
- 多 worker 部署时，各进程各自计数——生产环境应改接 Redis（本仓库当前
  单 worker 运行，先保证 6 位 PIN 不被脚本无限刷）。

调用侧：
    from utils.throttle import login_throttle
    ...
    if not login_throttle.check(key):
        raise HTTPException(429, "尝试过于频繁，请稍后再试")
    if not password_ok:
        login_throttle.record_fail(key)
    else:
        login_throttle.reset(key)
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass


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
