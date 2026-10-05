"""AI 流式并发限流 — 进程内 per-user 信号量

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

    单线程事件循环内 locked() 与 acquire() 之间没有 await，因此"判定-获取"是原子的；
    多 worker 部署时这里必须换成 Redis 计数器（否则每个进程各有一份信号量）。
    """
    entry = _slots.get(user_id)
    if entry is None or entry[1] != limit:
        # 用户升级/过期导致 limit 变化时重建信号量；旧的 release 闭包仍持有旧信号量，
        # 因此释放不会串到新信号量上（这正是返回闭包而非裸 Semaphore 的原因）
        entry = (asyncio.Semaphore(limit), limit)
        _slots[user_id] = entry

    sem = entry[0]
    if sem.locked():
        return None
    await sem.acquire()

    def _release(_sem: asyncio.Semaphore = sem) -> None:
        _sem.release()

    return _release
