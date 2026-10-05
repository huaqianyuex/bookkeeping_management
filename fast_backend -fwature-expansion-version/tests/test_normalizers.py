"""ai.normalizers 单元测试 — 金额 / 日期归一化（纯函数）"""

from datetime import date
from decimal import Decimal

from ai.normalizers import normalize_amount, normalize_date

TODAY = date(2026, 9, 26)


class TestNormalizeAmount:
    """金额口径为 Decimal（禁 float 存钱）：Decimal("15.46") != 15.46(float)，
    断言必须用 Decimal 字面量比较。"""

    def test_llm_parsed_value_clipped(self):
        assert normalize_amount(None, 15) == Decimal("15.00")
        assert normalize_amount(None, 15.456) == Decimal("15.46")  # 保留两位
        assert isinstance(normalize_amount(None, 15), Decimal)

    def test_out_of_range_returns_none(self):
        assert normalize_amount(None, 0) is None
        assert normalize_amount(None, -5) is None
        assert normalize_amount(None, 100_000_000) is None  # 超上限

    def test_arabic_from_raw_text(self):
        assert normalize_amount("早餐花了 15 元", None) == Decimal("15.00")
        assert normalize_amount("花了 1,200 块", None) == Decimal("1200.00")

    def test_wan_unit(self):
        assert normalize_amount("工资 1万2", None) == Decimal("12000.00")

    def test_chinese_digits(self):
        assert normalize_amount("七十九块", None) == Decimal("79.00")
        assert normalize_amount("两块钱", None) == Decimal("2.00")

    def test_no_float_precision_garbage(self):
        """0.1 必须精确成 0.10，而不是 0.1000000000000000055511…"""
        assert str(normalize_amount("0.1元", None)) == "0.10"

    def test_unparseable_returns_none(self):
        """抓不到金额 → None → 调用方触发 clarify 追问，不猜测"""
        assert normalize_amount("吃了个饭", None) is None


class TestNormalizeDate:
    def test_llm_iso_used_directly(self):
        assert normalize_date("2026-09-01", "2026-09-01", TODAY) == date(2026, 9, 1)

    def test_future_iso_year_minus_one(self):
        """未带未来语义的超前日期 → 年份-1（常见于「6月30号」在年初的歧义）"""
        assert normalize_date(None, "2027-09-01", TODAY) == date(2026, 9, 1)

    def test_relative_words(self):
        assert normalize_date("今天", None, TODAY) == TODAY
        assert normalize_date("昨天", None, TODAY) == date(2026, 9, 25)
        assert normalize_date("大前天", None, TODAY) == date(2026, 9, 23)
        assert normalize_date("3天前", None, TODAY) == date(2026, 9, 23)

    def test_month_day_without_year(self):
        """今年 9 月 26 日问「8月5号」→ 今年 8 月 5 日"""
        assert normalize_date("8月5号", None, TODAY) == date(2026, 8, 5)

    def test_fallback_to_today(self):
        assert normalize_date(None, None, TODAY) == TODAY
        assert normalize_date("外星语", None, TODAY) == TODAY
