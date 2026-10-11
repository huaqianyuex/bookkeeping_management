"""ai.observability 单元测试 — Token / TTFT 计量与聚合

纯逻辑，不产生任何 LLM 调用。
"""

import types

import pytest

from ai import observability as obs
from ai.observability import (
    KIND_ANALYZE,
    KIND_CHAT,
    KIND_BOOKKEEPING,
    LLMUsage,
    Timer,
    UsageRecorder,
    extract_tokens,
    record_call,
)


@pytest.fixture(autouse=True)
def _reset_global():
    obs.recorder.reset()
    yield
    obs.recorder.reset()


def usage(**kw):
    base = dict(kind=KIND_CHAT, model="m", user_id=1)
    base.update(kw)
    return LLMUsage(**base)


class TestExtractTokens:
    def test_usage_metadata(self):
        msg = types.SimpleNamespace(usage_metadata={"input_tokens": 12, "output_tokens": 34})
        assert extract_tokens(msg) == (12, 34)

    def test_response_metadata_fallback(self):
        msg = types.SimpleNamespace(
            usage_metadata=None,
            response_metadata={"token_usage": {"prompt_tokens": 5, "completion_tokens": 7}},
        )
        assert extract_tokens(msg) == (5, 7)

    def test_missing_returns_zeros(self):
        assert extract_tokens(types.SimpleNamespace()) == (0, 0)

    def test_none_response_metadata_is_safe(self):
        msg = types.SimpleNamespace(usage_metadata=None, response_metadata=None)
        assert extract_tokens(msg) == (0, 0)

    def test_partial_metadata_does_not_crash(self):
        msg = types.SimpleNamespace(usage_metadata={"input_tokens": 3})
        assert extract_tokens(msg) == (3, 0)


class TestUsageAccumulator:
    def test_total_tokens(self):
        u = usage(prompt_tokens=10, completion_tokens=20)
        assert u.total_tokens == 30

    def test_defaults(self):
        u = usage()
        assert u.total_tokens == 0 and u.ok is True and u.failover is False


class TestRecorder:
    def test_single_record(self):
        r = UsageRecorder()
        r.record(usage(prompt_tokens=10, completion_tokens=5, latency_ms=100))
        snap = r.snapshot()
        row = snap[KIND_CHAT]["1"]
        assert row["calls"] == 1
        assert row["totalTokens"] == 15
        assert row["avgLatencyMs"] == 100.0

    def test_grouped_by_kind_and_user(self):
        r = UsageRecorder()
        r.record(usage(kind=KIND_CHAT, user_id=1, prompt_tokens=10))
        r.record(usage(kind=KIND_CHAT, user_id=2, prompt_tokens=20))
        r.record(usage(kind=KIND_ANALYZE, user_id=1, prompt_tokens=30))
        snap = r.snapshot()
        assert snap[KIND_CHAT]["1"]["totalTokens"] == 10
        assert snap[KIND_CHAT]["2"]["totalTokens"] == 20
        assert snap[KIND_ANALYZE]["1"]["totalTokens"] == 30

    def test_averages_over_multiple_calls(self):
        r = UsageRecorder()
        r.record(usage(latency_ms=100, ttft_ms=50))
        r.record(usage(latency_ms=300, ttft_ms=150))
        row = r.snapshot()[KIND_CHAT]["1"]
        assert row["avgLatencyMs"] == 200.0
        assert row["avgTtftMs"] == 100.0

    def test_errors_and_failovers_counted(self):
        r = UsageRecorder()
        r.record(usage(ok=False))
        r.record(usage(failover=True))
        row = r.snapshot()[KIND_CHAT]["1"]
        assert row["errors"] == 1 and row["failovers"] == 1

    def test_ttft_none_when_absent(self):
        r = UsageRecorder()
        r.record(usage())
        assert r.snapshot()[KIND_CHAT]["1"]["avgTtftMs"] is None

    def test_ring_capacity_bounds_memory(self):
        r = UsageRecorder(capacity=5)
        for _ in range(20):
            r.record(usage(prompt_tokens=1))
        # 明细被裁剪，但聚合值必须完整
        assert r.snapshot()[KIND_CHAT]["1"]["calls"] == 20
        assert r.total_tokens() == 20

    def test_reset(self):
        r = UsageRecorder()
        r.record(usage())
        r.reset()
        assert r.snapshot() == {}

    def test_json_serialisable(self):
        import json
        r = UsageRecorder()
        r.record(usage(prompt_tokens=1, completion_tokens=2))
        json.dumps(r.snapshot())  # 不得抛异常


class TestTimer:
    def test_ttft_none_before_first_chunk(self):
        assert Timer().ttft_ms is None

    def test_mark_first_chunk_only_counts_first(self):
        t = Timer()
        t.mark_first_chunk()
        first = t.ttft_ms
        t.mark_first_chunk()
        assert t.ttft_ms == first

    def test_elapsed_is_non_negative(self):
        assert Timer().elapsed_ms >= 0


class TestRecordCall:
    def test_records_success(self):
        resp = types.SimpleNamespace(usage_metadata={"input_tokens": 8, "output_tokens": 4})
        u = record_call(KIND_CHAT, "m1", 7, response=resp)
        assert u.prompt_tokens == 8 and u.completion_tokens == 4 and u.ok is True
        assert obs.recorder.snapshot()[KIND_CHAT]["7"]["calls"] == 1

    def test_records_failure_without_raising(self):
        u = record_call(KIND_ANALYZE, "m1", 7, ok=False, error="TimeoutError")
        assert u.ok is False and u.error == "TimeoutError"
        assert obs.recorder.snapshot()[KIND_ANALYZE]["7"]["errors"] == 1

    def test_never_raises_on_bad_input(self):
        """计量是旁路，任何异常都不能打断业务"""
        u = record_call(KIND_BOOKKEEPING, "m", 1, response=object())
        assert isinstance(u, LLMUsage)


class TestKindsAlignedWithQuota:
    """聚合的 kind 必须与 MEMBERSHIP_PLANS 的配额维度一致，否则报表无法与配额对账"""

    def test_kinds_match_membership_quota(self):
        from config.settings import MEMBERSHIP_PLANS
        for plan in MEMBERSHIP_PLANS.values():
            for key in plan:
                if key.startswith("daily_"):
                    kind = key[len("daily_"):]
                    assert kind in {KIND_CHAT, KIND_ANALYZE, KIND_BOOKKEEPING}, kind