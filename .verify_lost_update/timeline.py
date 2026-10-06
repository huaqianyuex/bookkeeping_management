"""Timeline probe: show the natural interleaving of two concurrent
POST /api/membership/redeem requests at the SQL level (no artificial delay).

If both transactions read user_membership (plain SELECT) before either COMMITs,
the lost update claimed against crud/membership.py:220-231 is proven reachable
under natural timing, not only under an injected barrier.
"""
import asyncio
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

PROJ = Path(r"E:\一些毕设探索\Accounting Management System_fastapi\fast_backend -fwature-expansion-version")
sys.path.insert(0, str(PROJ))
os.chdir(PROJ)

from dotenv import load_dotenv  # noqa: E402
load_dotenv(PROJ / ".env")
BASE = os.environ["DATABASE_URL"]
SCRATCH = "probe_timeline_tmp"
head, _, query = BASE.partition("?")
prefix, _db = head.rsplit("/", 1)
SERVER_URL = prefix + "/"
SCRATCH_URL = f"{prefix}/{SCRATCH}" + (f"?{query}" if query else "")
os.environ["DATABASE_URL"] = SCRATCH_URL

from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy import event, text  # noqa: E402
from sqlalchemy.ext.asyncio import (  # noqa: E402
    AsyncSession, async_sessionmaker, create_async_engine,
)


async def reset_and_seed(sf):
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

    async with sf() as db:
        await db.execute(text("INSERT INTO users (username,password,role,status) VALUES ('t','x',0,1)"))
        uid = (await db.execute(text("SELECT id FROM users WHERE username='t'"))).scalar_one()
        base = datetime.now() + timedelta(days=10)
        await db.execute(text(
            "INSERT INTO user_membership (user_id,tier,expires_at,source) VALUES (:u,1,:e,1)"),
            {"u": uid, "e": base})
        for ch in "AB":
            await db.execute(text(
                "INSERT INTO membership_codes (code,days,status,batch_no) VALUES (:c,30,0,'t')"),
                {"c": "T" + ch * 15})
        await db.commit()
    return uid, base


async def main():
    sf = async_sessionmaker(create_async_engine(SCRATCH_URL), class_=AsyncSession,
                            expire_on_commit=False)
    uid, base = await reset_and_seed(sf)

    from main import app
    from config.db_config import async_engine
    from utils.security import create_access_token

    t0 = time.perf_counter()
    log: list[tuple[float, str, int]] = []

    def before(conn, cursor, statement, params, context, executemany):
        s = " ".join(statement.split())[:78]
        log.append((time.perf_counter() - t0, s, id(conn)))

    event.listen(async_engine.sync_engine, "before_cursor_execute", before)

    h = {"Authorization": f"Bearer {create_access_token(str(uid))}"}
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://probe") as client:
        r = await asyncio.gather(
            client.post("/api/membership/redeem", json={"code": "TA" + "A" * 14}, headers=h),
            client.post("/api/membership/redeem", json={"code": "TB" + "B" * 14}, headers=h),
        )
    print("HTTP:", [(x.status_code, x.json().get("message")) for x in r])

    # label each connection with A/B by its first membership_codes SELECT target
    labels: dict[int, str] = {}
    for _, s, cid in log:
        if cid not in labels and ("membership_codes" in s and "SELECT" in s):
            labels[cid] = "A" if "= %s" in s and len(labels) == 0 else ("B" if len(labels) == 1 else "?")

    print("\n t(ms)  conn  statement")
    for dt, s, cid in log:
        if any(k in s for k in ("membership_codes", "user_membership", "COMMIT", "ROLLBACK")):
            print(f"{dt*1000:7.2f}  {labels.get(cid,'?'):>4}  {s}")

    reads = [dt for dt, s, cid in log if s.startswith("SELECT") and "user_membership" in s]
    commits = [dt for dt, s, cid in log if s.startswith("COMMIT")]
    if reads and commits:
        print(f"\nfirst membership read at {reads[0]*1000:.2f}ms, "
              f"last membership read at {reads[-1]*1000:.2f}ms, "
              f"first COMMIT at {commits[0]*1000:.2f}ms")
        print("both reads precede first commit =>",
              reads[-1] < commits[0] if len(reads) > 1 else "n/a")

    async with sf() as db:
        exp = (await db.execute(text(
            "SELECT expires_at FROM user_membership WHERE user_id=:u"), {"u": uid})).scalar_one()
    print(f"final expiry - base = {(exp-base).total_seconds()/86400:.1f} days (60 = both survived)")

    await async_engine.dispose()
    await sf.kw["bind"].dispose()
    eng = create_async_engine(SERVER_URL)
    async with eng.begin() as conn:
        await conn.execute(text(f"DROP DATABASE IF EXISTS `{SCRATCH}`"))
    await eng.dispose()


asyncio.run(main())
