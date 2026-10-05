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
    """用例间隔离：登录限流/语音限流/AI 并发槽是进程内存态，
    多个用例共用同一 test client IP，不清理会互相污染出假 429/锁死。"""
    def _clear():
        from utils import ai_concurrency, throttle
        throttle.login_throttle._buckets.clear()
        throttle.login_throttle._locked.clear()
        throttle.login_ip_throttle._buckets.clear()
        throttle.login_ip_throttle._locked.clear()
        throttle.voice_rate_limiter._hits.clear()
        ai_concurrency._slots.clear()

    _clear()
    yield
    _clear()
