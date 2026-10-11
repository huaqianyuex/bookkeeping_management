"""临时端到端验收：在独立 scratch 库上跑会员模块真实流程，结束即 DROP（不碰 bookkeeping_fastapi）。

覆盖单测无法覆盖的 MySQL 特有路径：
- ai_usage_daily 的 ON DUPLICATE KEY UPDATE 累加；
- membership_codes 的 SELECT ... FOR UPDATE 行锁（并发同码仅一次成功）；
- generate_codes 的 IN 回读（created_at 由 DDL 填充）。

DB 侧准备/断言一律使用独立 engine（app 的 engine 归 TestClient 的事件循环所有，
跨 loop 复用连接会报 "attached to a different loop"）。
"""

import asyncio
import json
import os
import sys
from datetime import date, datetime, timedelta

# 与 tests/conftest.py 同口径：把项目根目录加入 sys.path（脚本可直接运行，不必装成包）
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()   # 先读 .env，才能拿到真实 DATABASE_URL 再替换库名
BASE_URL = os.environ["DATABASE_URL"]
SCRATCH = "bookkeeping_fastapi_verify_tmp"
_head, _, _query = BASE_URL.partition("?")
_prefix, _dbname = _head.rsplit("/", 1)
SERVER_URL = _prefix + "/"
SCRATCH_URL = f"{_prefix}/{SCRATCH}" + (f"?{_query}" if _query else "")
os.environ["DATABASE_URL"] = SCRATCH_URL

from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine  # noqa: E402

results: list[str] = []
USERNAME = "verifyuser"


def check(name: str, cond: bool, extra: str = "") -> None:
    results.append(("PASS" if cond else "FAIL") + f"  {name}" + (f"  [{extra}]" if extra else ""))
    if not cond:
        print("!! FAIL:", name, extra)


def run_db(factory):
    """在独立 engine/loop 中执行一段 DB 逻辑（返回结果），避免跨 loop 复用连接池。"""
    async def runner():
        engine = create_async_engine(SCRATCH_URL)
        session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        try:
            return await factory(session_factory)
        finally:
            await engine.dispose()
    return asyncio.run(runner())


async def _scalar(session_factory, sql: str, params: dict | None = None):
    """取单值的小工具（供 run_db(lambda sf: _scalar(...)) 使用）"""
    async with session_factory() as db:
        return (await db.execute(text(sql), params or {})).scalar_one()


async def create_schema():
    engine = create_async_engine(SERVER_URL)
    async with engine.begin() as conn:
        await conn.execute(text(f"DROP DATABASE IF EXISTS `{SCRATCH}`"))
        await conn.execute(text(f"CREATE DATABASE `{SCRATCH}` CHARACTER SET utf8mb4"))
    await engine.dispose()


async def create_tables():
    from models.base import Base
    import models.user, models.category, models.record, models.chat, models.bookkeeping, models.membership  # noqa
    engine = create_async_engine(SCRATCH_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()


async def drop_schema():
    from config.db_config import async_engine
    await async_engine.dispose()
    engine = create_async_engine(SERVER_URL)
    async with engine.begin() as conn:
        await conn.execute(text(f"DROP DATABASE IF EXISTS `{SCRATCH}`"))
    await engine.dispose()


def main():
    from fastapi.testclient import TestClient
    from main import app

    with TestClient(app) as c:
        # ── 1. 注册 / 登录 ─────────────────────────────────────────────
        r = c.post("/api/user/register", json={"username": USERNAME, "password": "123456"})
        check("register 200", r.status_code == 200, r.text[:160])
        r = c.post("/api/user/login", json={"username": USERNAME, "password": "123456"})
        check("login 200", r.status_code == 200, r.text[:160])
        token = r.json()["data"]["token"]
        h = {"Authorization": f"Bearer {token}"}

        # ── 2. /status 免费档 ──────────────────────────────────────────
        r = c.get("/api/membership/status", headers=h)
        d = r.json()["data"]
        check("status 200 + code=200", r.status_code == 200 and r.json()["code"] == 200)
        check("status free tier", d["tier"] == 0 and d["tierName"] == "免费版" and d["expiresAt"] is None)
        check("status benefits camelCase", d["benefits"] == {
            "dailyChat": 10, "concurrency": 1, "dailyAnalyze": 2,
            "dailyBookkeeping": 5, "premiumModel": False,
        }, json.dumps(d["benefits"], ensure_ascii=False))
        check("status usage limits", d["usage"]["chat"] == {"used": 0, "limit": 10}
              and d["usage"]["analyze"] == {"used": 0, "limit": 2}
              and d["usage"]["bookkeeping"] == {"used": 0, "limit": 5})

        async def get_uid(session_factory):
            async with session_factory() as db:
                return (await db.execute(
                    text("SELECT id FROM users WHERE username=:u"), {"u": USERNAME}
                )).scalar_one()

        uid = run_db(get_uid)

        # ── 3. 用量 upsert（MySQL ON DUPLICATE KEY UPDATE）─────────────
        async def usage_flow(session_factory):
            from config.settings import MEMBERSHIP_PLANS
            from crud import membership as mc

            async with session_factory() as db:
                for _ in range(3):
                    await mc.incr_usage(db, uid, "chat")
                    await db.commit()
                ok, used, limit = await mc.check_quota(db, uid, MEMBERSHIP_PLANS[0], "chat")
                row_tomorrow = await mc.get_usage_row(db, uid, date.today() + timedelta(days=1))
                return ok, used, limit, row_tomorrow

        ok, used, limit, row_tomorrow = run_db(usage_flow)
        check("usage upsert 累加到 3", used == 3 and limit == 10 and ok is True, f"used={used}")
        check("usage 跨天无行（自然归零）", row_tomorrow is None)

        # ── 4. 管理端：提权 + 生成兑换码 ───────────────────────────────
        async def promote(session_factory):
            async with session_factory() as db:
                await db.execute(text("UPDATE users SET role=1 WHERE id=:i"), {"i": uid})
                await db.commit()

        run_db(promote)
        r = c.post("/api/user/login", json={"username": USERNAME, "password": "123456"})
        ah = {"Authorization": f"Bearer {r.json()['data']['token']}"}

        r = c.post("/api/admin/membership/codes", json={"count": 3, "days": 30}, headers=ah)
        body = r.json()
        check("generate 200 + message", r.status_code == 200 and body["message"] == "已生成 3 张兑换码",
              body.get("message"))
        codes = body["data"]["codes"]
        check("generate 3 codes, 16位/无0O1I/status=0",
              len(codes) == 3 and all(len(x["code"]) == 16 for x in codes)
              and all(not (set(x["code"]) & set("0O1I")) for x in codes)
              and all(x["status"] == 0 for x in codes))
        check("generate createdAt 由库回读", all(x["createdAt"] for x in codes), str(codes[0]))
        check("generate camelCase 键", set(codes[0]) == {"id", "code", "days", "status", "batchNo",
                                                        "usedBy", "usedAt", "createdAt"})

        r = c.get("/api/admin/membership/codes?page=1&size=2&status=0", headers=ah)
        page = r.json()["data"]
        check("codes 列表分页结构", r.status_code == 200 and set(page) == {"records", "total", "pages",
              "current", "size"} and page["total"] == 3 and page["pages"] == 2 and len(page["records"]) == 2,
              json.dumps({k: v for k, v in page.items() if k != "records"}))
        check("codes 列表 id 倒序", page["records"][0]["id"] > page["records"][1]["id"])
        r = c.get("/api/admin/membership/codes?status=9", headers=ah)
        check("codes status 非法 -> 400 参数错误", r.status_code == 400 and r.json()["message"] == "参数错误")

        # ── 5. 作废：成功 -> 重复作废 400 ──────────────────────────────
        last_id = codes[-1]["id"]
        r = c.put(f"/api/admin/membership/codes/{last_id}/void", headers=ah)
        check("void 200 + 已作废", r.status_code == 200 and r.json()["message"] == "已作废", r.text[:120])
        r = c.put(f"/api/admin/membership/codes/{last_id}/void", headers=ah)
        check("void 重复拒绝", r.status_code == 400 and r.json()["message"] == "该兑换码已作废", r.text[:160])
        r = c.post("/api/membership/redeem", json={"code": codes[-1]["code"]}, headers=ah)
        check("作废码不可兑换", r.status_code == 400 and r.json()["message"] == "该兑换码已作废", r.text[:160])
        r = c.post("/api/membership/redeem", json={"code": "ZZZZZZZZZZZZZZZZ"}, headers=ah)
        check("不存在的码 400", r.status_code == 400 and r.json()["message"] == "兑换码不存在", r.text[:160])

        # ── 6. 兑换开通 + 叠加续费 + 重复核销 ─────────────────────────
        spaced = f"  {codes[0]['code'][:4]}-{codes[0]['code'][4:]}  "
        r = c.post("/api/membership/redeem", json={"code": spaced}, headers=ah)
        b = r.json()
        check("redeem 成功（含空格/连字符归一化）",
              r.status_code == 200 and b["message"] == "兑换成功，会员已延长 30 天", r.text[:160])
        exp1 = b["data"]["expiresAt"]
        check("redeem data={tier,expiresAt}", set(b["data"]) == {"tier", "expiresAt"} and b["data"]["tier"] == 1)

        r = c.get("/api/membership/status", headers=ah)
        d = r.json()["data"]
        check("兑换后 status=tier1", d["tier"] == 1 and d["tierName"] == "会员" and d["expiresAt"] == exp1)
        check("兑换后 benefits 会员档", d["benefits"]["dailyChat"] == 100 and d["benefits"]["premiumModel"] is True)
        check("兑换后用量延续今日计数", d["usage"]["chat"] == {"used": 3, "limit": 100}, str(d["usage"]["chat"]))

        r = c.post("/api/membership/redeem", json={"code": codes[0]["code"]}, headers=ah)
        check("同码重复核销 400", r.status_code == 400 and r.json()["message"] == "该兑换码已被使用", r.text[:160])

        r = c.post("/api/membership/redeem", json={"code": codes[1]["code"]}, headers=ah)
        exp2 = r.json()["data"]["expiresAt"]
        delta_days = (datetime.fromisoformat(exp2) - datetime.fromisoformat(exp1)).total_seconds() / 86400
        check("续费从现有到期叠加 30 天（不吞剩余天数）", abs(delta_days - 30) < 0.01, f"delta={delta_days}")

        # ── 7. 并发同码仅一次成功（SELECT ... FOR UPDATE）─────────────
        r = c.post("/api/admin/membership/codes", json={"count": 1, "days": 7}, headers=ah)
        race_code = r.json()["data"]["codes"][0]["code"]

        async def race(session_factory):
            from crud import membership as mc

            async def one():
                async with session_factory() as db:
                    return (await mc.redeem_code(db, uid, race_code))[0]

            return await asyncio.gather(one(), one())

        outcomes = run_db(race)
        check("并发同码仅一次成功", sum(1 for x in outcomes if x) == 1, f"outcomes={outcomes}")

        # ── 8. 管理端开通 / 404 / 会员标识注入 ────────────────────────
        r = c.post("/api/admin/membership/grant", json={"userId": uid, "days": 10}, headers=ah)
        b = r.json()
        check("grant 200 + 文案 + data 形状",
              r.status_code == 200 and b["message"] == f"已为用户 {uid} 开通/延期 10 天"
              and set(b["data"]) == {"tier", "expiresAt"}, r.text[:160])
        r = c.post("/api/admin/membership/grant", json={"userId": 999999, "days": 10}, headers=ah)
        check("grant 用户不存在 404", r.status_code == 404 and r.json()["message"] == "用户不存在", r.text[:120])

        r = c.get("/api/user/info", headers=ah)
        d = r.json()["data"]
        check("GET /user/info 注入会员标识", d.get("membership_tier") == 1 and d.get("membership_expires_at"),
              json.dumps({k: str(v) for k, v in d.items() if k.startswith("membership")}, ensure_ascii=False))

        r = c.get("/api/admin/users?page=1&size=10", headers=ah)
        rec = r.json()["data"]["records"][0]
        check("GET /admin/users 注入会员标识", rec.get("membership_tier") == 1 and rec.get("membership_expires_at"),
              json.dumps({k: str(v) for k, v in rec.items() if k.startswith("membership")}, ensure_ascii=False))

        # ── 9. AI 闸门：真实 DB 上超额 -> 429 裸 JSON ─────────────────
        async def fill_quota(session_factory):
            from config.settings import MEMBERSHIP_PLANS
            from crud import membership as mc
            async with session_factory() as db:
                for _ in range(MEMBERSHIP_PLANS[1]["daily_analyze"]):
                    await mc.incr_usage(db, uid, "analyze")
                await db.commit()

        run_db(fill_quota)
        r = c.post("/api/ai/analyze/expenses", json={}, headers=ah)
        body = r.json()
        check("AI 闸门超额 -> 429 裸 JSON QUOTA_EXCEEDED",
              r.status_code == 429 and body.get("code") == "QUOTA_EXCEEDED"
              and "data" not in body and "已用完" in body.get("error", ""), r.text[:220])

        r = c.get("/api/membership/status", headers=ah)
        check("status.usage 反映真实计数", r.json()["data"]["usage"]["analyze"] == {"used": 30, "limit": 30},
              str(r.json()["data"]["usage"]["analyze"]))

        # ── 10. 并发原子性（独立复核发现的三类竞态；纯 DB 层，不触发 LLM）──
        # 10.1 配额「校验+自增」必须原子：20 并发抢 3 个额度
        async def quota_burst(session_factory):
            from config.settings import MEMBERSHIP_PLANS
            from crud import membership as mc

            plan = dict(MEMBERSHIP_PLANS[0])
            plan["daily_bookkeeping"] = 3
            async with session_factory() as db:
                await db.execute(text("DELETE FROM ai_usage_daily WHERE user_id=:i"), {"i": uid})
                await db.commit()

            async def one():
                async with session_factory() as db:
                    return (await mc.consume_quota(db, uid, plan, "bookkeeping"))[0]

            admitted = await asyncio.gather(*[one() for _ in range(20)])
            async with session_factory() as db:
                final = (await db.execute(
                    text("SELECT bookkeeping_count FROM ai_usage_daily WHERE user_id=:i"),
                    {"i": uid})).scalar_one()
            return sum(1 for x in admitted if x), final

        admitted_n, final_count = run_db(quota_burst)
        check("并发 20 抢 3 额度：恰好 3 次准入且计数不超限",
              admitted_n == 3 and final_count == 3, f"admitted={admitted_n} count={final_count}")

        # 10.2 两个不同兑换码并发核销：天数必须都保住（各 30 天）
        r = c.post("/api/admin/membership/codes", json={"count": 2, "days": 30}, headers=ah)
        two = [x["code"] for x in r.json()["data"]["codes"]]

        async def concurrent_redeem(session_factory):
            from crud import membership as mc

            async with session_factory() as db:
                before = (await db.execute(
                    text("SELECT expires_at FROM user_membership WHERE user_id=:i"),
                    {"i": uid})).scalar_one()

            async def one(code):
                async with session_factory() as db:
                    return (await mc.redeem_code(db, uid, code))[0]

            outcomes = await asyncio.gather(one(two[0]), one(two[1]))
            async with session_factory() as db:
                after = (await db.execute(
                    text("SELECT expires_at FROM user_membership WHERE user_id=:i"),
                    {"i": uid})).scalar_one()
            return outcomes, (after - before).total_seconds() / 86400

        outcomes, gained = run_db(concurrent_redeem)
        check("两码并发核销均成功且天数叠加 60 天（无丢失更新）",
              all(outcomes) and abs(gained - 60) < 0.05, f"outcomes={outcomes} gained={gained}")

        # 10.3 并发首次开通（该用户尚无会员行）：不撞唯一键、不丢天数
        c.post("/api/user/register", json={"username": "verifyuser2", "password": "123456"})
        uid2 = run_db(lambda sf: _scalar(sf, "SELECT id FROM users WHERE username='verifyuser2'"))

        async def concurrent_first_grant(session_factory):
            from crud import membership as mc

            async def one():
                async with session_factory() as db:
                    return await mc.grant_membership(db, uid2, 30)

            results_grant = await asyncio.gather(*[one() for _ in range(6)])
            async with session_factory() as db:
                rows = (await db.execute(
                    text("SELECT COUNT(*), MAX(expires_at) FROM user_membership WHERE user_id=:i"),
                    {"i": uid2})).one()
            return results_grant, rows[0], rows[1]

        grant_results, row_count, max_exp = run_db(concurrent_first_grant)
        gained2 = (max_exp - datetime.now()).total_seconds() / 86400
        check("并发 6 次首次开通：单行、无异常、天数累计 180 天",
              row_count == 1 and all(x is not None for x in grant_results) and abs(gained2 - 180) < 0.1,
              f"rows={row_count} gained={gained2:.1f}")

        # 10.4 并发 作废 vs 核销：终态必须自洽（不能「已作废 + 已核销」）
        r = c.post("/api/admin/membership/codes", json={"count": 1, "days": 5}, headers=ah)
        race2 = r.json()["data"]["codes"][0]

        async def void_vs_redeem(session_factory):
            from crud import membership as mc

            async def do_void():
                async with session_factory() as db:
                    return await mc.void_code(db, race2["id"])

            async def do_redeem():
                async with session_factory() as db:
                    return await mc.redeem_code(db, uid, race2["code"])

            await asyncio.gather(do_void(), do_redeem())
            async with session_factory() as db:
                return (await db.execute(
                    text("SELECT status, used_by FROM membership_codes WHERE id=:i"),
                    {"i": race2["id"]})).one()

        status_final, used_by_final = run_db(void_vs_redeem)
        consistent = (status_final == 2 and used_by_final is None) or \
                     (status_final == 1 and used_by_final == uid)
        check("并发 作废/核销 终态自洽", consistent, f"status={status_final} used_by={used_by_final}")

        # ── 11. 真实流式链路：闸门内 commit 后，生成器仍能复用同一 session ──
        # 只替换 LLM 调用（chat_stream），闸门 / 并发槽 / 落库 / SSE 全部走真实代码
        from routers import ai as ai_router

        # 签名镜像 ai.chat_chain.chat_stream：premium / user_id 两个可选参数
        async def fake_stream(messages, premium=False, user_id=None):
            yield "你好"
            yield "，已记下"

        ai_router.chat_chain.chat_stream = fake_stream

        async def chat_count(session_factory):
            return await _scalar(
                session_factory,
                "SELECT chat_count FROM ai_usage_daily WHERE user_id=:i AND usage_date=CURDATE()",
                {"i": uid},
            )

        before_chat = run_db(chat_count)
        sid = c.post("/api/ai/sessions", json={}, headers=ah).json()["id"]
        r = c.post("/api/ai/chat/stream", json={"sessionId": sid, "message": "你好"}, headers=ah)
        check("流式：HTTP 200 + SSE content/done 事件",
              r.status_code == 200 and '"type": "content"' in r.text and '"type": "done"' in r.text,
              r.text[:200])

        msgs = c.get(f"/api/ai/sessions/{sid}/messages", headers=ah).json()
        check("流式：user/assistant 两条消息落库（闸门 commit 后 session 复用正常）",
              [m["role"] for m in msgs] == ["user", "assistant"], str(msgs)[:200])

        after_chat = run_db(chat_count)
        check("流式：闸门真实计数 +1", after_chat == before_chat + 1,
              f"{before_chat} -> {after_chat}")

    print()
    for line in results:
        print(line)
    failed = [x for x in results if x.startswith("FAIL")]
    print(f"\n== {len(results) - len(failed)}/{len(results)} passed ==")
    return 1 if failed else 0


if __name__ == "__main__":
    exit_code = 2
    try:
        asyncio.run(create_schema())
        asyncio.run(create_tables())
        exit_code = main()
    except Exception:
        import traceback
        traceback.print_exc()
    finally:
        try:
            asyncio.run(drop_schema())
            print("scratch 库已清理")
        except Exception:
            import traceback
            traceback.print_exc()
    # aiomysql 连接在解释器收尾阶段的 __del__ 会抛 "Event loop is closed"（无害噪音），
    # 会污染进程退出码；显式 flush 后直接退出，保证 CI/人工看退出码可信。
    sys.stdout.flush()
    os._exit(exit_code)
