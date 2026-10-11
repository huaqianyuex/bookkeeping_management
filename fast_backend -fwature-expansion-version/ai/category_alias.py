"""分类解析 — 把 LLM 给出的分类名映射到用户实际分类（06 §11.5）

优先级：用户自定义精确匹配 → 系统预设精确匹配 → 别名词典 → **首尾锚定模糊匹配** → 兜底「其他」。
resolve_category 返回 (命中分类或 None, 是否走了兜底)；None 时调用方
归入「其他」分类并附 warning。

⚠️ 模糊匹配为什么不能用「双向子串包含」
------------------------------------
历史实现是 ``cat.name in target or target in cat.name``，双向包含会制造
大量误判。实测最典型的一条：

    LLM 抽取目标词 = 「今日用餐」，系统存在分类「日用」
    「日用」是「今日用餐」的**中间子串**（今[日用]餐）→ 命中「日用」
    结果：一顿正餐被记成日用品，分类污染且用户不易察觉。

反向包含同样危险：分类「餐饮」遇到目标词「餐」会被单字命中。

本实现的判定规则（`MATCH_MIN_LEN` / 首尾锚定）：

1. 候选分类名长度必须 ≥ ``MATCH_MIN_LEN``（默认 2），单字分类不参与模糊匹配，
   避免「餐」「玩」这类单字命中一切；
2. 候选分类名必须出现在目标词的**开头或结尾**（首尾锚定），中间子串不算命中
   ——「今日用餐」里的「日用」是中间子串，故被拒绝；
3. 多个候选同时命中时取**名字最长**者（最具体优先）。

命中不了的宁可归入「其他」并附 warning 交给用户核对，也不猜错分类。
"""

# 口语 → 标准分类 别名词典（可按需扩充）
ALIAS: dict[str, str] = {
    "吃饭": "餐饮", "早饭": "餐饮", "午饭": "餐饮", "晚饭": "餐饮", "晚餐": "餐饮",
    "外卖": "餐饮", "下馆子": "餐饮", "聚餐": "餐饮", "烤肉": "餐饮", "火锅": "餐饮",
    "早餐": "餐饮", "午餐": "餐饮", "晚餐": "餐饮", "夜宵": "餐饮", "小吃": "餐饮",
    "今日用餐": "餐饮", "今天吃饭": "餐饮", "吃饭了吗": "餐饮", "食堂": "餐饮",
    "打车": "交通", "地铁": "交通", "公交": "交通", "出租车": "交通", "滴滴": "交通",
    "加油": "交通", "停车": "交通", "火车": "交通", "机票": "交通", "高铁": "交通",
    "共享单车": "交通", "单车": "交通", "轮渡": "交通", "过路费": "交通", "洗车": "交通",
    "看电影": "娱乐", "电影": "娱乐", "游戏": "娱乐", "KTV": "娱乐", "旅游": "娱乐",
    "演唱会": "娱乐", "景点": "娱乐", "门票": "娱乐", "会员订阅": "娱乐",
    "买菜": "日用", "日用品": "日用", "纸巾": "日用", "洗发水": "日用",
    "超市": "日用", "便利店": "日用", "生活用品": "日用", "洗护": "日用",
    "话费": "通讯", "流量": "通讯", "网费": "通讯", "宽带": "通讯", "充值话费": "通讯",
    "房租": "居住", "水电": "居住", "物业": "居住",
    "房贷": "居住", "取暖费": "居住", "燃气费": "居住", "中介费": "居住",
    "工资": "收入", "奖金": "收入", "红包": "收入",
    "报销": "收入", "退款": "收入", "理财收益": "收入", "利息": "收入", "转入": "收入",
}

# 参与模糊匹配的最短分类名长度；单字分类（如「餐」「玩」）不参与，避免误命中
MATCH_MIN_LEN = 2


def _anchor_match(cat_name: str, target: str) -> bool:
    """首尾锚定匹配：分类名出现在目标词的开头或结尾即算命中。

    返回 False 的典型：目标「今日用餐」中的「日用」（中间子串）。
    """
    if len(cat_name) < MATCH_MIN_LEN:
        return False
    return target.startswith(cat_name) or target.endswith(cat_name)


def resolve_category(name: str | None, user_categories: list) -> tuple[object | None, bool]:
    """解析分类。

    user_categories: 当前用户的分类 ORM 列表（含系统预设 user_id IS NULL 的，
    由调用方提前合并好），元素需有 .name 与 .id 属性。
    返回 (category | None, fallback)；fallback=True 表示未精确命中，
    调用方应附 warning 并归入「其他」。
    """
    if not user_categories:
        return None, True
    if not name:
        return None, True

    target = name.strip()
    if not target:
        return None, True

    # 1) 精确匹配（用户自定义优先——列表顺序由调用方保证：自定义在前）
    for cat in user_categories:
        if cat.name == target:
            return cat, False

    # 2) 别名词典 → 再精确匹配一次
    canonical = ALIAS.get(target)
    if canonical:
        for cat in user_categories:
            if cat.name == canonical:
                return cat, False

    # 3) 首尾锚定模糊匹配；多个候选取名字最长的（最具体优先）
    #    ⚠️ 不要再写 `cat.name in target`（中间子串）——会把「今日用餐」判成「日用」
    candidates = [c for c in user_categories
                  if c.name and _anchor_match(c.name.strip(), target)]
    if candidates:
        return max(candidates, key=lambda c: len(c.name.strip())), False

    # 4) 别名词典的前缀扩展：目标词比别名词更长时，用「别名词 + 尾部修饰」匹配
    #    如目标「买菜水果」→ 别名「买菜」→ 规范名「日用」
    #    ⚠️ 必须排在第 3 步之后：否则「超市宠物」会被「超市→日用」劫持，
    #    而用户明明有个叫「宠物」的分类，应优先命中它。
    if len(target) > 2:
        for alias, canonical_name in ALIAS.items():
            if len(alias) >= MATCH_MIN_LEN and target.startswith(alias):
                for cat in user_categories:
                    if cat.name == canonical_name:
                        return cat, False

    # 5) 兜底：由调用方归入「其他」
    return None, True