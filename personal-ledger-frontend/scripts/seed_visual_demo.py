# -*- coding: utf-8 -*-
"""视觉验收演示数据种子：注册 uidemo2026 并通过用户级 API 造近 6 个月账单。
仅操作本脚本新建的账号，不触碰任何既有数据。"""
import asyncio
import random
import sys
import time

import aiohttp

BASE = "http://127.0.0.1:8000/api"
USERNAME = "uidemo2026"
PASSWORD = "123456"

random.seed(2026)


async def api(session, method, path, token=None, **kwargs):
    headers = kwargs.pop("headers", {})
    if token:
        headers["Authorization"] = f"Bearer {token}"
    async with session.request(method, f"{BASE}{path}", headers=headers, **kwargs) as resp:
        return await resp.json(content_type=None)


async def main():
    async with aiohttp.ClientSession() as session:
        # 1. 注册（已存在则忽略）
        reg = await api(session, "POST", "/user/register",
                        json={"username": USERNAME, "password": PASSWORD})
        print("register:", reg.get("code"), reg.get("message", ""))

        # 2. 登录
        login = await api(session, "POST", "/user/login",
                          json={"username": USERNAME, "password": PASSWORD})
        assert login["code"] == 200, login
        token = login["data"]["token"]
        print("login ok")

        # 3. 分类（幂等：先查再建）
        existing = await api(session, "GET", "/categories", token=token)
        have = {c["name"] for c in existing["data"]}
        want = [("餐饮", 0), ("交通", 0), ("购物", 0), ("娱乐", 0), ("居住", 0),
                ("工资", 1), ("理财", 1), ("兼职", 1)]
        for name, t in want:
            if name not in have:
                r = await api(session, "POST", "/categories", token=token,
                              json={"name": name, "type": t})
                print("category", name, r.get("code"))

        cats = (await api(session, "GET", "/categories", token=token))["data"]
        expense_ids = [c["id"] for c in cats if c["type"] == 0]
        income_ids = [c["id"] for c in cats if c["type"] == 1]

        # 4. 近 6 个月账单（幂等：跳过已有本月记录太多的账号无意义，直接查重备注标记）
        have_records = await api(session, "GET", "/records?page=1&size=100", token=token)
        marked = any("visualseed" in (r.get("remark") or "") for r in have_records["data"]["records"])
        if marked:
            print("records already seeded, skip")
            return

        # 月份基线：2026-05 .. 2026-10
        amounts_plan = [
            (5, 0, [(12.5, "visualseed 早餐"), (35.0, "visualseed 地铁"), (289.0, "visualseed 购物"), (66.0, "visualseed 电影")]),
            (5, 1, [(8500.0, "visualseed 月薪")]),
            (6, 0, [(23.8, "visualseed 午餐"), (45.0, "visualseed 打车"), (1299.0, "visualseed 外套"), (200.0, "visualseed KTV")]),
            (6, 1, [(8500.0, "visualseed 月薪"), (320.0, "visualseed 基金收益")]),
            (7, 0, [(18.0, "visualseed 晚餐"), (52.3, "visualseed 油费"), (456.0, "visualseed 鞋"), (150.0, "visualseed 密室")]),
            (7, 1, [(8500.0, "visualseed 月薪")]),
            (8, 0, [(30.0, "visualseed 面条"), (28.0, "visualseed 公交"), (899.0, "visualseed 键盘"), (88.0, "visualseed 桌游")]),
            (8, 1, [(8500.0, "visualseed 月薪"), (150.0, "visualseed 兼职")]),
            (9, 0, [(26.5, "visualseed 咖啡"), (66.0, "visualseed 高铁"), (1520.0, "visualseed 显示器"), (233.0, "visualseed 演唱会")]),
            (9, 1, [(8500.0, "visualseed 月薪"), (260.0, "visualseed 基金收益")]),
            (10, 0, [(42.0, "visualseed 火锅"), (15.0, "visualseed 单车"), (399.0, "visualseed 秋装"), (120.0, "visualseed 剧本杀")]),
            (10, 1, [(8500.0, "visualseed 月薪"), (80.0, "visualseed 兼职")]),
        ]
        count = 0
        for month, ctype, items in amounts_plan:
            pool = expense_ids if ctype == 0 else income_ids
            for i, (amount, remark) in enumerate(items):
                payload = {
                    "categoryId": pool[(month + i) % len(pool)],
                    "amount": amount,
                    "remark": remark,
                    "recordDate": f"2026-{month:02d}-{(3 + i * 6) % 27 + 1:02d}",
                }
                r = await api(session, "POST", "/records", token=token, json=payload)
                if r.get("code") == 200:
                    count += 1
                else:
                    print("record fail:", payload["recordDate"], r.get("message"))
        print(f"records created: {count}")


if __name__ == "__main__":
    t0 = time.time()
    try:
        asyncio.run(main())
    except AssertionError as e:
        print("FAILED:", e)
        sys.exit(1)
    print(f"done in {time.time() - t0:.1f}s")
