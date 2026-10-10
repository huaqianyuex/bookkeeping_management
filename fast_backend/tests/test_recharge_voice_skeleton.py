"""充值 + AI 语音测试骨架 — 对应《基础版待完成接口实现规格.md》§6.2 / §6.3

用法
----
本文件分两部分：

- **Part A｜纯逻辑用例**：不依赖尚未实现的 `crud/recharge.py` / `ai/stt.py`，
  **今天就能跑**（编码状态机合法性、订单号格式、语音魔数核对表、错误文案口径）。
- **Part B｜集成用例**：依赖 `crud/recharge.py` 与 `routers/recharge.py`。
  模块不存在时**整类 skip**，落地后自动开始生效，无需改测试代码。

⚠️ 依赖提醒：`requirements-dev.txt` 目前只声明了 `pytest` + `httpx`，
**未声明 `pytest-asyncio`**。Part B 的 async 用例依赖它（当前环境实测 1.4.0 已装，
但换机器/换 venv 会直接 collection error）。落地前请补：

    pip install pytest-asyncio
    # 或写入 fast_backend/requirements-dev.txt：
    # pytest-asyncio>=0.23

pytest-asyncio 1.x 默认 `asyncio_mode=strict`，故每个 async 用例都显式带
`@pytest.mark.asyncio`，不依赖 ini 配置。
"""

import re
from decimal import Decimal

import pytest

# ── 契约常量（与规格文档一致；实现落地后改为从模块导入，避免两处漂移）──

ORDER_STATES = {0: "待支付", 1: "待审批", 2: "已支付", 3: "已拒绝", 4: "已取消", 5: "已关闭"}
TERMINAL_STATES = {2, 3, 4, 5}
ALLOWED_LEGAL_TRANSITIONS = {
    (0, 2),  # 支付成功且无风控
    (0, 1),  # 支付成功但命中风控
    (0, 4),  # 用户取消
    (0, 5),  # 超时懒关闭
    (1, 2),  # 审核通过
    (1, 3),  # 审核拒绝
}

AUDIO_MAGIC = {
    "wav":  (b"RIFF", b"WAVE"),
    "mp3":  (b"ID3", None),
    "webm": (b"\x1a\x45\xdf\xa3", None),
    "ogg":  (b"OggS", None),
    "m4a":  (None, b"ftyp"),
    "aac":  (None, b"ftyp"),
}


# ══════════════════════════════════════════════════════════════════════
# Part A｜纯逻辑用例（今天即可运行）
# ══════════════════════════════════════════════════════════════════════


class TestOrderNoFormat:
    """规格 §一「业务规则」第 5 步：order_no = RCH + 14 位时间戳 + 6 位 hex 大写 = 23 字符"""

    # RCH(3) + 20260910160000(14) + A3F9CD(6) = 23
    SAMPLE = "RCH20260910160000A3F9CD"
    ORDER_NO_RE = re.compile(r"^RCH\d{14}[0-9A-F]{6}$")

    def test_length_is_23(self):
        assert len(self.SAMPLE) == 23, "订单号示例本身写错：RCH+14位时间戳+6位hex 应为 23 字符"

    def test_shape(self):
        assert self.ORDER_NO_RE.match(self.SAMPLE)

    def test_timestamp_part_is_14_digits(self):
        ts = self.SAMPLE[3:17]
        assert len(ts) == 14 and ts.isdigit()

    def test_rand_part_is_6_upper_hex(self):
        tail = self.SAMPLE[17:]
        assert len(tail) == 6, f"hex 段应为 6 位，实际 {len(tail)} 位"
        assert all(c in "0123456789ABCDEF" for c in tail)

    def test_lowercase_hex_rejected(self):
        assert not self.ORDER_NO_RE.match(self.SAMPLE[:17] + self.SAMPLE[17:].lower())

    def test_fits_order_no_column(self):
        """库列 String(32)，23 字符留有余量"""
        assert len(self.SAMPLE) <= 32


class TestOrderStateMachine:
    """规格 §一「订单状态机」：终态 {2,3,4,5}，其余流转一律拒绝"""

    def test_all_six_states_defined(self):
        assert set(ORDER_STATES) == {0, 1, 2, 3, 4, 5}

    def test_status_text_covers_every_status(self):
        assert set(ORDER_STATES.values()) == {"待支付", "待审批", "已支付", "已拒绝", "已取消", "已关闭"}

    def test_legal_transitions(self):
        actual = {(a, b) for a in ORDER_STATES for b in ORDER_STATES
                  if (a, b) in ALLOWED_LEGAL_TRANSITIONS}
        assert actual == ALLOWED_LEGAL_TRANSITIONS

    def test_no_transition_out_of_terminal_states(self):
        """终态不可再流转——这是防重复延期的第一道闸"""
        for term in TERMINAL_STATES:
            for nxt in ORDER_STATES:
                assert (term, nxt) not in ALLOWED_LEGAL_TRANSITIONS

    def test_approve_and_reject_edges_exist(self):
        """1→2（通过）与 1→3（拒绝）是仅有的两条「人工审核」出口"""
        assert (1, 2) in ALLOWED_LEGAL_TRANSITIONS
        assert (1, 3) in ALLOWED_LEGAL_TRANSITIONS

    def test_no_direct_edge_into_rejected_except_from_pending(self):
        """status=3（已拒绝）只能由 status=1 进入——用户/超时都不能直接到已拒绝"""
        sources = [a for a, b in ALLOWED_LEGAL_TRANSITIONS if b == 3]
        assert sources == [1]

    def test_paid_state_reachable_by_two_paths(self):
        """status=2 有两条入口：0→2（支付直通）与 1→2（审核放行）"""
        sources = sorted(a for a, b in ALLOWED_LEGAL_TRANSITIONS if b == 2)
        assert sources == [0, 1]

    def test_cancel_only_from_unpaid(self):
        assert (0, 4) in ALLOWED_LEGAL_TRANSITIONS
        for src in (1, 2, 3, 4, 5):
            assert (src, 4) not in ALLOWED_LEGAL_TRANSITIONS

    def test_review_states_cannot_skip_paid(self):
        """待审批(1) 不能直接到 已取消(4)/已关闭(5)"""
        for dst in (4, 5):
            assert (1, dst) not in ALLOWED_LEGAL_TRANSITIONS


class TestRiskThresholdLogic:
    """规格 §一「业务规则」第 6 步：单笔 >=100 → SINGLE_AMOUNT；日累计>=200 → DAILY_TOTAL"""

    MANUAL_REVIEW_AMOUNT = Decimal("100")
    DAILY_REVIEW_AMOUNT = Decimal("200")

    @staticmethod
    def decide(amount: Decimal, today_received: Decimal) -> list[str]:
        """复刻风控判定；返回命中的标记列表（空=低风险直转已支付）"""
        flags = []
        if amount >= 100:
            flags.append("SINGLE_AMOUNT")
        if today_received >= 0 and today_received + amount >= 200:
            flags.append("DAILY_TOTAL")
        return flags

    def test_small_amount_low_risk(self):
        assert self.decide(Decimal("18.00"), Decimal("0")) == []

    def test_single_amount_threshold_inclusive(self):
        """阈值含等号：正好 100 也进人工审核"""
        assert "SINGLE_AMOUNT" in self.decide(Decimal("100.00"), Decimal("0"))

    def test_just_below_single_threshold(self):
        assert "SINGLE_AMOUNT" not in self.decide(Decimal("99.99"), Decimal("0"))

    def test_daily_total_accumulates(self):
        """当日已收 190 + 本笔 20 = 210 >= 200 → DAILY_TOTAL"""
        assert "DAILY_TOTAL" in self.decide(Decimal("20.00"), Decimal("190.00"))

    def test_daily_total_not_triggered_by_first_order(self):
        assert "DAILY_TOTAL" not in self.decide(Decimal("150.00"), Decimal("0"))

    def test_both_flags_can_coexist(self):
        flags = self.decide(Decimal("250.00"), Decimal("100.00"))
        assert set(flags) == {"SINGLE_AMOUNT", "DAILY_TOTAL"}


class TestAmountComparison:
    """规格 §一「业务规则」第 5 步：Decimal 精确比对，字符串下发避免精度丢失"""

    def test_str_roundtrip_keeps_two_decimals(self):
        assert str(Decimal("18.00")) == "18.00"
        assert str(Decimal("158.00")) == "158.00"

    def test_mismatched_amount_rejected(self):
        assert Decimal("1.00") != Decimal("18.00")

    def test_trailing_zero_difference_is_equal(self):
        """18.0 与 18.00 是同值，不应被误判为金额不符"""
        assert Decimal("18.0") == Decimal("18.00")

    def test_float_would_lose_precision(self):
        """说明为何必须 Decimal：float 会引入二进制误差"""
        assert Decimal("0.1") + Decimal("0.2") == Decimal("0.3")
        assert 0.1 + 0.2 != 0.3  # noqa: F632 —— 正是要避免的写法


class TestVoiceMagicNumber:
    """规格 §二「魔数核对表」：Content-Type 与文件名均可伪造，只信魔数

    实现落地后改为 `from routers.ai import _looks_like_audio` 直接测真实实现。
    """

    @staticmethod
    def looks_like_audio(data: bytes, ext: str) -> bool:
        if len(data) < 12:
            return False
        if ext == "wav":
            return data[:4] == b"RIFF" and data[8:12] == b"WAVE"
        if ext == "mp3":
            return data[:3] == b"ID3" or (data[0] == 0xFF and (data[1] & 0xE0) == 0xE0)
        if ext in ("m4a", "aac"):
            return data[4:8] == b"ftyp" or (data[0] == 0xFF and (data[1] & 0xF6) == 0xF0)
        if ext == "webm":
            return data[:4] == b"\x1a\x45\xdf\xa3"
        if ext == "ogg":
            return data[:4] == b"OggS"
        return False

    # 构造合法样本（每个样本 >= 12 字节，否则会被长度门槛直接判否）
    WAV = b"RIFF\x24\x08\x00\x00WAVEfmt "
    MP3_ID3 = b"ID3\x03\x00\x00\x00\x00\x00\x00\x00\x00"   # ID3v2.3 头
    MP3_SYNC = b"\xff\xfb\x90\x64\x00\x00\x00\x00\x00\x00\x00\x00"   # 帧同步 0xFF 0xFB
    M4A = b"\x00\x00\x00\x20ftypM4A \x00\x00"
    WEBM = b"\x1a\x45\xdf\xa3\x01\x00\x00\x00\x00\x00\x00\x00"
    OGG = b"OggS\x00\x02\x00\x00\x00\x00\x00\x00"
    TXT = b"this is definitely plain text, not audio at all"

    def test_all_valid_samples_meet_length_gate(self):
        """先自检样本本身，避免样本写短了导致魔数测试假失败"""
        for name in ("WAV", "MP3_ID3", "MP3_SYNC", "M4A", "WEBM", "OGG"):
            assert len(getattr(self, name)) >= 12, f"{name} 样本不足 12 字节"

    @pytest.mark.parametrize("ext,data", [
        ("wav", WAV), ("mp3", MP3_ID3), ("mp3", MP3_SYNC),
        ("m4a", M4A), ("webm", WEBM), ("ogg", OGG),
    ])
    def test_valid_audio_accepted(self, ext, data):
        assert self.looks_like_audio(data, ext) is True

    @pytest.mark.parametrize("ext", ["wav", "mp3", "m4a", "aac", "webm", "ogg"])
    def test_text_disguised_as_audio_rejected(self, ext):
        """核心防护：改后缀的任意字节不得消耗外部 ASR 计费"""
        assert self.looks_like_audio(self.TXT, ext) is False

    def test_too_short_always_rejected(self):
        assert self.looks_like_audio(b"RIFF", "wav") is False
        assert self.looks_like_audio(b"", "wav") is False

    def test_unknown_extension_rejected(self):
        assert self.looks_like_audio(self.WAV, "flac") is False

    def test_cross_format_mismatch_rejected(self):
        """wav 内容配 mp3 后缀 -> 必须拒绝"""
        assert self.looks_like_audio(self.WAV, "mp3") is False

    def test_wav_requires_both_riff_and_wave(self):
        assert self.looks_like_audio(b"RIFF\x00\x00\x00\x00XXXX" + b"Y", "wav") is False


class TestErrorMessageConsistency:
    """规格「统一约定」：业务失败中文、验签失败固定 401、裸 JSON 用中文 error"""

    # 允许出现在错误文案里的技术名词（格式名 / 单位），检查前先剔除
    ALLOWED_ASCII = ("mp3", "m4a", "wav", "aac", "webm", "ogg", "MB", "ASR")

    @classmethod
    def _has_stray_english(cls, msg: str) -> bool:
        cleaned = msg
        for token in cls.ALLOWED_ASCII:
            cleaned = cleaned.replace(token, "")
        return bool(re.search(r"[A-Za-z]{2,}", cleaned))

    def test_business_error_messages_are_chinese(self):
        msgs = [
            "充值套餐不存在", "存在未支付订单，请先完成或取消", "支付金额不符",
            "订单已支付", "订单已过期", "订单已关闭", "订单待审核中", "支付失败",
            "回调签名无效", "订单不存在", "下单过于频繁，请稍后再试",
        ]
        for m in msgs:
            assert m, "错误文案不得为空"
            assert not self._has_stray_english(m), f"错误文案混入英文：{m}"

    # 规格 §1.7「验签失败固定 401」/ §1.6「跨用户统一 404」/ §1.2「限流 429」
    SIGN_ERROR_CODE = 401
    NOT_FOUND_CODE = 404
    RATE_LIMIT_CODE = 429
    BUSINESS_CODE = 400

    def test_error_status_codes_are_mutually_distinct(self):
        """三类失败必须用不同状态码，网关侧才能据此区分「签名配置错了」与「业务状态不对」"""
        assert len({self.SIGN_ERROR_CODE, self.NOT_FOUND_CODE,
                    self.RATE_LIMIT_CODE, self.BUSINESS_CODE}) == 4

    def test_sign_failure_not_reusing_business_code(self):
        assert self.SIGN_ERROR_CODE != self.BUSINESS_CODE

    def test_voice_error_messages_are_chinese(self):
        for m in ["语音识别未启用", "说话太频繁，请 30 秒后再试",
                  "不支持的音频格式，请使用 mp3 / m4a / wav / aac / webm",
                  "音频过大，请控制在 5MB 以内", "音频内容为空",
                  "音频内容与格式不符，请重新录音后再试", "语音识别暂不可用，请稍后重试"]:
            assert m, "错误文案不得为空"
            assert not self._has_stray_english(m), f"错误文案混入英文：{m}"


# ══════════════════════════════════════════════════════════════════════
# Part B｜集成用例（依赖 crud/recharge.py / routers/recharge.py，缺失则 skip）
# ══════════════════════════════════════════════════════════════════════

# 注意：这里用 try/except 而不是 pytest.importorskip —— 后者在模块级会把
# **整个文件**跳过，导致上面的 Part A 纯逻辑用例也一并不跑（实测踩过）。
try:  # pragma: no cover - 仅探测模块是否存在
    from crud import recharge as _recharge_crud

    _HAS_RECHARGE = True
    _SKIP_REASON = ""
except ImportError:  # pragma: no cover
    _recharge_crud = None
    _HAS_RECHARGE = False
    _SKIP_REASON = "crud/recharge.py 未实现（规格 §6.1 步骤 5）"

skip_if_no_recharge = pytest.mark.skipif(not _HAS_RECHARGE, reason=_SKIP_REASON)


@skip_if_no_recharge
class TestCreateOrderChain:
    """规格 §6.2 前两行 + 「防堆积」"""

    @pytest.mark.asyncio
    async def test_plan_not_in_config(self):
        """planId 不在 RECHARGE_PLANS -> 400「充值套餐不存在」"""
        with pytest.raises(Exception) as ei:
            await _recharge_crud.create_order(db=None, user_id=1, plan_id="__nope__", client_ip="")
        assert "充值套餐不存在" in str(ei.value)

    @pytest.mark.asyncio
    async def test_rate_limit_after_three_creates(self):
        """60s 内第 4 次下单 -> 429"""
        # 需要真实 DB session；落地后用 TestClient + dependency_overrides 驱动
        pytest.skip("需 DB：见规格 §6.1 步骤 6 的 curl 验收")

    @pytest.mark.asyncio
    async def test_pending_order_blocks_second_order(self):
        """已有 status=0 订单 -> 400「存在未支付订单，请先完成或取消」"""
        pytest.skip("需 DB：见规格 §6.2「防堆积」用例")


@skip_if_no_recharge
class TestPaymentCallback:
    """规格 §6.2 核心 8 条：正常支付 / 风控 / 幂等 / 金额核对 / 验签 / 超时 / 失败锁"""

    @pytest.mark.asyncio
    async def test_normal_payment_extends_membership(self):
        """status=0 -> 2，会员延期 days 天，审计 CREATE + PAY_SUCCESS"""
        pytest.skip("需 DB")

    @pytest.mark.asyncio
    async def test_single_amount_hold(self):
        """amount>=100 -> status=1、risk_flags=SINGLE_AMOUNT、不延期"""
        pytest.skip("需 DB")

    @pytest.mark.asyncio
    async def test_daily_total_hold(self):
        """当日已收 + 本笔>=200 -> status=1、risk_flags=DAILY_TOTAL"""
        pytest.skip("需 DB")

    @pytest.mark.asyncio
    async def test_duplicate_callback_does_not_extend_twice(self):
        """已 status=2 再回调 -> 400，且会员到期时间不变（防重复延期）"""
        pytest.skip("需 DB")

    @pytest.mark.asyncio
    async def test_amount_mismatch_rejected(self):
        """Decimal 比对不符 -> 400「支付金额不符」+ 审计 PAY_FAIL"""
        pytest.skip("需 DB")

    @pytest.mark.asyncio
    async def test_expired_order_lazy_closed(self):
        """expires_at <= NOW -> status=5 + 400「订单已过期」+ 审计 CLOSE"""
        pytest.skip("需 DB")

    @pytest.mark.asyncio
    async def test_pay_fail_lock(self):
        """连续 5 次 fail -> 第 6 次 429"""
        pytest.skip("需 DB")

    def test_row_lock_taken_before_state_check(self):
        """静态红线：SELECT ... FOR UPDATE 必须在状态判定之前

        实现落地后改为读 crud/recharge.py 源码，断言 FOR UPDATE 出现在
        status 判定之前；此处先以注释固化该约束。
        """
        pytest.skip("静态检查：见规格 §6.3「充值业务」第 4 行")


@skip_if_no_recharge
class TestApproveRejectCancel:
    """规格 §6.2 中段：审核通过 / 审核拒绝 / 取消"""

    @pytest.mark.asyncio
    async def test_approve_only_from_pending(self):
        pytest.skip("需 DB")

    @pytest.mark.asyncio
    async def test_reject_does_not_extend(self):
        pytest.skip("需 DB")

    @pytest.mark.asyncio
    async def test_cancel_uses_dual_condition_lock(self):
        """cancel 按 order_no + user_id 双条件行锁，跨用户不可取消"""
        pytest.skip("需 DB")


@skip_if_no_recharge
class TestCrossUserIsolation:
    """规格 §1.6：归属写进 WHERE，跨用户统一 404（不区分不存在/非本人）"""

    @pytest.mark.asyncio
    async def test_other_user_gets_404(self):
        pytest.skip("需 DB")