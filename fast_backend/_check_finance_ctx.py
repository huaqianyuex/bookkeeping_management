"""验证 AI 财务上下文（排查「账单分析查不到数据」）

用法：
    python _check_finance_ctx.py [user_id]

打印 build_user_context / build_finance_block 的真实输出：
- 当月有账单时，上下文应出现非零收入/支出与 Top 分类；
- 当月无账单时，应显式标注「本月暂无任何记账记录」；
- 若这里查到数据、而对话仍答"没查到"，说明问题在调用链而非查询。
"""

import asyncio
import sys

from ai import context as ai_context
from config.db_config import AsyncSessionLocal


async def main() -> None:
    user_id = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    async with AsyncSessionLocal() as db:
        ctx = await ai_context.build_user_context(db, user_id)
        print(f"=== build_user_context(user_id={user_id}) ===")
        for key, value in ctx.items():
            print(f"{key}: {value}")

        print("\n=== build_finance_block（拼入对话 system 的内容）===")
        block = await ai_context.build_finance_block(db, user_id)
        print(block if block else "（空串：查询抛异常，检查数据库连接）")


if __name__ == "__main__":
    asyncio.run(main())
