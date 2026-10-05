"""分类解析 — 把 LLM 给出的分类名映射到用户实际分类（06 §11.5）

优先级：用户自定义精确匹配 → 系统预设精确匹配 → 别名词典 → 模糊包含 → 兜底「其他」。
resolve_category 返回 (命中分类或 None, 是否走了兜底)；None 时调用方
归入「其他」分类并附 warning。
"""

# 口语 → 标准分类 别名词典（可按需扩充）
ALIAS: dict[str, str] = {
    "吃饭": "餐饮", "早饭": "餐饮", "午饭": "餐饮", "晚饭": "餐饮", "晚餐": "餐饮",
    "外卖": "餐饮", "下馆子": "餐饮", "聚餐": "餐饮", "烤肉": "餐饮", "火锅": "餐饮",
    "打车": "交通", "地铁": "交通", "公交": "交通", "出租车": "交通", "滴滴": "交通",
    "加油": "交通", "停车": "交通", "火车": "交通", "机票": "交通", "高铁": "交通",
    "看电影": "娱乐", "电影": "娱乐", "游戏": "娱乐", "KTV": "娱乐", "旅游": "娱乐",
    "买菜": "日用", "日用品": "日用", "纸巾": "日用", "洗发水": "日用",
    "话费": "通讯", "流量": "通讯", "网费": "通讯",
    "房租": "居住", "水电": "居住", "物业": "居住",
    "工资": "收入", "奖金": "收入", "红包": "收入",
}


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

    # 3) 模糊包含（用户分类名出现在目标词中，如目标「打车去公司」含「交通」之外的「打车」已走别名）
    for cat in user_categories:
        if cat.name and (cat.name in target or target in cat.name):
            return cat, False

    # 4) 兜底：由调用方归入「其他」
    return None, True
