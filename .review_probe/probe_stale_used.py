"""Review probe: is the `used` value reported by consume_quota on the REJECTED path fresh?

Reproduces the real call sequence of routers/ai.py::_quota_gate inside one request
transaction, against a real MySQL scratch DB (dropped at the end).
"""
import asyncio
import os
import sys
import time
from datetime import date
from pathlib import Path

PROJ = Path(r"E:\一些毕设探索\Accounting Management System_fastapi\fast_backend -fwature-expansion-version")
sys.path.insert(0, str(PROJ))
os.chdir(PROJ)

from dotenv import load_dotenv  # noqa: E402

load_dotenv(PROJ / ".env")
BASE = os.environ["DATABASE_URL"]
SCRATCH = "review_stale_used_tmp"
head, _, query = BASE.partition("?")
prefix, _db = head.rsplit("/", 1)
SERVER_URL = prefix + "/"
SCRATCH_URL = f"{prefix}/{SCRATCH}" + (f"?{query}" if query else "")
os.environ["DATABASE_URL"] = SCRATCH_URL
os.environ["JWT_SECRET_INSECURE_OK"] = "1"

from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine  # noqa: E402


async def reset_db():
    eng = create_async_engine(SERVER_URL)
    async with eng.begin() as conn:
        await conn.execute(text(f"DROP DATABASE IF EXISTS `{SCRATCH}`"))
        await conn.execute(text(f"CREATE DATABASE `{SCRATCH}` CHARACTER SET utf8mb4"))
    await eng.dispose()

    import models.bookkeeping, models.category, models.chat, models.membership  # noqa
    import models.record, models.user  # noqa
    from models.base import Base

    eng = create_async_engine(SCRATCH_URL)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await eng.dispose()


async def seed(username: str, used: int, sessions: int = 1):
    eng = create_async_engine(SCRATCH_URL)
    sf = async_sessionmaker(eng, class_=AsyncSession, expire_on_commit=False)
    async with sf() as db:
        await db.execute(text(
            "INSERT INTO users (username, password, role, status) VALUES (:u, 'x', 0, 1)"
        ), {"u": username})
        uid = (await db.execute(text(
            "SELECT id FROM users WHERE username=:u"), {"u": username})).scalar_one()
        sids = [f"session_{username}_{i}" for i in range(sessions)]
        for sid in sids:
            await db.execute(text(
                "INSERT INTO sessions (id, user_id, title, auto_title, created_at, updated_at, deleted_at)"
                " VALUES (:i, :u, 't', 1, 0, 0, 0)"
            ), {"i": sid, "u": uid})
        if used is not None:
            await db.execute(text(
                "INSERT INTO ai_usage_daily (user_id, usage_date, chat_count, analyze_count, bookkeeping_count)"
                " VALUES (:u, :d, :c, 0, 0)"
            ), {"u": uid, "d": date.today(), "c": used})
        await db.commit()
    await eng.dispose()
    return uid, sids


async def true_count(uid: int) -> int:
    eng = create_async_engine(SCRATCH_URL)
    sf = async_sessionmaker(eng, class_=AsyncSession, expire_on_commit=False)
    async with sf() as db:
        n = (await db.execute(text(
            "SELECT chat_count FROM ai_usage_daily WHERE user_id=:u AND usage_date=:d"
        ), {"u": uid, "d": date.today()})).scalar_one_or_none()
    await eng.dispose()
    return n


PLAN = {"daily_chat": 10}


async def scenario_deterministic():
    """Interleave: T1 opens (gate reads tier) -> T2 consumes the last slot -> T1 consumes."""
    from crud import membership as mc

    uid, _ = await seed("probe_det", 9)

    eng = create_async_engine(SCRATCH_URL)
    S = async_sessionmaker(eng, class_=AsyncSession, expire_on_commit=False)

    s1 = S()
    # faithful first step of _quota_gate: get_tier() issues a consistent read -> read view fixed here
    tier = await mc.get_tier(s1, uid)
    print(f"  T1 get_tier -> {tier} (read view established, snapshot chat_count=9)")

    async with S() as s2:
        r2 = await mc.consume_quota(s2, uid, PLAN, "chat")
    print(f"  T2 consume_quota -> admitted={r2[0]} used={r2[1]} limit={r2[2]}  (T2 committed, count=10)")

    r1 = await mc.consume_quota(s1, uid, PLAN, "chat")
    real = await true_count(uid)
    print(f"  T1 consume_quota -> admitted={r1[0]} used={r1[1]} limit={r1[2]}")
    print(f"  actual committed chat_count = {real}")
    verdict = "OK" if r1[1] == real else f"STALE: payload says {r1[1]} but truth is {real}"
    print(f"  REJECTED-PATH used vs truth: {verdict}")
    await s1.close()
    await eng.dispose()
    return r1, real


async def scenario_http_burst():
    """Real endpoint: 5 concurrent POST /api/ai/chat for a free user at chat_count=9, limit=10."""
    from httpx import ASGITransport, AsyncClient

    import routers.ai as ai_router
    from main import app
    from utils.security import create_access_token

    uid, sids = await seed("probe_http", 9)
    token = create_access_token(uid)

    async def fake_chat(messages):
        await asyncio.sleep(0.4)
        return "ok"

    ai_router.chat_chain.chat = fake_chat

    h = {"Authorization": f"Bearer {token}"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://probe") as c:
        resps = await asyncio.gather(*[
            c.post("/api/ai/chat", json={"sessionId": sids[0], "message": f"并发{i}"}, headers=h)
            for i in range(5)
        ])
    print("  statuses:", [r.status_code for r in resps])
    for r in resps:
        if r.status_code == 429:
            b = r.json()
            print(f"    429 body -> used={b.get('used')} limit={b.get('limit')} | {b.get('error')}")
        else:
            print("    200 body keys:", list(r.json().keys()))
    real = await true_count(uid)
    print(f"  actual committed chat_count = {real}")
    return resps, real


async def main():
    await reset_db()
    print("=== A. deterministic interleaving (real crud.membership functions) ===")
    r1, real = await scenario_deterministic()
    print("\n=== B. real HTTP endpoint: 5 concurrent /api/ai/chat at 9/10 ===")
    await scenario_http_burst()

    eng = create_async_engine(SERVER_URL)
    async with eng.begin() as conn:
        await conn.execute(text(f"DROP DATABASE IF EXISTS `{SCRATCH}`"))
    await eng.dispose()
    print("\nscratch DB dropped")


asyncio.run(main())
