"""Independent verification probe for the claim:

  crud/membership.py:180  void_code() read-check-write has no row lock, so a
  concurrent redeem (status 0->1) can be overwritten by the void (status->2).

This probe uses the REAL functions (`crud.membership.redeem_code` and
`crud.membership.void_code`) on a scratch MySQL DB.

Phase 1 (deterministic): widen the window with a third transaction H that holds an
X-lock on the victim user's `user_membership` row.  The real `redeem_code` acquires
the code row X-lock via SELECT ... FOR UPDATE, then blocks inside its own commit on
H's lock.  While it is blocked, the real `void_code` runs: its plain SELECT still
sees status=0 and its UPDATE blocks on the code row lock.  H then commits, redeem
commits, and the void's UPDATE is applied afterwards.

Phase 2 (natural): run the two real functions concurrently with asyncio.gather on
fresh codes, N trials, and count how often void_code reports success while the row
ends up status=2/used_by set.

All SQL issued by the void session is captured via a before_cursor_execute listener.
"""

import asyncio
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

PROJ = Path(r"E:\一些毕设探索\Accounting Management System_fastapi\fast_backend -fwature-expansion-version")
sys.path.insert(0, str(PROJ))
os.chdir(PROJ)

from dotenv import load_dotenv  # noqa: E402

load_dotenv(PROJ / ".env")
BASE = os.environ["DATABASE_URL"]
SCRATCH = "verify_void_race_tmp"
head, _, query = BASE.partition("?")
prefix, _db = head.rsplit("/", 1)
SERVER_URL = prefix + "/"
SCRATCH_URL = f"{prefix}/{SCRATCH}" + (f"?{query}" if query else "")
os.environ["DATABASE_URL"] = SCRATCH_URL
os.environ.setdefault("JWT_SECRET_INSECURE_OK", "1")

from sqlalchemy import event, text  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine  # noqa: E402

CODE1 = "VOIDRACE00000001"
CODE2 = "VOIDRACE00000002"
CODE3 = "VOIDRACE00000003"


async def setup():
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


async def teardown():
    eng = create_async_engine(SERVER_URL)
    async with eng.begin() as conn:
        await conn.execute(text(f"DROP DATABASE IF EXISTS `{SCRATCH}`"))
    await eng.dispose()


async def phase1(sf, make_code):
    """Deterministic: real redeem_code held mid-commit + real void_code."""
    from crud import membership as mc

    async with sf() as db:
        await db.execute(text(
            "INSERT INTO users (username, password, role, status) VALUES ('p1','x',0,1)"))
        uid = (await db.execute(text("SELECT id FROM users WHERE username='p1'"))).scalar_one()
        code_id = await make_code(db, CODE1)
        # victim already has a live membership so redeem_code takes the UPDATE path
        await db.execute(text(
            "INSERT INTO user_membership (user_id, tier, expires_at, source, created_at, updated_at)"
            " VALUES (:u, 1, :e, 0, NOW(), NOW())"),
            {"u": uid, "e": datetime.now() + timedelta(days=10)})
        await db.commit()

    h = sf()      # holds an X-lock on the victim's membership row (uncommitted)
    a = sf()      # real redeem_code
    void_sql: list[str] = []

    b_eng = create_async_engine(SCRATCH_URL)
    b = async_sessionmaker(b_eng, class_=AsyncSession, expire_on_commit=False)()
    real_commit = b.commit

    @event.listens_for(b_eng.sync_engine, "before_cursor_execute")
    def _cap(conn, cursor, statement, parameters, context, executemany):  # noqa: ANN001
        void_sql.append(statement)

    await h.execute(text("SELECT * FROM user_membership WHERE user_id=:u FOR UPDATE"), {"u": uid})

    redeem_task = asyncio.create_task(mc.redeem_code(a, uid, CODE1))
    await asyncio.sleep(1.0)          # redeem: code FOR UPDATE ok, now blocked on H

    void_task = asyncio.create_task(mc.void_code(b, code_id))
    await asyncio.sleep(1.0)          # void: plain SELECT saw status=0, UPDATE blocked

    await h.commit()                  # release -> redeem finishes, then void's UPDATE lands
    await asyncio.sleep(1.0)
    redeem_res = await redeem_task
    void_res = await void_task
    await h.close()

    async with sf() as db:
        final = (await db.execute(text(
            "SELECT status, used_by, used_at FROM membership_codes WHERE id=:i"),
            {"i": code_id})).first()
        exp = (await db.execute(text(
            "SELECT tier, expires_at FROM user_membership WHERE user_id=:u"), {"u": uid})).first()

    print("=== PHASE 1 (deterministic, real redeem_code + real void_code) ===")
    print("redeem_code(...)  ->", redeem_res[0], "|", redeem_res[1])
    print("void_code(...)    ->", void_res)
    print("final row         -> status=%s used_by=%s used_at=%s" % tuple(
        str(v) for v in final))
    print("membership row    -> tier=%s expires_at=%s" % (exp[0], exp[1]))
    print("void session SQL  ->")
    for s in void_sql:
        print("   ", " ".join(s.split())[:160])

    await b.close()
    await a.close()
    await b_eng.dispose()

    bug = (void_res[0] is True) and (final[0] == 2) and (final[1] is not None)
    print("BUG OBSERVED" if bug else "no bug in this run")
    return bug


async def phase2(sf, make_code, trials=25):
    """Natural: both real functions on the same code, started together."""
    from crud import membership as mc

    async with sf() as db:
        await db.execute(text(
            "INSERT INTO users (username, password, role, status) VALUES ('p2','x',0,1)"))
        uid = (await db.execute(text("SELECT id FROM users WHERE username='p2'"))).scalar_one()
        await db.execute(text(
            "INSERT INTO user_membership (user_id, tier, expires_at, source, created_at, updated_at)"
            " VALUES (:u, 1, :e, 0, NOW(), NOW())"),
            {"u": uid, "e": datetime.now() + timedelta(days=10)})
        ids = []
        for i in range(trials):
            ids.append(await make_code(db, f"VOIDNAT{i:08d}"))
        await db.commit()

    hits = 0
    for i, cid in enumerate(ids):
        code = f"VOIDNAT{i:08d}"

        async def do_redeem():
            async with sf() as db:
                return await mc.redeem_code(db, uid, code)

        async def do_void():
            async with sf() as db:
                return await mc.void_code(db, cid)

        r_res, v_res = await asyncio.gather(do_redeem(), do_void())
        async with sf() as db:
            final = (await db.execute(text(
                "SELECT status, used_by FROM membership_codes WHERE id=:i"), {"i": cid})).first()
        if v_res[0] is True and final[0] == 2 and final[1] is not None:
            hits += 1
            print(f"  [trial {i}] redeem={r_res[0]} void={v_res} final=(status={final[0]},"
                  f" used_by={final[1]})  <-- void overwrote a used code")
    print("=== PHASE 2 (natural concurrency) ===")
    print(f"void overwrote a concurrently-redeemed code in {hits}/{trials} trials")
    return hits


async def main():
    await setup()
    sf = async_sessionmaker(create_async_engine(SCRATCH_URL), class_=AsyncSession,
                            expire_on_commit=False)

    from models.membership import MembershipCode

    async def make_code(db, code):
        db.add(MembershipCode(code=code, days=30, status=0, batch_no="probe"))
        await db.commit()
        return (await db.execute(text(
            "SELECT id FROM membership_codes WHERE code=:c"), {"c": code})).scalar_one()

    try:
        p1 = await phase1(sf, make_code)
        p2 = await phase2(sf, make_code)
        print()
        print(f"RESULT: deterministic={p1}  natural_hits={p2}")
    finally:
        await teardown()


asyncio.run(main())
