"""pytest 全局夹具

- 把 fast_backend 根目录加入 sys.path（测试包导入用）；
- 在导入任何应用模块前设置安全校验所需的环境变量
  （config.settings 在 import 时即校验 JWT_SECRET）。
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ["JWT_SECRET"] = "unit-test-secret-key-0123456789abcdef"
os.environ["JWT_SECRET_INSECURE_OK"] = "1"
os.environ.setdefault("DATABASE_URL", "mysql+aiomysql://root:root@127.0.0.1:3306/unit_test?charset=utf8mb4")


@pytest.fixture(autouse=True)
def _reset_in_memory_throttles():
    """用例间隔离：登录限流/语音限流/AI 并发槽/充值防刷是进程内存态，
    多个用例共用同一 test client IP，不清理会互相污染出假 429/锁死。"""
    def _clear():
        from utils import ai_concurrency, throttle
        throttle.login_throttle._buckets.clear()
        throttle.login_throttle._locked.clear()
        throttle.login_ip_throttle._buckets.clear()
        throttle.login_ip_throttle._locked.clear()
        throttle.voice_rate_limiter._hits.clear()
        ai_concurrency._slots.clear()
        # AI 路由模块级滑动窗口限流器（FAQ 检索 P0-4 / 语音转写 P1-7 /
        # 记账预览限流）也是进程内存态，同一测试用户会跨用例累计命中，
        # 不清理会让后续用例出现假 429。
        from routers import ai as ai_router
        ai_router.faq_search_rate_limiter._hits.clear()
        ai_router.voice_rate_limiter._hits.clear()
        ai_router.voice_rate_limiter_member._hits.clear()
        ai_router.bookkeeping_preview_rate_limiter._hits.clear()
        # 记账预览结果缓存同样是进程内存态：不清理会让上一个用例的预览结果被
        # 下一个用例的确认请求命中，出现「确认没调 LLM」的假通过。
        ai_router.bookkeeping_preview_cache.clear()
        # 充值模块：创建频率限流 + 支付失败冷却（crud.recharge 模块级单例）
        from crud import recharge as recharge_crud
        recharge_crud.create_rate_limiter._hits.clear()
        recharge_crud.pay_fail_throttle._buckets.clear()
        recharge_crud.pay_fail_throttle._locked.clear()
        # 会员模块：兑换码核销限流（routers.membership 模块级单例）
        from routers import membership as membership_router
        membership_router.redeem_rate_limiter._hits.clear()

    _clear()
    yield
    _clear()
