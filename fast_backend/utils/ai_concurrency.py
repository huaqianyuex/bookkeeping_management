"""AI 流式并发限流 — 进程内 per-user 信号量（骨架：函数签名 + TODO）

实现规格：docs/membership-plan.md §4.3。

⚠️ 部署前提：单 worker 进程（同 utils/throttle.py::LoginThrottle 的声明）。
多 worker / 多机部署时需替换为 Redis（INCR+EXPIRE 或令牌桶），保持函数形状不变即可。

用法（在 /api/ai/chat/stream 的生成器内，接入配额闸门时使用）：
    release = await try_acquire(user_id, plan["concurrency"])
    if release is None:
        yield sse({"type": "error", "code": "CONCURRENCY_LIMIT", "error": "您的对话并发已达上限，请等待当前回复完成"})
        return
    try:
        ...
    finally:
        release()

返回闭包而非裸 Semaphore，是为了规避「用户升级导致 limit 变化、信号量被重建后
旧持有者误释放新信号量」的错位问题。
"""

import asyncio
from collections.abc import Callable

# user_id -> (信号量, 建立时的 limit)；limit 变化（升级/过期）时重建
_slots: dict = {}


async def try_acquire(user_id: int, limit: int) -> Callable[[], None] | None:
    """尝试占用一个并发槽。成功返回 release 闭包（调用方在 finally 中执行）；满额返回 None。

    TODO:
      1) entry = _slots.get(user_id)；entry 为 None 或 entry[1] != limit
         -> 重建 (asyncio.Semaphore(limit), limit) 存回 _slots
      2) sem.locked()（value==0）-> return None
         （单线程事件循环内 locked() 与 acquire() 之间无 await，判定原子）
      3) await sem.acquire() 后返回闭包 lambda: sem.release()
    """
    raise NotImplementedError
