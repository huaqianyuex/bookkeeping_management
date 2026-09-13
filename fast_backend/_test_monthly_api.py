"""一次性测试脚本：/api/statistics/monthly 接口功能测试

- 用 aiosqlite 内存库依赖覆盖 get_db，不动真实 MySQL；
- 走真实 get_current_user（真实 JWT 签发/解码），鉴权场景端到端；
- 另附 CRUD 层直测，验证数据层逻辑（软删过滤、半开区间、12 月边界）。
"""

import asyncio
from decimal import Decimal

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import crud.statistics as crud_stats
from main import app as real_app  # 真实 app（含全部路由与异常处理器）
from models.base import Base
from models.category import Category
from models.record import Record
from models.user import User
from utils.security import create_access_token

engine = create_async_engine("sqlite+aiosqlite:///:memory:")
TestSession = async_sessionmaker(engine, expire_on_commit=False)


async def override_get_db():
    async with TestSession() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


real_app.dependency_overrides[__import__("config.db_config", fromlist=["get_db"]).get_db] = override_get_db

client = TestClient(real_app, raise_server_exceptions=False)

# ---- 造数据：user 1 有收支记录（含软删、跨月），user 2 无记录 ----
CATS = [
    Category(id=1, name="餐饮", type=0),
    Category(id=2, name="工资", type=1),
]
RECORDS = [
    # 2026-05 正常支出
    Record(id=1, user_id=1, category_id=1, type=0, amount=Decimal("35.50"), date=__import__("datetime").date(2026, 5, 10), status=1),
    Record(id=2, user_id=1, category_id=1, type=0, amount=Decimal("64.50"), date=__import__("datetime").date(2026, 5, 20), status=1),
    # 2026-05 收入
    Record(id=3, user_id=1, category_id=2, type=1, amount=Decimal("8000.00"), date=__import__("datetime").date(2026, 5, 1), status=1),
    # 2026-05 软删（不应计入）
    Record(id=4, user_id=1, category_id=1, type=0, amount=Decimal("999.99"), date=__import__("datetime").date(2026, 5, 15), status=0),
    # 2026-06 跨月（不应计入 5 月）
    Record(id=5, user_id=1, category_id=1, type=0, amount=Decimal("123.45"), date=__import__("datetime").date(2026, 6, 1), status=1),
    # 其他用户
    Record(id=6, user_id=2, category_id=1, type=0, amount=Decimal("77.77"), date=__import__("datetime").date(2026, 5, 5), status=1),
]


async def seed():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with TestSession() as s:
        s.add_all(CATS)
        s.add_all(RECORDS)
        s.add(User(id=1, username="alice", password="x"))
        s.add(User(id=2, username="bob", password="x"))
        await s.commit()


asyncio.run(seed())

TOK1 = create_access_token(1)
TOK2 = create_access_token(2)
HDR = {"Authorization": f"Bearer {TOK1}"}

results = []


def case(name, expect, actual_desc, actual):
    ok = "✅符合预期" if actual_desc == expect else "❌"
    results.append((name, expect, actual_desc, actual, ok))
    print(f"\n=== {name}\n  期待: {expect}\n  实际: {actual_desc}\n  响应体: {actual}")


def run(name, expect, headers=None, params=None, url="/api/statistics/monthly"):
    r = client.get(url, headers=headers, params=params)
    try:
        body = r.json()
    except Exception:
        body = r.text
    desc = f"HTTP {r.status_code}, code={body.get('code') if isinstance(body, dict) else '-'}"
    case(name, expect, desc, body)


print("#" * 30, "接口层测试（真实路由 + SQLite 覆盖）", "#" * 30)

run("T1 正常参数 year=2026&month=5（5月支出100/收入8000）",
    "HTTP 200, code=200, data={year:2026,month:5,totalIncome:8000.0,totalExpense:100.0,balance:7900.0}",
    HDR, {"year": 2026, "month": 5})

run("T2 无 Authorization 头（未登录）", "HTTP 401, code=401 无效令牌", None, {"year": 2026, "month": 5})

run("T3 伪造/乱码 token", "HTTP 401, code=401",
    {"Authorization": "Bearer garbage.token.here"}, {"year": 2026, "month": 5})

run("T4 过期 token", "HTTP 401, code=401",
    {"Authorization": "Bearer " + create_access_token(1, expires_delta=__import__("datetime").timedelta(seconds=-10))},
    {"year": 2026, "month": 5})

import jwt as pyjwt
from config.settings import JWT_SECRET
bad_sub = pyjwt.encode({"sub": "not-a-number", "exp": 9999999999}, JWT_SECRET, algorithm="HS256")
run("T5 有效签名但 sub 非数字", "HTTP 401, code=401（应视为无效令牌）",
    {"Authorization": f"Bearer {bad_sub}"}, {"year": 2026, "month": 5})

run("T6 缺 year/month 必填参数", "HTTP 400/422 参数错误", HDR, None)

run("T7 month=13（越界月份）", "HTTP 400/422 参数校验失败", HDR, {"year": 2026, "month": 13})

run("T8 month=0", "HTTP 400/422", HDR, {"year": 2026, "month": 0})

run("T9 year=abc 类型错误", "HTTP 400/422 类型错误", HDR, {"year": "abc", "month": 5})

run("T10 负数 month=-1", "HTTP 400/422", HDR, {"year": 2026, "month": -1})

run("T11 12月边界 year=2026&month=12", "HTTP 200 正常统计（不因月份+1报错）", HDR, {"year": 2026, "month": 12})

run("T12 已登录但无任何记录的用户", "HTTP 200 全 0", {"Authorization": f"Bearer {TOK2}"}, {"year": 2026, "month": 5})

run("T13 Bearer 前缀缺失（纯 token）", "HTTP 401 或按 token 解析失败", {"Authorization": TOK1}, {"year": 2026, "month": 5})

run("T14 无权访问他人数据？传 user_id 参数试图越权", "接口不接收 user_id，无法越权（应仍按 token 的 user=1 返回）",
    HDR, {"year": 2026, "month": 5, "user_id": 2})

print("\n" + "#" * 30, "CRUD 层直测（验证数据层逻辑是否正确）", "#" * 30)


async def crud_checks():
    async with TestSession() as s:
        inc, exp = await crud_stats.get_summary(s, 1, 2026, 5)
        print(f"C1 2026-05: income={inc} expense={exp} （期待 income=8000.00 expense=100.00，软删与6月不计）")
        inc12, exp12 = await crud_stats.get_summary(s, 1, 2026, 12)
        print(f"C2 2026-12（12月边界）: income={inc12} expense={exp12}（期待 0.00/0.00 不报错）")
        inc0, exp0 = await crud_stats.get_summary(s, 2, 2026, 5)
        print(f"C3 user2: income={inc0} expense={exp0}（期待 0.00/77.77）")
        try:
            await crud_stats.get_summary(s, 1, 2026, 13)
            print("C4 month=13: 未报错（⚠️ 数据层也不校验月份范围）")
        except ValueError as e:
            print(f"C4 month=13: ValueError({e})")


asyncio.run(crud_checks())

print("\n" + "#" * 30, "汇总", "#" * 30)
for name, expect, actual_desc, _, ok in results:
    print(f"[{ok}] {name}: {actual_desc}")
