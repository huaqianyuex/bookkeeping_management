"""Independent verification probe for the claimed lost-update on user_membership.

Goes through the REAL HTTP surface (httpx ASGITransport -> main.app -> router ->
get_db session -> crud.membership.redeem_code) on a throwaway scratch DB, so the
claim's reachability through POST /api/membership/redeem is what gets tested, not
just a direct CRUD call.

Scenario A: user with an active membership row (now+10d); two DIFFERENT 30-day
            codes redeemed concurrently -> measure days actually gained.
Scenario B: user with NO membership row; two DIFFERENT codes concurrently
            -> observe HTTP status/body of the loser (IntegrityError path).
Mode `--barrier`: forces the exact claimed interleaving (both transactions read
            the membership row before either writes) by wrapping the real
            get_membership_row with an asyncio barrier. Used only if the natural
            race does not reproduce, to prove the window is exploitable.
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
SCRATCH = "probe_lost_update_http_tmp"
head, _, query = BASE.partition("?")
prefix, _db = head.rsplit("/", 1)
SERVER_URL = prefix + "/"
SCRATCH_URL = f"{prefix}/{SCRATCH}" + (f"?{query}" if query else "")
os.environ["DATABASE_URL"] = SCRATCH_URL
os.environ["JWT_SECRET_INSECURE_OK"] = "1"

from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import (  # noqa: E402
    AsyncSession, async_sessionmaker, create_async_engine,
)

BARRIER = "--barrier" in sys.argv


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


def sql_factory():
    return async_sessionmaker(create_async_engine(SCRATCH_URL), class_=AsyncSession,
                              expire_on_commit=False)


async def seed_active(sf, tag: str, existing_days: int = 10):
    """Active membership + 2 unused 30-day codes; returns (uid, base_expiry, codes)."""
    async with sf() as db:
        await db.execute(text(
            "INSERT INTO users (username, password, role, status) VALUES (:u, 'x', 0, 1)"
        ), {"u": tag})
        uid = (await db.execute(text("SELECT id FROM users WHERE username=:u"), {"u": tag})).scalar_one()
        base = datetime.now() + timedelta(days=existing_days)
        await db.execute(text(
            "INSERT INTO user_membership (user_id, tier, expires_at, source) VALUES (:u,1,:e,1)"
        ), {"u": uid, "e": base})
        codes = []
        for i, ch in enumerate("AB"):
            c = (tag.upper()[:6] + ch * 10)[:16]
            codes.append(c)
            await db.execute(text(
                "INSERT INTO membership_codes (code, days, status, batch_no) VALUES (:c,30,0,'p')"
            ), {"c": c})
        await db.commit()
    return uid, base, codes


async def main():
    await reset_db()
    from main import app
    from crud import membership as mc

    if BARRIER:
        real = mc.get_membership_row
        barrier = asyncio.Barrier(2) if hasattr(asyncio, "Barrier") else None

        async def gated(db, user_id):
            row = await real(db, user_id)
            if barrier is not None:
                try:
                    await barrier.wait()
                except Exception:
                    pass
            return row

        mc.get_membership_row = gated
        print(">>> barrier mode: forcing both readers past the membership SELECT")

    from utils.security import create_access_token

    sf = sql_factory()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://probe") as client:
        # ---------- Scenario A: active membership ----------
        print("=== A: two DIFFERENT 30d codes, same user, concurrently (active membership) ===")
        lost = 0
        for i in range(5):
            uid, base, codes = await seed_active(sf, f"p{i}")
            h = {"Authorization": f"Bearer {create_access_token(str(uid))}"}
            r = await asyncio.gather(
                client.post("/api/membership/redeem", json={"code": codes[0]}, headers=h),
                client.post("/api/membership/redeem", json={"code": codes[1]}, headers=h),
            )
            async with sf() as db:
                exp = (await db.execute(text(
                    "SELECT expires_at FROM user_membership WHERE user_id=:u"), {"u": uid})).scalar_one()
                consumed = (await db.execute(text(
                    "SELECT COUNT(*) FROM membership_codes WHERE status=1 AND used_by=:u"),
                    {"u": uid})).scalar_one()
            gained = (exp - base).total_seconds() / 86400
            print(f"  run{i}: statuses={[x.status_code for x in r]} consumed={consumed} "
                  f"days_gained={gained:.1f} (60.0 expected if both survive)")
            if consumed == 2 and abs(gained - 30) < 0.01:
                lost += 1
        print(f"  --> LOST UPDATE in {lost}/5 natural runs\n")

        # ---------- Scenario B: no membership row ----------
        print("=== B: two DIFFERENT codes, user with NO membership row ===")
        for i in range(3):
            uid, base, codes = await seed_active(sf, f"n{i}")
            async with sf() as db:
                await db.execute(text("DELETE FROM user_membership WHERE user_id=:u"), {"u": uid})
                await db.commit()
            h = {"Authorization": f"Bearer {create_access_token(str(uid))}"}
            r = await asyncio.gather(
                client.post("/api/membership/redeem", json={"code": codes[0]}, headers=h),
                client.post("/api/membership/redeem", json={"code": codes[1]}, headers=h),
            )
            print(f"  run{i}: " + " | ".join(
                f"{x.status_code} {x.text[:110]}" for x in r))

    await sf.kw["bind"].dispose() if hasattr(sf, "kw") else None
    eng = create_async_engine(SERVER_URL)
    async with eng.begin() as conn:
        await conn.execute(text(f"DROP DATABASE IF EXISTS `{SCRATCH}`"))
    await eng.dispose()
    print("\nscratch DB dropped")


asyncio.run(main())
