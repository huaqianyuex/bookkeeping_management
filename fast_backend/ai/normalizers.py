"""记账字段归一化 — 金额/日期的规则级清洗（06 §11.3-11.5）

纯函数、不调 LLM：LLM（bookkeeping_chain）负责抽取，本模块负责校验与兜底。
- normalize_amount：LLM 已给数则校验范围 (0, 99999999.99]；没给则从原文按
  阿拉伯数字/中文数字再抓一次；仍失败返回 None（触发 clarify 追问，不猜测）。
- normalize_date：优先 LLM 转好的 ISO；否则解析常见相对词（今天/昨天/前天/
  大前天/N天前/本周X/上周X/M月D号）；未指定年份且结果晚于今天则年份-1；
  全失败回落 today。
"""
import re
from datetime import date, timedelta

MAX_AMOUNT = 99_999_999.99

# 中文数字映射（个位 + 十位组合，覆盖「七十九」「两」等口语写法）
_CN_DIGIT = {"零": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5,
             "六": 6, "七": 7, "八": 8, "九": 9}
_WEEKDAY = {"一": 0, "二": 1, "三": 2, "四": 3, "五": 4, "六": 5, "日": 6, "天": 6}

_RE_ARABIC = re.compile(r"(\d+(?:,\d{3})*(?:\.\d+)?)\s*(?:万)?[块块钱元¥rmbRMB]?")
_RE_WAN = re.compile(r"(\d+(?:\.\d+)?)\s*万\s*([一二三四五六七八九0-9]*)?")
_RE_CN = re.compile(r"([一二两三四五六七八九]{0,1}十[一二三四五六七八九]{0,1}|[一二两三四五六七八九])[块块钱元]")


def _cn_to_int(text: str) -> int | None:
    """「七十九」→79、「两」→2；不支持百以上（交给 LLM）"""
    if not text:
        return None
    if "十" in text:
        tens, _, ones = text.partition("十")
        t = _CN_DIGIT.get(tens, 1) if tens else 1
        o = _CN_DIGIT.get(ones, 0) if ones else 0
        return t * 10 + o
    if len(text) == 1:
        return _CN_DIGIT.get(text)
    return None


def _clip(amount: float) -> float | None:
    """范围校验：0 < amount <= 99999999.99，保留 2 位"""
    if amount <= 0 or amount > MAX_AMOUNT:
        return None
    return round(amount, 2)


def normalize_amount(amount_raw: str | None, parsed: float | None) -> float | None:
    """返回归一化金额；无法确定返回 None（调用方触发追问）"""
    # 1) LLM 已给数：直接校验范围
    if parsed is not None:
        return _clip(float(parsed))

    # 2) 从原文抓取
    if amount_raw:
        m = _RE_WAN.search(amount_raw)          # 1万2 → 12000
        if m:
            whole = float(m.group(1).replace(",", ""))
            tail_text = m.group(2) or ""
            if tail_text.isdigit():
                tail = int(tail_text)
            else:
                tail = _cn_to_int(tail_text) or 0
            return _clip(whole * 10000 + tail * 1000)
        m = _RE_ARABIC.search(amount_raw)       # 79 / 79.5 / 1,200
        if m:
            return _clip(float(m.group(1).replace(",", "")))
        m = _RE_CN.search(amount_raw)           # 七十九块
        if m:
            n = _cn_to_int(m.group(1))
            if n is not None:
                return _clip(float(n))
    return None


def normalize_date(date_expr: str | None, parsed_iso: str | None, today: date) -> date:
    """返回记账日期；解析失败一律回落 today"""
    # 1) LLM 已转好 ISO：直接用
    if parsed_iso:
        try:
            d = date.fromisoformat(parsed_iso)
            if d > today:                       # 未来日期且未显式带未来语义 → 年份-1
                return d.replace(year=d.year - 1)
            return d
        except ValueError:
            pass

    if not date_expr:
        return today
    expr = date_expr.strip()

    if expr == "今天":
        return today
    if expr == "昨天":
        return today - timedelta(days=1)
    if expr == "前天":
        return today - timedelta(days=2)
    if expr == "大前天":
        return today - timedelta(days=3)

    m = re.fullmatch(r"(\d+)\s*天前", expr)     # 3天前
    if m:
        return today - timedelta(days=int(m.group(1)))

    m = re.fullmatch(r"(?:本|这)周([一二三四五六日天])", expr)   # 本周三
    if m:
        delta = (today.weekday() - _WEEKDAY[m.group(1)]) % 7
        return today - timedelta(days=delta)

    m = re.fullmatch(r"上周([一二三四五六日天])", expr)          # 上周三
    if m:
        delta = (today.weekday() - _WEEKDAY[m.group(1)]) % 7
        return today - timedelta(days=delta + 7)

    m = re.fullmatch(r"(\d{1,2})月(\d{1,2})[号日]?", expr)      # 3月5号
    if m:
        try:
            d = date(today.year, int(m.group(1)), int(m.group(2)))
            if d > today:                       # 未指定年份且晚于今天 → 年份-1
                d = d.replace(year=d.year - 1)
            return d
        except ValueError:
            return today

    return today
