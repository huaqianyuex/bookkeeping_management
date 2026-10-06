"""ai.memory 单元测试 — 历史窗口条数/字数上限，且只从库里取尾部 N 条"""

import types

import pytest

from ai import memory as mem


class FakeCrud:
    """记录调用参数的假 crud.ai"""

    def __init__(self, rows):
        self.rows = rows
        self.calls = []

    async def list_messages_tail(self, db, session_id, limit):
        self.calls.append((session_id, limit))
        return self.rows[-limit:] if limit > 0 else []

    async def list_messages(self, db, session_id):
        raise AssertionError("build_history 不应再全量拉取会话消息")


def msg(role, content):
    return types.SimpleNamespace(role=role, content=content)


@pytest.fixture
def patch_crud(monkeypatch):
    import crud
    import crud.ai as crud_ai

    def _install(rows):
        fake = FakeCrud(rows)
        monkeypatch.setattr(crud_ai, "list_messages_tail", fake.list_messages_tail)
        monkeypatch.setattr(crud_ai, "list_messages", fake.list_messages)
        return fake

    return _install


@pytest.mark.asyncio
async def test_uses_sql_limit_not_full_scan(patch_crud):
    """回归：原先调 list_messages 把整个会话读进来再切片"""
    rows = [msg("user" if i % 2 == 0 else "assistant", f"第{i}条") for i in range(50)]
    fake = patch_crud(rows)
    out = await mem.build_history(None, "s1")
    assert fake.calls == [("s1", mem.KEEP_RECENT)]
    assert len(out) == mem.KEEP_RECENT


@pytest.mark.asyncio
async def test_history_is_ascending(patch_crud):
    rows = [msg("user", f"m{i}") for i in range(4)]
    patch_crud(rows)
    out = await mem.build_history(None, "s1")
    assert [m.content for m in out] == ["m0", "m1", "m2", "m3"]


@pytest.mark.asyncio
async def test_token_budget_truncates(patch_crud):
    from langchain_core.messages import HumanMessage

    mem.MAX_TOKENS = 20          # 每条 10 字 → 只能装 2 条
    try:
        rows = [msg("user", "x" * 10) for _ in range(5)]
        patch_crud(rows)
        out = await mem.build_history(None, "s1")
        assert len(out) <= 2
    finally:
        mem.MAX_TOKENS = 2000


@pytest.mark.asyncio
async def test_role_mapping(patch_crud):
    from langchain_core.messages import AIMessage, HumanMessage

    patch_crud([msg("user", "你好"), msg("assistant", "在的")])
    out = await mem.build_history(None, "s1")
    assert isinstance(out[0], HumanMessage)
    assert isinstance(out[1], AIMessage)


@pytest.mark.asyncio
async def test_empty_session(patch_crud):
    patch_crud([])
    assert await mem.build_history(None, "s1") == []


@pytest.mark.asyncio
async def test_zero_keep_recent_skips_query(monkeypatch):
    """KEEP_RECENT=0 时不该白发一次查询"""
    monkeypatch.setattr(mem, "KEEP_RECENT", 0)
    assert await mem.build_history(None, "s1") == []


def test_constants_come_from_settings():
    """回归：MAX_TOKENS/KEEP_RECENT 过去在本文件硬编码，
    settings 里的 MAX_HISTORY_TOKENS/KEEP_RECENT_MESSAGES 形同虚设"""
    from config.settings import KEEP_RECENT_MESSAGES, MAX_HISTORY_TOKENS

    assert mem.MAX_TOKENS == MAX_HISTORY_TOKENS
    assert mem.KEEP_RECENT == KEEP_RECENT_MESSAGES
