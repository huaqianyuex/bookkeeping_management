"""Scenario C: two concurrent POST /api/admin/membership/grant for the same user.

crud/membership.py::grant_membership (lines 247/255/257) has the same
read-modify-write shape as redeem_code, so the claim says the two grants
collapse into one.
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
SCRATCH = "probe_grant_tmp"
head, _, query = BASE.partition("?")
prefix, _db = head.rsplit("/", 1)
SERVER_URL = prefix + "/"
SCRATCH_URL = f"{prefix}/{SCRATCH}" + (f"?{query}" if query else "")
os.environ["DATABASE_URL"] = SCRATCH_URL

from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import (  # noqa: E402
    AsyncSession, async_sessionmaker, create_async_engine,
)


async def main():
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

    sf = async_sessionmaker(create_async_engine(SCRATCH_URL), class_=AsyncSession,
                            expire_on_commit=False)

    from main import app
    from utils.security import create_access_token

    for i in range(3):
        async with sf() as db:
            await db.execute(text("INSERT INTO users (username,password,role,status) VALUES (:u,'x',1,1)"),
                             {"u": f"admin{i}"})
            admin_id = (await db.execute(text("SELECT id FROM users WHERE username=:u"),
                                         {"u": f"admin{i}"})).scalar_one()
            await db.execute(text("INSERT INTO users (username,password,role,status) VALUES (:u,'x',0,1)"),
                             {"u": f"target{i}"})
            target_id = (await db.execute(text("SELECT id FROM users WHERE username=:u"),
                                          {"u": f"target{i}"})).scalar_one()
            base = datetime.now() + timedelta(days=5)
            await db.execute(text(
                "INSERT INTO user_membership (user_id,tier,expires_at,source) VALUES (:u,1,:e,1)"),
                {"u": target_id, "e": base})
            await db.commit()

        h = {"Authorization": f"Bearer {create_access_token(str(admin_id))}"}
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://probe") as client:
            r = await asyncio.gather(
                client.post("/api/admin/membership/grant",
                            json={"userId": target_id, "days": 10}, headers=h),
                client.post("/api/admin/membership/grant",
                            json={"userId": target_id, "days": 10}, headers=h),
            )
        async with sf() as db:
            exp = (await db.execute(text(
                "SELECT expires_at FROM user_membership WHERE user_id=:u"), {"u": target_id})).scalar_one()
        gained = (exp - base).total_seconds() / 86400
        print(f"run{i}: statuses={[x.status_code for x in r]} days_gained={gained:.1f} "
              f"(20.0 expected from two +10 grants)")

    await sf.kw["bind"].dispose()
    eng = create_async_engine(SERVER_URL)
    async with eng.begin() as conn:
        await conn.execute(text(f"DROP DATABASE IF EXISTS `{SCRATCH}`"))
    await eng.dispose()


asyncio.run(main())
