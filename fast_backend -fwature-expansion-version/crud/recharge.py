"""充值模块数据访问 — recharge_orders / recharge_audit_logs

设计规格：docs/fastapi-backend/11-充值与审批模块.md。

订单状态机（status）——所有流转必须经 apply_payment_callback / approve / reject /
cancel / 懒关闭，其余任何写路径不存在：
    0 待支付 ──支付成功+风控通过──→ 2 已支付（同事务延期会员，source=2）
    0 待支付 ──支付成功+命中风控──→ 1 待审批（钱已收，等管理员放行到账）
    0 待支付 ──用户取消──────────→ 4 已取消
    0 待支付 ──超时（读/支付路径懒关闭）→ 5 已关闭
    1 待审批 ──管理员通过────────→ 2 已支付（同事务延期会员）
    1 待审批 ──管理员拒绝（原因必填）──→ 3 已拒绝
    其余流转一律拒绝。

防绕过链路（每笔订单必经，缺一不可）：
    ① 登录态 + 归属校验（路由层 get_current_user / user_id 比对）
    ② 服务端定价（下单只收 planId，金额/天数取自 RECHARGE_PLANS 快照）
    ③ 创建频率限流（进程内滑动窗口）+ 进行中订单幂等上限
    ④ 支付事件必须经 build_payment_event 验签（HMAC）才能进状态机——类型层面封死
       "未验签入账"；金额与订单应收核对防网关侧改单
    ⑤ 状态推进前 SELECT ... FOR UPDATE 行锁，并发下同一订单只入账一次（回调重放无害）
    ⑥ 每次流转与审计日志同一事务写入，管理员审批需 role=1（get_current_admin）

约定：
- 金额全链路 Decimal（DECIMAL(10,2) ↔ Decimal ↔ 字符串出参），禁 float；
- 时间比较用 DB NOW()（与会员模块同口径，避免应用/DB 钟差）；会员过期判定是惰性的，
  本模块不改 user_membership 的过期逻辑，入账统一走 membership_crud 单一入口；
- 风控阈值不下发前端（防探测拆单），命中规则只进 risk_flags 与审计 detail。
"""

import secrets
from datetime import datetime
from decimal import Decimal

from sqlalchemy import func, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import (
    RECHARGE_DAILY_REVIEW_AMOUNT,
    RECHARGE_MANUAL_REVIEW_AMOUNT,
    RECHARGE_MAX_PENDING_ORDERS,
    RECHARGE_ORDER_TTL_SECONDS,
    RECHARGE_PAY_FAIL_COOLDOWN_SECONDS,
    RECHARGE_PAY_FAIL_LIMIT,
    RECHARGE_PLANS,
    RECHARGE_RATE_MAX_CREATE,
    RECHARGE_RATE_WINDOW_SECONDS,
)
from crud import membership as membership_crud
from models.recharge import RechargeAuditLog, RechargeOrder
from models.user import User
from utils.recharge_security import PaymentEvent
from utils.security import escape_like
from utils.throttle import LoginThrottle, SlidingWindowRateLimiter

# ---- 状态常量（与 DDL/模型注释同口径，勿改数值）----
STATUS_PENDING_PAY = 0     # 待支付
STATUS_PENDING_REVIEW = 1  # 待审批（支付成功但命中风控，钱已收）
STATUS_PAID = 2            # 已支付（已入账：会员已延期）
STATUS_REJECTED = 3        # 已拒绝（审批不通过，模拟渠道原路退回）
STATUS_CANCELLED = 4       # 已取消（用户主动取消待支付订单）
STATUS_CLOSED = 5          # 超时关闭（未支付懒关闭）

# 风控规则标识（写入 risk_flags，逗号分隔）
RISK_SINGLE_AMOUNT = "SINGLE_AMOUNT"   # 单笔金额 ≥ 单笔阈值
RISK_DAILY_TOTAL = "DAILY_TOTAL"       # 当日累计金额（含本笔）≥ 累计阈值

# 终态集合：进入后不再流转
_FINAL_STATUSES = (STATUS_PAID, STATUS_REJECTED, STATUS_CANCELLED, STATUS_CLOSED)

# ---- 进程内防刷器（单 worker 前提，与 login/voice 限流同一套基建）----
# 创建订单：成功也计数的放行限流（防脚本批量造单刷审计表）
create_rate_limiter = SlidingWindowRateLimiter(
    max_calls=RECHARGE_RATE_MAX_CREATE, window=RECHARGE_RATE_WINDOW_SECONDS
)
# 支付失败：失败累积锁定（防对同一订单暴力重试/探测风控阈值）
pay_fail_throttle = LoginThrottle(
    max_fails=RECHARGE_PAY_FAIL_LIMIT,
    window=600,
    throttle_seconds=RECHARGE_PAY_FAIL_COOLDOWN_SECONDS,
)


def _gen_order_no() -> str:
    """生成订单号：RCH + 时间戳(14) + 6 位随机 hex，共 23 字符（≤32）

    唯一性由 uk_recharge_orders_no 兜底；同秒并发碰撞概率 16^-6，
    create_order 里还有库内预查（与 generate_codes 同一道防线）。
    """
    return "RCH" + datetime.now().strftime("%Y%m%d%H%M%S") + secrets.token_hex(3).upper()


def _audit(db: AsyncSession, order: RechargeOrder, action: str, to_status: int,
           actor_type: int, actor_id: int | None, ip: str | None,
           from_status: int | None = None, detail: str | None = None) -> None:
    """追加一条审计日志（只 db.add 不 commit——与状态流转同一事务提交）"""
    db.add(RechargeAuditLog(
        order_id=order.id,
        order_no=order.order_no,
        actor_type=actor_type,
        actor_id=actor_id,
        action=action,
        from_status=from_status,
        to_status=to_status,
        detail=detail[:500] if detail else None,
        ip=ip,
    ))


async def _close_expired_orders(db: AsyncSession, user_id: int | None = None) -> int:
    """把超时未支付的待支付订单置为已关闭（懒关闭，无定时任务）。

    在创建/列表/详情/支付前调用，保证「进行中订单数」与各列表页看到的状态是新鲜的。
    每单一行 EXPIRE_CLOSE 审计（actor=系统）；有关闭才 commit（释放行锁）。
    """
    conditions = [
        RechargeOrder.status == STATUS_PENDING_PAY,
        RechargeOrder.expires_at.is_not(None),
        RechargeOrder.expires_at <= func.now(),   # DB 时钟判定，避免应用/DB 钟差
    ]
    if user_id is not None:
        conditions.append(RechargeOrder.user_id == user_id)
    rows = (await db.execute(
        select(RechargeOrder).where(*conditions).with_for_update()
    )).scalars().all()
    for row in rows:
        from_status = row.status
        row.status = STATUS_CLOSED
        _audit(db, row, "EXPIRE_CLOSE", STATUS_CLOSED, actor_type=1, actor_id=None,
               ip=None, from_status=from_status, detail="待支付超时，订单自动关闭")
    if rows:
        await db.commit()
    return len(rows)


async def _daily_paid_total(db: AsyncSession, user_id: int) -> Decimal:
    """该用户当日已收款项合计（已支付 + 待审批，按 paid_at 的 DB 日期）。

    待审批订单的钱也已收（只是没放行），计入累计口径才能防"拆单绕过日阈值"。
    """
    total = (await db.execute(
        select(func.coalesce(func.sum(RechargeOrder.amount), 0)).where(
            RechargeOrder.user_id == user_id,
            RechargeOrder.status.in_((STATUS_PAID, STATUS_PENDING_REVIEW)),
            func.date(RechargeOrder.paid_at) == func.curdate(),
        )
    )).scalar_one()
    return Decimal(total)


# ── 下单 ────────────────────────────────────────────────────────────────

async def create_order(
    db: AsyncSession, user_id: int, plan_id: str, ip: str | None
) -> tuple[bool, str, RechargeOrder | None]:
    """创建充值订单（只收 planId——金额/天数由服务端定价并快照，杜绝金额篡改）。

    校验链：套餐存在 → 创建频率限流 → 懒关闭超时单 → 进行中订单幂等上限。
    返回 (ok, 中文提示, 订单)；失败时订单为 None。
    """
    plan = RECHARGE_PLANS.get(plan_id)
    if plan is None:
        return False, "套餐不存在，请刷新后重试", None

    allowed, wait = create_rate_limiter.allow(f"recharge:create:{user_id}")
    if not allowed:
        return False, f"操作过于频繁，请 {wait} 秒后再试", None

    # 先懒关闭本用户超时单，再统计进行中数量（幂等：防同一用户堆 pending 单）
    await _close_expired_orders(db, user_id)
    pending = (await db.execute(
        select(func.count(RechargeOrder.id)).where(
            RechargeOrder.user_id == user_id, RechargeOrder.status == STATUS_PENDING_PAY
        )
    )).scalar_one()
    if pending >= RECHARGE_MAX_PENDING_ORDERS:
        return False, "您已有待支付的订单，请先完成支付或取消", None

    order_no = _gen_order_no()
    # 库内预查防撞（唯一键 uk_recharge_orders_no 兜底，极端并发由 DB 拒绝）
    exists = (await db.execute(
        select(RechargeOrder.id).where(RechargeOrder.order_no == order_no)
    )).first()
    if exists:
        return False, "订单创建冲突，请重试", None

    order = RechargeOrder(
        order_no=order_no,
        user_id=user_id,
        plan_id=plan_id,
        plan_name=plan["name"],
        days=int(plan["days"]),
        amount=Decimal(plan["price"]),
        status=STATUS_PENDING_PAY,
        pay_method=0,
        client_ip=ip,
    )
    db.add(order)
    await db.flush()   # 拿到 order.id，供审计外键与 expires_at 回填使用
    # expires_at 必须由 DB 时钟生成（懒关闭/支付超时判定都用 DB NOW() 比较，钟差才会一致）
    await db.execute(
        update(RechargeOrder).where(RechargeOrder.id == order.id).values(
            expires_at=text(
                f"DATE_ADD(NOW(), INTERVAL {int(RECHARGE_ORDER_TTL_SECONDS)} SECOND)"
            )
        )
    )
    _audit(db, order, "CREATE", STATUS_PENDING_PAY, actor_type=0, actor_id=user_id,
           ip=ip, from_status=None,
           detail=f"下单套餐 {plan['name']}（{plan['days']} 天 / ¥{plan['price']}）")
    await db.commit()
    await db.refresh(order)   # 回读 DB 侧生成的 expires_at / created_at
    return True, "订单已创建，请在 15 分钟内完成支付", order


# ── 支付（回调闸口：唯一能推进订单到已支付/待审批的路径）─────────────────

async def apply_payment_callback(
    db: AsyncSession, event: PaymentEvent, ip: str | None
) -> tuple[bool, str, RechargeOrder | None]:
    """应用已验签的网关支付事件（utils.recharge_security.PaymentEvent）。

    这是订单推进到「已支付/待审批」的唯一入口：行锁 → 终态幂等 → 金额核对
    → 风控评估 → 状态流转 + 审计 +（低风险路径）会员延期，同一事务提交。

    返回 (ok, 中文提示, 订单)；ok=True 表示事件被受理（含进入待审批的情况）。
    """
    row = (await db.execute(
        select(RechargeOrder).where(RechargeOrder.order_no == event.order_no).with_for_update()
    )).scalars().first()
    if row is None:
        return False, "订单不存在", None
    pay_key = f"recharge:payfail:{row.user_id}"

    # ---- 幂等：已受理/终态订单对重复回调直接按原状态应答（不重复入账）----
    if row.status == STATUS_PAID:
        return True, "订单已支付", row
    if row.status == STATUS_PENDING_REVIEW and event.status == "success":
        return True, "订单已支付，等待管理员审核", row
    if row.status in _FINAL_STATUSES:
        return False, "订单已关闭或已处理", row

    # ---- 失败事件：审计留痕 + 失败计数（连续失败触发冷却，见路由层 is_locked）----
    if event.status == "fail":
        from_status = row.status
        pay_fail_throttle.record_fail(pay_key)
        _audit(db, row, "PAY_FAIL", from_status, actor_type=1, actor_id=None,
               ip=ip, from_status=from_status, detail="网关返回支付失败/用户取消")
        await db.commit()
        return False, "支付未完成，如需开通请重新发起支付", row

    # ---- 成功事件：仅待支付订单可推进 ----
    if row.status != STATUS_PENDING_PAY:
        return False, "订单状态不允许支付", row

    # 懒关闭：支付到达前已超时（DB 时钟判定）
    expired = (await db.execute(
        select(RechargeOrder.id).where(
            RechargeOrder.id == row.id,
            RechargeOrder.expires_at.is_not(None),
            RechargeOrder.expires_at <= func.now(),
        )
    )).first()
    if expired:
        from_status = row.status
        row.status = STATUS_CLOSED
        _audit(db, row, "EXPIRE_CLOSE", STATUS_CLOSED, actor_type=1, actor_id=None,
               ip=ip, from_status=from_status, detail="支付到达前订单已超时")
        await db.commit()
        return False, "订单已超时关闭，请重新下单", row

    # 金额核对：网关实收必须与订单应收一致（签名防伪造，这里防网关侧改单）
    try:
        paid_amount = Decimal(event.amount)
    except Exception:
        return False, "回调金额格式非法", row
    if paid_amount != row.amount:
        _audit(db, row, "PAY_FAIL", STATUS_PENDING_PAY, actor_type=1, actor_id=None,
               ip=ip, from_status=STATUS_PENDING_PAY,
               detail=f"回调金额 {event.amount} 与订单应收 {row.amount} 不符，已拒绝受理")
        await db.commit()
        return False, "回调金额与订单不符", row

    from_status = row.status
    row.paid_at = func.now()

    # ---- 风控评估：命中 → 转 1 待审批（钱已收，等管理员放行）----
    flags = []
    if row.amount >= Decimal(RECHARGE_MANUAL_REVIEW_AMOUNT):
        flags.append(RISK_SINGLE_AMOUNT)
    if await _daily_paid_total(db, row.user_id) + row.amount >= Decimal(RECHARGE_DAILY_REVIEW_AMOUNT):
        flags.append(RISK_DAILY_TOTAL)

    if flags:
        row.status = STATUS_PENDING_REVIEW
        row.risk_flags = ",".join(flags)
        _audit(db, row, "RISK_HOLD", STATUS_PENDING_REVIEW, actor_type=1, actor_id=None,
               ip=ip, from_status=from_status,
               detail=f"命中风控规则：{','.join(flags)}，支付成功但需人工审批后到账")
        await db.commit()
        # paid_at 用 func.now() 写入（DB 时钟），flush 后属性过期；提交后必须 refresh
        # 重载，否则路由层序列化时在异步上下文触发属性懒加载 → MissingGreenlet 500
        await db.refresh(row)
        return True, "支付成功，订单已进入人工审核，管理员通过后会员自动到账", row

    # ---- 低风险：直接入账（状态流转 + 审计 + 会员延期同一事务）----
    row.status = STATUS_PAID
    _audit(db, row, "PAY_SUCCESS", STATUS_PAID, actor_type=1, actor_id=None,
           ip=ip, from_status=from_status, detail=f"支付成功 ¥{row.amount}")
    _audit(db, row, "EXTEND_MEMBERSHIP", STATUS_PAID, actor_type=1, actor_id=None,
           ip=ip, from_status=STATUS_PAID, detail=f"会员延长 {row.days} 天（source=2 充值购买）")
    await membership_crud.extend_membership_for_recharge(db, row.user_id, row.days)
    await db.commit()
    pay_fail_throttle.reset(pay_key)
    await db.refresh(row)   # 同上：重载 func.now() 写入的 paid_at，供响应序列化
    return True, f"支付成功，会员已延长 {row.days} 天", row


# ── 用户侧：取消 / 记录 / 详情 ──────────────────────────────────────────

async def cancel_order(
    db: AsyncSession, order_no: str, user_id: int, ip: str | None
) -> tuple[bool, str]:
    """用户取消待支付订单（归属校验：order_no + user_id 双条件，防跨用户操作）。"""
    row = (await db.execute(
        select(RechargeOrder).where(
            RechargeOrder.order_no == order_no, RechargeOrder.user_id == user_id
        ).with_for_update()
    )).scalars().first()
    if row is None:
        return False, "订单不存在"
    if row.status != STATUS_PENDING_PAY:
        return False, "仅待支付订单可取消"

    from_status = row.status
    row.status = STATUS_CANCELLED
    _audit(db, row, "CANCEL", STATUS_CANCELLED, actor_type=0, actor_id=user_id,
           ip=ip, from_status=from_status, detail="用户主动取消")
    await db.commit()
    return True, "订单已取消"


async def list_user_orders(
    db: AsyncSession, user_id: int, page: int = 1, size: int = 20
) -> dict:
    """我的充值记录（先懒关闭超时单，再按 id 倒序分页）。返回 {"rows", "total"}。"""
    await _close_expired_orders(db, user_id)
    conditions = [RechargeOrder.user_id == user_id]
    total = (await db.execute(
        select(func.count(RechargeOrder.id)).where(*conditions)
    )).scalar_one()
    rows = (await db.execute(
        select(RechargeOrder).where(*conditions)
        .order_by(RechargeOrder.id.desc())
        .offset((page - 1) * size)
        .limit(size)
    )).scalars().all()
    return {"rows": rows, "total": total}


async def get_user_order(
    db: AsyncSession, user_id: int, order_no: str
) -> RechargeOrder | None:
    """订单详情（归属校验在查询条件里；返回前顺带懒关闭本用户超时单）。"""
    await _close_expired_orders(db, user_id)
    return (await db.execute(
        select(RechargeOrder).where(
            RechargeOrder.order_no == order_no, RechargeOrder.user_id == user_id
        )
    )).scalars().first()


# ── 管理端：审批 / 列表 / 审计轨迹 ──────────────────────────────────────

async def approve_order(
    db: AsyncSession, order_id: int, admin_id: int, note: str | None, ip: str | None
) -> tuple[bool, str]:
    """管理员通过待审批订单：放行到账（状态流转 + 审计 + 会员延期同一事务）。"""
    row = (await db.execute(
        select(RechargeOrder).where(RechargeOrder.id == order_id).with_for_update()
    )).scalars().first()
    if row is None:
        return False, "订单不存在"
    if row.status != STATUS_PENDING_REVIEW:
        return False, "仅待审批订单可执行通过操作"

    from_status = row.status
    row.status = STATUS_PAID
    row.reviewed_by = admin_id
    row.reviewed_at = func.now()
    row.review_note = note
    _audit(db, row, "APPROVE", STATUS_PAID, actor_type=2, actor_id=admin_id,
           ip=ip, from_status=from_status, detail=note or "管理员审核通过，放行到账")
    _audit(db, row, "EXTEND_MEMBERSHIP", STATUS_PAID, actor_type=2, actor_id=admin_id,
           ip=ip, from_status=STATUS_PAID, detail=f"会员延长 {row.days} 天（source=2 充值购买）")
    await membership_crud.extend_membership_for_recharge(db, row.user_id, row.days)
    await db.commit()
    return True, f"已通过，会员已延长 {row.days} 天"


async def reject_order(
    db: AsyncSession, order_id: int, admin_id: int, reason: str, ip: str | None
) -> tuple[bool, str]:
    """管理员拒绝待审批订单（原因必填，写入订单 review_note 与审计）。"""
    row = (await db.execute(
        select(RechargeOrder).where(RechargeOrder.id == order_id).with_for_update()
    )).scalars().first()
    if row is None:
        return False, "订单不存在"
    if row.status != STATUS_PENDING_REVIEW:
        return False, "仅待审批订单可执行拒绝操作"

    from_status = row.status
    row.status = STATUS_REJECTED
    row.reviewed_by = admin_id
    row.reviewed_at = func.now()
    row.review_note = reason
    _audit(db, row, "REJECT", STATUS_REJECTED, actor_type=2, actor_id=admin_id,
           ip=ip, from_status=from_status, detail=f"拒绝原因：{reason}（模拟渠道款项原路退回）")
    await db.commit()
    return True, "已拒绝，模拟支付款项将原路退回"


async def admin_list_orders(
    db: AsyncSession, page: int = 1, size: int = 20,
    status: int | None = None, keyword: str | None = None,
) -> dict:
    """管理端订单分页列表：status 筛选 + keyword（用户名/订单号/套餐名模糊）。

    返回 {"rows": [(order, username), ...], "total": n}，路由层组 PageResult。
    先全量懒关闭，保证管理端看到的待审批集合是新鲜的。
    """
    await _close_expired_orders(db)
    conditions = []
    if status is not None:
        conditions.append(RechargeOrder.status == status)
    if keyword:
        like = f"%{escape_like(keyword)}%"
        conditions.append(
            RechargeOrder.order_no.like(like, escape="\\")
            | RechargeOrder.plan_name.like(like, escape="\\")
            | User.username.like(like, escape="\\")
        )

    # username 随行返回：N:1 join 不会放大行数，count/rows 同一 join 条件
    count_stmt = select(func.count(RechargeOrder.id)).join(
        User, RechargeOrder.user_id == User.id, isouter=True
    )
    rows_stmt = select(RechargeOrder, User.username).join(
        User, RechargeOrder.user_id == User.id, isouter=True
    )
    if conditions:
        count_stmt = count_stmt.where(*conditions)
        rows_stmt = rows_stmt.where(*conditions)

    total = (await db.execute(count_stmt)).scalar_one()
    rows = (await db.execute(
        rows_stmt.order_by(RechargeOrder.id.desc())
        .offset((page - 1) * size)
        .limit(size)
    )).all()
    return {"rows": [(r[0], r[1]) for r in rows], "total": total}


async def get_order_by_id(db: AsyncSession, order_id: int) -> RechargeOrder | None:
    """管理端按主键查订单（审计轨迹接口先定位订单，404 语义在这里收口）。"""
    return (await db.execute(
        select(RechargeOrder).where(RechargeOrder.id == order_id)
    )).scalars().first()


async def list_order_logs(db: AsyncSession, order_id: int) -> list[RechargeAuditLog]:
    """某订单的审计轨迹（id 升序 = 时间线）。"""
    return list((await db.execute(
        select(RechargeAuditLog)
        .where(RechargeAuditLog.order_id == order_id)
        .order_by(RechargeAuditLog.id.asc())
    )).scalars().all())
