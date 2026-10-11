"""会员模块数据访问 — user_membership / ai_usage_daily / membership_codes

实现规格：docs/membership-plan.md §4.2 / 10-实现骨架.md §七。

约定（实现时必须遵守）：
- 会员生效判定是"惰性"的：tier==1 且 expires_at > NOW() 才算会员，过期**不写库**，
  查询时判定即可——所有配额判断只走 get_tier() 单一入口，勿在别处自行比较 expires_at；
- 每日用量按 (user_id, usage_date) 唯一键 MySQL upsert（sqlalchemy.dialects.mysql.insert），
  跨天自然归零，无需定时任务；kind 必须过白名单、n 必须 int() 后再拼 text()；
- 兑换码核销必须 SELECT ... FOR UPDATE 行锁，状态置 1 与会员期 UPSERT 同一事务；
- 会员期叠加语义：base = max(NOW, 现有 expires_at 且 tier==1)，不覆盖未到期的剩余天数；
- 权益数值口径全部来自 config.settings.MEMBERSHIP_PLANS，本模块不硬编码额度。
"""

import secrets
from datetime import date, datetime

from sqlalchemy import func, select, text, update
from sqlalchemy.dialects.mysql import insert as mysql_insert
from sqlalchemy.ext.asyncio import AsyncSession

from crud import user as user_crud
from models.membership import AiUsageDaily, MembershipCode, UserMembership

# 兑换码字母表：去除 0/O/1/I 防手抄歧义（用户手抄场景多）
_CODE_ALPHABET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"

# 用量字段白名单：incr_usage / check_quota 的 kind 合法值
_USAGE_FIELDS = {"chat": "chat_count", "analyze": "analyze_count", "bookkeeping": "bookkeeping_count"}


def normalize_code(raw: str) -> str:
    """用户输入归一化：去空格/连字符、去首尾空白、转大写。

    兼容用户从聊天工具粘贴的 `MP-XXXX-XXXX-XXXX` 分组形态。
    """
    return (raw or "").replace(" ", "").replace("-", "").strip().upper()


def _gen_code() -> str:
    """生成一张 16 位兑换码；字符表无 0/O/1/I（防用户手抄歧义）"""
    return "".join(secrets.choice(_CODE_ALPHABET) for _ in range(16))


# ── 等级判定 ────────────────────────────────────────────────────────────

async def get_membership_row(db: AsyncSession, user_id: int) -> UserMembership | None:
    """查会员行（不判过期）。免费用户可以没有行，故返回 None 是正常情况。"""
    return (await db.execute(
        select(UserMembership).where(UserMembership.user_id == user_id)
    )).scalars().first()


async def get_effective_membership(db: AsyncSession, user_id: int) -> UserMembership | None:
    """生效会员记录：不存在 / tier!=1 / 已过期 → None（免费）。

    过期**不写库**：查询时判定即可，省掉一个定时任务（docs/membership-plan.md §0.2）。
    到期比较交给 DB 的 NOW()：expires_at 由 DATE_ADD(NOW(),…) 写入（DB 时钟），
    若用应用侧 datetime.now() 比较，两台机器时区/钟差会导致会员提前或延后失效。
    """
    return (await db.execute(
        select(UserMembership).where(
            UserMembership.user_id == user_id,
            UserMembership.tier == 1,
            UserMembership.expires_at.is_not(None),
            UserMembership.expires_at > func.now(),
        )
    )).scalars().first()


async def get_tier(db: AsyncSession, user_id: int) -> int:
    """生效等级 0/1 —— 所有配额判断的唯一入口（AI 闸门也只调它）。"""
    return 1 if await get_effective_membership(db, user_id) else 0


# ── 每日用量 ────────────────────────────────────────────────────────────

async def get_usage_row(db: AsyncSession, user_id: int, today=None) -> AiUsageDaily | None:
    """查当日用量行（today 缺省 date.today()）；无行返回 None（调用方按 0 组包）。"""
    d = today or date.today()
    return (await db.execute(
        select(AiUsageDaily).where(
            AiUsageDaily.user_id == user_id, AiUsageDaily.usage_date == d
        )
    )).scalars().first()


async def check_quota(db: AsyncSession, user_id: int, plan: dict, kind: str) -> tuple[bool, int, int]:
    """配额校验（不写库）：返回 (是否还有额度, 今日已用, 上限)。

    kind 由调用方保证合法（白名单键）；上限口径来自 plan[f"daily_{kind}"]。

    ⚠️ 只读、不占额度：**不要**用「check_quota 通过 → 再 incr_usage」这种两步写法做闸门，
    并发请求会全部读到同一个旧值而放行超额请求；要占额度请用 consume_quota（单语句原子）。
    """
    field = _USAGE_FIELDS[kind]
    limit = plan[f"daily_{kind}"]
    row = await get_usage_row(db, user_id)
    used = getattr(row, field) if row is not None else 0
    return used < limit, used, limit


async def consume_quota(db: AsyncSession, user_id: int, plan: dict, kind: str) -> tuple[bool, int, int]:
    """原子占用一次配额：返回 (是否准入, 今日已用, 上限)。

    闸门必须用本函数而不是 check_quota + incr_usage：
    「先读后写」在并发下所有请求都读到同一个旧计数（InnoDB 一致性读不阻塞），
    `used < limit` 全部为真 → 一次并发风暴可以把日额度冲到任意大（配额形同虚设）。
    这里两步都是单语句原子的：
      1) no-op UPSERT 确保当日行存在（顺带取得行锁，首次并发也不会撞唯一键）；
      2) `UPDATE ... WHERE col < limit`：rowcount==1 即准入，==0 即超额。
    末尾 commit 立即释放行锁，并落实文档 §0.6「计数即扣、LLM 失败不回滚」的取舍。
    """
    if kind not in _USAGE_FIELDS:
        raise ValueError(f"illegal usage kind: {kind}")
    col = _USAGE_FIELDS[kind]
    limit = plan[f"daily_{kind}"]
    today = date.today()
    field_attr = getattr(AiUsageDaily, col)

    # 1) 确保当日行存在（已存在则把计数写回自身，不改数值、仅取行锁）
    ensure = mysql_insert(AiUsageDaily).values(
        user_id=user_id, usage_date=today, **{col: 0}
    ).on_duplicate_key_update(**{col: text(f"{AiUsageDaily.__tablename__}.{col}")})
    await db.execute(ensure)

    # 2) 条件自增：只有未达上限才 +1（单语句原子，rowcount 即准入结果）
    result = await db.execute(
        update(AiUsageDaily)
        .where(
            AiUsageDaily.user_id == user_id,
            AiUsageDaily.usage_date == today,
            field_attr < limit,
        )
        .values(**{col: field_attr + 1})
    )
    admitted = result.rowcount == 1

    used = (await db.execute(
        select(field_attr).where(
            AiUsageDaily.user_id == user_id, AiUsageDaily.usage_date == today
        )
    )).scalar_one_or_none() or 0
    await db.commit()
    return admitted, used, limit


async def incr_usage(db: AsyncSession, user_id: int, kind: str, n: int = 1) -> None:
    """当日用量 +n（MySQL upsert，不 commit：随请求事务由 get_db 统一提交）。

    计数时机 = 实际触发 LLM 之前，调用失败不回滚——防刷量优先（industry 惯例）。
    kind 必须过白名单、n 必须 int()，之后才可拼进 text()（否则是注入口）。

    ⚠️ 累加表达式必须用**表名限定** `ai_usage_daily.<col>`：SQLAlchemy 2.0 生成的
    `INSERT ... AS new ON DUPLICATE KEY UPDATE` 里，「目标表列」与「新行别名列」
    同名，写裸 `col + n` 会被 MySQL 判为 ambiguous（1052）；membership-plan §4.2
    的参考实现未限定，实测直接报错（见交付说明「修正点 1」）。
    """
    if kind not in _USAGE_FIELDS:
        raise ValueError(f"illegal usage kind: {kind}")
    col = _USAGE_FIELDS[kind]
    stmt = mysql_insert(AiUsageDaily).values(
        user_id=user_id, usage_date=date.today(), **{col: int(n)}
    )
    # on_duplicate_key_update：同一 (user_id, usage_date) 累加，跨天自然归零
    stmt = stmt.on_duplicate_key_update(
        **{col: text(f"{AiUsageDaily.__tablename__}.{col} + {int(n)}")}
    )
    await db.execute(stmt)


# ── 兑换码 ──────────────────────────────────────────────────────────────

async def generate_codes(
    db: AsyncSession, count: int, days: int, batch_no: str | None = None
) -> list[MembershipCode]:
    """批量生成兑换码（count 1-500、days 1-3650 由 schema 层校验）。

    去重三道防线：候选池内去重 + 库内**批量**预查 + 唯一键
    uk_membership_codes_code 兜底（极端并发下由 DB 拒绝，不静默串码）。

    性能：历史实现是「生成一个码 → 查一次库」的逐条循环，count=500 时最多
    500 次 DB 往返；改为「按批生成候选 → 一次 IN 查库过滤」，往返次数降为 1~2 次。
    """
    batch = batch_no or datetime.now().strftime("%Y%m%d%H%M%S")
    picked: list[str] = []
    picked_set: set[str] = set()

    while len(picked) < count:
        # 候选池：一次凑够剩余所需数量（_gen_code 空间 32^16，池内碰撞概率可忽略）
        pool: set[str] = set()
        need = count - len(picked)
        while len(pool) < need:
            pool.add(_gen_code())
        pool -= picked_set
        if not pool:
            continue
        # 一次 IN 查库，剔除库中已存在的码（替代逐条 SELECT 的 N+1）
        existing = set((await db.execute(
            select(MembershipCode.code).where(MembershipCode.code.in_(pool))
        )).scalars().all())
        for code in pool - existing:
            if len(picked) >= count:
                break
            picked.append(code)
            picked_set.add(code)

    rows = [MembershipCode(code=c, days=days, status=0, batch_no=batch) for c in picked]
    db.add_all(rows)
    await db.commit()
    # 回读主键与 DB 侧默认值（created_at 由 DDL CURRENT_TIMESTAMP 填充）：
    # 一条 IN 查询替代逐行 refresh，也避免 async 下直接读未加载列触发隐式懒加载
    ids = [row.id for row in rows]
    return list((await db.execute(
        select(MembershipCode).where(MembershipCode.id.in_(ids)).order_by(MembershipCode.id.asc())
    )).scalars().all())


async def list_codes(
    db: AsyncSession, page: int = 1, size: int = 20, status: int | None = None
) -> dict:
    """兑换码分页列表（id 倒序）；status ∈ (0,1,2) 或 None=全部。

    返回 {"rows": [...], "total": n}，由路由层组 PageResult。
    """
    conditions = []
    if status is not None:
        conditions.append(MembershipCode.status == status)

    total = (await db.execute(
        select(func.count(MembershipCode.id)).where(*conditions)
    )).scalar_one()
    rows = (await db.execute(
        select(MembershipCode)
        .where(*conditions)
        .order_by(MembershipCode.id.desc())
        .offset((page - 1) * size)
        .limit(size)
    )).scalars().all()
    return {"rows": rows, "total": total}


async def list_user_redemptions(
    db: AsyncSession, user_id: int, page: int = 1, size: int = 20
) -> dict:
    """普通用户的兑换记录：该用户核销过的兑换码（体验资格来源），id 倒序分页。

    只取 status=1（已核销）且 used_by==user_id 的行——这是「我的体验资格从哪来」
    的唯一可查来源；未使用/已作废的码与用户无关，不返回。

    返回 {"rows": [...], "total": n}，由路由层组 PageResult。
    """
    conditions = (MembershipCode.used_by == user_id, MembershipCode.status == 1)
    total = (await db.execute(
        select(func.count(MembershipCode.id)).where(*conditions)
    )).scalar_one()
    rows = (await db.execute(
        select(MembershipCode)
        .where(*conditions)
        .order_by(MembershipCode.id.desc())
        .offset((page - 1) * size)
        .limit(size)
    )).scalars().all()
    return {"rows": rows, "total": total}


async def void_code(db: AsyncSession, code_id: int) -> tuple[bool, str]:
    """作废：仅未使用（status=0）可作废。返回 (ok, 中文提示)。

    同样取行锁：否则「一致性读看到 status=0 → 随后 UPDATE」会在并发的 redeem 提交后
    把已核销的码覆盖成 status=2，出现「已作废 + used_by 有值」的自相矛盾状态。
    """
    row = (await db.execute(
        select(MembershipCode).where(MembershipCode.id == code_id).with_for_update()
    )).scalars().first()
    if row is None:
        return False, "兑换码不存在"
    if row.status == 1:
        return False, "已使用的兑换码不能作废"
    if row.status == 2:
        return False, "该兑换码已作废"
    row.status = 2
    await db.commit()
    return True, "已作废"


def _extend_membership_stmt(user_id: int, days: int, source: int):
    """会员期叠加的原子 UPSERT 语句（MySQL）。

    语义即文档要求的「会员期 UPSERT（同一事务）」：
      - 无行 → INSERT tier=1, expires_at = NOW() + days；
      - 有行 → expires_at = max(NOW, 现有 expires_at) + days（未到期续费不损失剩余天数）。

    ⚠️ 为什么必须由 SQL 完成叠加：用「普通 SELECT 读 → Python 算 → UPDATE 写回」时，
    两个并发事务会读到同一个旧 expires_at（InnoDB 一致性读不阻塞），后提交者覆盖前者
    → 兑换码已核销、会员天数却只加了一次（真金白银的天数丢失）；首次并发开通还会双双
    INSERT 撞 uk_membership_user 抛 IntegrityError。
    列名用表名限定：SQLAlchemy 生成的 `INSERT ... AS new ON DUPLICATE KEY UPDATE`
    带行别名，裸列名会被 MySQL 判为 ambiguous（1052）。
    days 只来自 schema 校验的 int 或库列 int，int() 后拼字面量，无注入面。
    """
    days = int(days)
    stmt = mysql_insert(UserMembership).values(
        user_id=user_id,
        tier=1,
        source=source,
        expires_at=text(f"DATE_ADD(NOW(), INTERVAL {days} DAY)"),
    )
    return stmt.on_duplicate_key_update(
        tier=1,
        source=source,
        expires_at=text(
            "DATE_ADD(GREATEST(COALESCE(user_membership.expires_at, NOW()), NOW()), "
            f"INTERVAL {days} DAY)"
        ),
        # create_all 出来的表没有 ON UPDATE CURRENT_TIMESTAMP（onupdate 是客户端行为），
        # 显式写入保证两种建表来源下 updated_at 都正确
        updated_at=func.now(),
    )


async def redeem_code(db: AsyncSession, user_id: int, raw: str) -> tuple[bool, str, UserMembership | None]:
    """兑换码核销（行锁防并发重复核销）。返回 (ok, 中文提示, 生效后的会员行)。

    核销与会员期叠加在**同一事务**：状态置 1 + used_by/used_at + 会员期 UPSERT，
    中间失败不留下"码已用但会员未开"的半成品。
    """
    code = normalize_code(raw)
    if not code:
        return False, "请输入兑换码", None

    # SELECT ... FOR UPDATE：同一码并发提交时只有一个事务能拿到行锁，另一个读到 status=1
    row = (await db.execute(
        select(MembershipCode).where(MembershipCode.code == code).with_for_update()
    )).scalars().first()
    if row is None:
        return False, "兑换码不存在", None
    if row.status == 1:
        return False, "该兑换码已被使用", None
    if row.status == 2:
        return False, "该兑换码已作废", None

    row.status = 1
    row.used_by = user_id
    row.used_at = func.now()    # 与会员期写入同一 DB 时钟，避免应用/DB 钟差

    # 叠加语义：未到期则从现有到期时间续，不吞掉剩余天数；已过期/免费从 NOW 起算
    # （整段由一条 UPSERT 完成，见 _extend_membership_stmt）
    await db.execute(_extend_membership_stmt(user_id, row.days, source=0))
    await db.commit()

    membership = await get_membership_row(db, user_id)
    return True, f"兑换成功，会员已延长 {row.days} 天", membership


# ── 管理端开通 ──────────────────────────────────────────────────────────

async def grant_membership(db: AsyncSession, user_id: int, days: int) -> UserMembership | None:
    """管理员开通/延期：source=1，叠加语义同 redeem。用户不存在返回 None（路由转 404）。"""
    if await user_crud.get_user_by_id(db, user_id) is None:
        return None

    await db.execute(_extend_membership_stmt(user_id, days, source=1))
    await db.commit()
    return await get_membership_row(db, user_id)


async def extend_membership_for_recharge(db: AsyncSession, user_id: int, days: int) -> None:
    """充值订单入账专用：source=2，叠加语义与 redeem/grant 完全一致（单一来源）。

    刻意不 commit——充值侧必须把「订单状态流转 + 审计留痕 + 会员延期」作为同一事务
    提交，中途失败不留"钱已收、会员未开"的半成品（与 redeem_code 同一事务原则）。
    """
    await db.execute(_extend_membership_stmt(user_id, days, source=2))
