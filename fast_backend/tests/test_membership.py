"""会员模块测试骨架 — 用例清单见 docs/membership-plan.md §9

约定：不连真实 MySQL；路由流程用 dependency_overrides + monkeypatch
（照 tests/test_sqli_login.py 模式），纯逻辑用普通断言。
"""

from fastapi.testclient import TestClient

from main import app


class TestMembershipRoutes:
    """路由注册冒烟：main 导入成功本身即覆盖 import 依赖完整性"""

    def test_membership_routes_registered(self):
        paths = {r.path for r in app.routes}
        assert "/api/membership/status" in paths
        assert "/api/membership/redeem" in paths
        assert "/api/admin/membership/codes" in paths
        assert "/api/admin/membership/codes/{code_id}/void" in paths
        assert "/api/admin/membership/grant" in paths


# —— 待实现用例（实现 crud 后补齐，规格见 docs/membership-plan.md §9） ——
# TODO: normalize_code 纯单元（去空格/连字符、转大写）
# TODO: MEMBERSHIP_PLANS 完整性（会员各项 > 免费各项）
# TODO: /status 信封（monkeypatch get_tier/get_effective_membership/get_usage_row；
#       断言 code==200、data.tierName=="免费版"、data.usage.chat.limit==10）
# TODO: /redeem 400 分支与成功分支（monkeypatch redeem_code）
# TODO: 管理端 403 鉴权（get_current_admin 抛 403 的依赖 override）
# TODO: AI 闸门 429 裸 JSON（超额断言 status_code==429、code=="QUOTA_EXCEEDED"、
#       响应体不是 {code,message,data} 信封）
# TODO: 配额通过即计数（monkeypatch incr_usage 记录调用参数，断言 kind=="chat"）
