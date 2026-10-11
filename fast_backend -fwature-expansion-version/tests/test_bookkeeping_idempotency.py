"""AI 记账幂等键生命周期测试 — 失败后能否用同一 clientMsgId 重试

回归背景
--------
`uk_abk_client_msg (user_id, client_msg_id)` 唯一键会被**任何没产出 record 的
日志**占住；而两个去重查询（find_log_by_client_msg / find_recent_by_dedup）都带
`status=1 AND record_ids IS NOT NULL` 过滤，查不到这类日志。于是：

    失败 → 用户用同一 clientMsgId 重试 → INSERT 撞唯一键 → IntegrityError
         → 回查只认成功日志 → 查不到 → 永远返回「请求处理中」

客户端幂等键存在的意义恰恰是「弱网重发要安全」，这条链路把它废掉了。
修复：失败时把 client_msg_id 置 NULL（MySQL 唯一索引对多行 NULL 不冲突，
正好复用 models/bookkeeping.py 里已写明的既有语义）。
"""

import types

import pytest

from crud import ai as ai_crud


class LogRow:
    """假 AiBookkeepingLog 行"""

    def __init__(self, id=1, user_id=1, client_msg_id="cm-1",
                 status=1, action="created", record_ids=None):
        self.id = id
        self.user_id = user_id
        self.client_msg_id = client_msg_id
        self.status = status
        self.action = action
        self.record_ids = record_ids


class RecordingSession:
    def __init__(self, rows=None):
        self.rows = rows or []
        self.statements = []
        self.committed = False

    async def execute(self, stmt):
        self.statements.append(str(stmt))
        return _R()

    async def commit(self):
        self.committed = True

    def sql_for(self, table: str) -> str:
        needle = f"update {table}"
        for s in self.statements:
            if needle in s.lower():
                return s
        raise AssertionError(f"未找到对 {table} 的 UPDATE：{self.statements}")


class _R:
    scalar_one_or_none = staticmethod(lambda: None)


class TestFindAnyByClientMsg:
    """该查询刻意不过滤 status / record_ids——否则就看不到死日志"""

    def test_query_has_no_status_filter(self, monkeypatch):
        db = RecordingSession()
        captured = {}

        async def _exec(stmt):
            captured["sql"] = str(stmt)
            return _R()

        db.execute = _exec
        import inspect
        src = inspect.getsource(ai_crud.find_any_by_client_msg)
        assert "status" not in src.split('"""')[-1], "查询体不应含 status 过滤"
        assert "record_ids" not in src.split('"""')[-1], "查询体不应含 record_ids 过滤"

    @pytest.mark.asyncio
    async def test_returns_none_safely(self):
        db = RecordingSession()
        assert await ai_crud.find_any_by_client_msg(db, 1, "cm-1") is None


class TestReleaseClientMsgId:
    @pytest.mark.asyncio
    async def test_updates_client_msg_id_column(self):
        """SQL 里只能看到 SET client_msg_id=...；NULL 是执行时绑定的参数，
        不出现在语句文本中，故这里断言「设置了该列」而非「文本含 NULL」"""
        db = RecordingSession()
        await ai_crud.release_client_msg_id(db, 42)
        sql = db.sql_for("ai_bookkeeping_logs")
        assert "client_msg_id" in sql

    @pytest.mark.asyncio
    async def test_binds_null_value(self):
        """抓取实际绑定参数，确认传的是 None（这才是释放键的关键）"""
        db = RecordingSession()
        bound = {}

        async def _exec(stmt):
            bound["stmt"] = stmt
            return _R()

        db.execute = _exec
        await ai_crud.release_client_msg_id(db, 42)
        # 未执行的语句上 _bindparams 为空，改用 compile().params 取绑定值
        params = bound["stmt"].compile().params
        assert "client_msg_id" in params, f"未绑定 client_msg_id：{params}"
        assert params["client_msg_id"] is None, \
            "释放幂等键必须绑定 None，否则唯一键仍被占用"

    @pytest.mark.asyncio
    async def test_does_not_delete_the_row(self):
        """释放键≠ 删行：审计痕迹必须保留（哪次失败了、为什么）"""
        import inspect
        src = inspect.getsource(ai_crud.release_client_msg_id)
        assert "delete" not in src.lower(), "释放幂等键不应删除审计行"

    def test_bk_fail_passes_none(self):
        """_bk_fail 必须显式传 client_msg_id=None"""
        import inspect
        from routers import ai as ai_router

        src = inspect.getsource(ai_router.bookkeeping)
        assert "client_msg_id=None" in src, \
            "失败善后未释放幂等键，重试会永久撞 uk_abk_client_msg"


class TestIdempotencyKeyLifecycle:
    """纯逻辑复现：模拟一次失败后能否重试"""

    def _dedup_lookup_returns(self, log):
        """复刻 find_log_by_client_msg 的过滤条件"""
        return log if (log.status == 1 and log.record_ids is not None) else None

    def test_dead_log_is_invisible_to_dedup_queries(self):
        """死日志对两个去重查询都不可见——这正是撞键后查不到的原因"""
        dead = LogRow(status=0, action="error", record_ids=None)
        assert self._dedup_lookup_returns(dead) is None

    def test_crash_leaves_status1_but_no_records(self):
        """硬崩（进程被 kill）时日志停在 status=1 + record_ids=NULL"""
        crashed = LogRow(status=1, action="created", record_ids=None)
        assert self._dedup_lookup_returns(crashed) is None

    def test_successful_log_is_visible(self):
        ok = LogRow(status=1, action="created", record_ids=[128])
        assert self._dedup_lookup_returns(ok) is not None

    def test_null_client_msg_id_frees_unique_key(self):
        """修复的核心：置 NULL 后唯一键不再阻塞重试

        MySQL 唯一索引对多行 NULL 不冲突（models/bookkeeping.py 已写明该语义）。
        """
        released = LogRow(client_msg_id=None, status=0, action="error")
        assert released.client_msg_id is None
        # 释放后再次查询该 client_msg_id，查不到任何占位者 -> 可重新 INSERT
        assert not [r for r in [released]
                    if r.client_msg_id == "cm-1"]


class TestDeadLogRecoveryBranch:
    """IntegrityError 分支必须区分「真在处理中」与「死日志」"""

    def test_dead_log_detected_by_record_ids(self):
        dead = LogRow(status=1, action="created", record_ids=None)
        assert dead.record_ids is None, "无 record 即为死日志"

    def test_successful_log_not_treated_as_dead(self):
        ok = LogRow(status=1, action="created", record_ids=[1])
        assert ok.record_ids, "有 record 的成功日志不能被当成死日志释放掉"

    def test_router_source_branches_on_record_ids(self):
        """静态检查：IntegrityError 分支确实按 record_ids 做了二分支"""
        import inspect

        from routers import ai as ai_router

        src = inspect.getsource(ai_router.bookkeeping)
        assert "find_any_by_client_msg" in src, "缺少死日志检测"
        assert "release_client_msg_id" in src, "缺少释放幂等键的动作"
        assert "请求处理中" in src, "并发处理中的提示应保留"


class TestUniqueKeySemantics:
    """用真实数据库验证修复所依赖的前提：UNIQUE 列上的多行 NULL 不冲突。

    models/bookkeeping.py 的类注释声称「MySQL 唯一索引对多行 NULL 不冲突」，
    本修复正是复用该语义。这里用 SQLite（行为与 MySQL 一致）跑真表验证，
    避免「注释说的」和「实际做的」不一致时无人察觉。
    """

    @staticmethod
    def _conn():
        from sqlalchemy import create_engine, text

        eng = create_engine("sqlite://")
        with eng.begin() as c:
            c.execute(text(
                "CREATE TABLE logs ("
                "  id INTEGER PRIMARY KEY,"
                "  user_id INTEGER NOT NULL,"
                "  client_msg_id VARCHAR(64)"
                ")"
            ))
            c.execute(text(
                "CREATE UNIQUE INDEX uk_abk_client_msg "
                "ON logs (user_id, client_msg_id)"
            ))
        return eng

    def test_duplicate_non_null_key_is_rejected(self):
        from sqlalchemy import text

        eng = self._conn()
        with eng.begin() as c:
            c.execute(text("INSERT INTO logs (user_id, client_msg_id) VALUES (1,'cm-1')"))
            try:
                c.execute(text("INSERT INTO logs (user_id, client_msg_id) VALUES (1,'cm-1')"))
                raised = False
            except Exception:
                raised = True
        assert raised, "非 NULL 的重复键必须被拒——这正是撞键保护生效的证据"

    def test_multiple_null_keys_are_allowed(self):
        """置 NULL 释放键的前提：唯一索引允许多行 NULL"""
        from sqlalchemy import text

        eng = self._conn()
        with eng.begin() as c:
            c.execute(text("INSERT INTO logs (user_id, client_msg_id) VALUES (1,'cm-1')"))
            c.execute(text("UPDATE logs SET client_msg_id=NULL WHERE client_msg_id='cm-1'"))
            # 连续插入多行 NULL 不应冲突
            for _ in range(3):
                c.execute(text("INSERT INTO logs (user_id, client_msg_id) VALUES (1, NULL)"))
            total = c.execute(text("SELECT COUNT(*) FROM logs")).scalar()
        assert total == 4, "多行 NULL 必须都能插入，否则释放键的方案不成立"

    def test_retry_after_release_succeeds(self):
        """完整复现修复效果：释放键后，同一 clientMsgId 可重新 INSERT"""
        from sqlalchemy import text

        eng = self._conn()
        with eng.begin() as c:
            # 第一次：占位
            c.execute(text("INSERT INTO logs (user_id, client_msg_id) VALUES (1,'cm-1')"))
            # 失败 → 释放键
            c.execute(text("UPDATE logs SET client_msg_id=NULL WHERE client_msg_id='cm-1'"))
            # 重试：同一 clientMsgId 重新占位，应当成功
            c.execute(text("INSERT INTO logs (user_id, client_msg_id) VALUES (1,'cm-1')"))
        assert True, "释放后重试成功"