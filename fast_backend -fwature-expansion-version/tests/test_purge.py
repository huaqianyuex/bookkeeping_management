"""tasks.purge 单元测试 — 软删物理清理

不连真实 MySQL：用假 session 记录执行的 SQL 并按表名返回 rowcount。
APScheduler 为可选依赖，缺失时 start_scheduler 应优雅返回 False。
"""

import pytest

from tasks import purge


class FakeResult:
    def __init__(self, rowcount=0):
        self.rowcount = rowcount


class RecordingSession:
    """记录每次 execute 的 SQL 文本，用于断言删除条件带上了软删过滤

    真实表名是 `sessions` / `messages`（见 models/chat.py）。
    """

    def __init__(self):
        self.statements = []
        self.committed = False

    async def execute(self, stmt):
        text = str(stmt)
        self.statements.append(text)
        low = text.lower()
        if "delete from sessions" in low:
            return FakeResult(rowcount=3)
        if "delete from messages" in low:
            return FakeResult(rowcount=1)
        return FakeResult(rowcount=0)

    async def commit(self):
        self.committed = True

    def sql_for(self, table: str) -> str:
        needle = f"delete from {table}"
        for s in self.statements:
            if needle in s.lower():
                return s
        raise AssertionError(f"未找到对 {table} 的 DELETE 语句：{self.statements}")


class TestPurgeExpiredSessions:
    @pytest.mark.asyncio
    async def test_deletes_and_commits(self):
        db = RecordingSession()
        result = await purge.purge_expired_sessions(db)
        assert result["sessions"] == 3
        assert result["orphanMessages"] == 1
        assert db.committed is True

    @pytest.mark.asyncio
    async def test_session_delete_requires_soft_deleted_and_expired(self):
        """关键不变量：必须同时含 deleted_at > 0 与 deleted_at < cutoff，
        否则会误删用户**没有**删除的正常会话"""
        db = RecordingSession()
        await purge.purge_expired_sessions(db)
        sql = db.sql_for("sessions")
        assert "deleted_at" in sql
        assert sql.lower().count("deleted_at") >= 2, \
            f"删除条件应同时含 deleted_at > 0 与 deleted_at < cutoff，实际：{sql}"

    @pytest.mark.asyncio
    async def test_orphan_cleanup_is_defensive_only(self):
        """孤儿消息清理走 NOT IN 子查询（messages 本身没有软删字段）"""
        db = RecordingSession()
        await purge.purge_expired_sessions(db)
        assert "not in" in db.sql_for("messages").lower()

    @pytest.mark.asyncio
    async def test_second_run_does_not_raise(self):
        """重复执行应幂等，不抛异常"""
        db = RecordingSession()
        await purge.purge_expired_sessions(db)
        db.statements.clear()
        result = await purge.purge_expired_sessions(db)
        assert set(result) == {"sessions", "orphanMessages"}

    def test_cutoff_keeps_recent_deletions(self):
        import time as _t

        cutoff = purge._cutoff_ms()
        now_ms = int(_t.time() * 1000)
        assert 0 < cutoff < now_ms, "cutoff 应是早于当前的历史毫秒时间戳"
        # 刚删除（1 秒前）的会话必须落在 cutoff 之后，即不被清理——留反悔窗口
        assert (now_ms - 1000) > cutoff, "1 秒前删除的会话不应被清理"


class TestSchedulerLifecycle:
    def test_start_returns_false_when_apscheduler_missing(self, monkeypatch):
        """缺可选依赖必须优雅降级，绝不能让应用起不来"""
        import builtins

        real_import = builtins.__import__

        def _fake_import(name, *args, **kwargs):
            if name.startswith("apscheduler"):
                raise ImportError("No module named 'apscheduler'")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", _fake_import)
        assert purge.start_scheduler() is False

    def test_stop_never_raises(self):
        """关闭失败不应影响应用退出"""
        purge.stop_scheduler()   # 不抛异常即通过

    @pytest.mark.asyncio
    async def test_purge_job_swallows_db_error(self, monkeypatch):
        """一轮失败不能让调度器停摆"""
        import config.db_config as db_cfg

        class BoomSession:
            async def __aenter__(self):
                raise RuntimeError("db down")

            async def __aexit__(self, *a):
                return False

        monkeypatch.setattr(db_cfg, "AsyncSessionLocal", lambda: BoomSession())
        await purge._purge_job()   # 不抛异常即通过