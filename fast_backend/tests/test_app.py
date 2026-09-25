"""应用冒烟测试 — 依赖完整性 + 健康检查

import main 成功本身即是一道回归防线：任何模块顶层 import 缺失依赖
（如 requirements.txt 漏装 langchain）都会在这里第一时间暴露。
"""

from fastapi.testclient import TestClient

from main import app


class TestApp:
    def test_health_endpoint(self):
        client = TestClient(app)
        res = client.get("/api/health")
        assert res.status_code == 200
        body = res.json()
        assert body["code"] == 200
        assert body["data"]["status"] == "ok"
        assert body["data"]["version"] == "1.0.0"

    def test_core_routes_registered(self):
        """关键路由挂载检查：AI 流式对话、账单分页、月度统计"""
        paths = {r.path for r in app.routes}
        assert "/api/ai/chat/stream" in paths
        assert "/api/records" in paths
        assert "/api/statistics/monthly" in paths
        assert "/api/ai/analyze/expenses" in paths
