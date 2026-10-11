"""ai.category_alias 单元测试 — 分类映射（含「今日用餐」误判回归）

纯函数、无 LLM/DB 依赖，直接用轻量假对象替代 ORM 行。
"""

import types

import pytest

from ai.category_alias import ALIAS, MATCH_MIN_LEN, resolve_category


def cat(name, cid=1, ctype=0):
    """假分类行（只需 .name / .id / .type）"""
    return types.SimpleNamespace(name=name, id=cid, type=ctype)


# 典型分类集合：系统预设 6 类 + 一个易混淆的自定义类
SYSTEM = [cat("餐饮", 1), cat("交通", 2), cat("日用", 3),
          cat("居住", 4), cat("通讯", 5), cat("娱乐", 6)]
SYSTEM_WITH_OTHERS = SYSTEM + [cat("其他", 99)]


class TestExactMatch:
    def test_exact_hit(self):
        got, fb = resolve_category("餐饮", SYSTEM)
        assert got.name == "餐饮" and fb is False

    def test_user_category_wins_by_order(self):
        """列表顺序 = 自定义在前，精确匹配应取到用户自定义那份"""
        custom = cat("宠物", 20)
        got, fb = resolve_category("宠物", [custom] + SYSTEM)
        assert got is custom and fb is False

    def test_none_name_falls_back(self):
        got, fb = resolve_category(None, SYSTEM)
        assert got is None and fb is True

    def test_blank_name_falls_back(self):
        assert resolve_category("   ", SYSTEM) == (None, True)

    def test_empty_category_list(self):
        assert resolve_category("餐饮", []) == (None, True)


class TestAliasMatch:
    @pytest.mark.parametrize("alias,expect", [
        ("午饭", "餐饮"), ("打车", "交通"), ("买菜", "日用"), ("房租", "居住"),
    ])
    def test_common_aliases(self, alias, expect):
        got, fb = resolve_category(alias, SYSTEM_WITH_OTHERS)
        assert got.name == expect and fb is False

    def test_alias_extension_covers_today_meal(self):
        """LLM 直接吐出「今日用餐」也应正确落到餐饮"""
        got, fb = resolve_category("今日用餐", SYSTEM_WITH_OTHERS)
        assert got.name == "餐饮" and fb is False

    def test_red_packet_needs_income_category_to_exist(self):
        """「红包」映射到「收入」；分类表里没有「收入」时应兜底而非硬塞"""
        got, fb = resolve_category("红包", SYSTEM_WITH_OTHERS)
        assert got is None and fb is True


class TestRegressionInteriorSubstring:
    """核心回归：中间子串不得命中

    历史实现 ``cat.name in target or target in cat.name`` 会把
    「今日用餐」判成「日用」（日用是今日用餐的中间子串）。
    """

    def test_today_meal_not_matched_as_daily_use(self):
        """「今日用餐」应判为餐饮（或兜底），**绝不能**是日用"""
        got, _ = resolve_category("今日用餐", SYSTEM_WITH_OTHERS)
        assert got is None or got.name != "日用", "「日用」是中间子串，不该命中"

    def test_interior_substring_rejected(self):
        """「我看日用百货」：日用在中间，无别名可用，应兜底而不是误命中"""
        cats = [cat("餐饮", 1), cat("日用", 3)]   # 刻意不含「其他」，排除别名干扰
        got, fb = resolve_category("我看日用百货", cats)
        assert got is None and fb is True

    def test_anchor_words_still_hit(self):
        """对照组：日用出现在开头/结尾时仍应命中，证明不是把模糊匹配整体关掉了"""
        assert resolve_category("日用品采买", [cat("日用", 3)])[0].name == "日用"
        assert resolve_category("采购日用", [cat("日用", 3)])[0].name == "日用"

    def test_single_char_category_not_used(self):
        """单字分类名不参与模糊匹配，否则「餐」会命中一切"""
        single = cat("餐", 30)
        got, fb = resolve_category("今天吃饭", [single] + SYSTEM_WITH_OTHERS)
        assert got is None or got.name != "餐"

    def test_match_min_len_is_two(self):
        assert MATCH_MIN_LEN == 2


class TestAnchoredMatch:
    def test_category_as_prefix_hits(self):
        got, fb = resolve_category("宠物用品", [cat("宠物", 20)] + SYSTEM_WITH_OTHERS)
        assert got.name == "宠物" and fb is False

    def test_category_as_suffix_hits(self):
        got, fb = resolve_category("超市宠物", [cat("宠物", 20)] + SYSTEM_WITH_OTHERS)
        assert got.name == "宠物" and fb is False

    def test_longest_candidate_wins(self):
        """同时命中多个时取最具体（名字最长）的那个"""
        cats = [cat("交通", 2), cat("交通罚款", 21)]
        got, _ = resolve_category("交通罚款", cats)
        assert got.name == "交通罚款"


class TestAliasPrefixExtension:
    def test_longer_phrase_with_alias_prefix(self):
        """目标「买菜水果」：别名「买菜」→ 规范名「日用」"""
        got, fb = resolve_category("买菜水果", SYSTEM_WITH_OTHERS)
        assert got.name == "日用" and fb is False

    def test_alias_prefix_does_not_override_exact(self):
        """精确匹配优先级最高，不能被别名前缀扩展抢走"""
        user_cat = cat("买菜", 22)
        got, _ = resolve_category("买菜", [user_cat] + SYSTEM_WITH_OTHERS)
        assert got is user_cat


class TestIncomeDirection:
    """收支类型相关别名：报销/退款/理财收益属收入"""

    @pytest.mark.parametrize("word", ["报销", "退款", "理财收益", "利息"])
    def test_income_aliases_present(self, word):
        assert ALIAS.get(word) == "收入"

    def test_income_word_resolves_when_category_exists(self):
        cats = SYSTEM_WITH_OTHERS + [cat("收入", 7, ctype=1)]
        got, fb = resolve_category("报销", cats)
        assert got.name == "收入" and fb is False