# 会员功能开发文档（P0 · 会员核心）

> **状态**：待实施　|　**基线**：`master @ d88b734`（与 Gitee 同步）
> **分工**：本文档 = 设计与验收标准；代码实现由开发者按第 8 节顺序执行
> **关联**：P1 功能（BYOK / 预算管理 / AI 月报 / 导出）与 P2 远期项见第 1.3 与第 10 节，本文档只覆盖 P0

---

## 0. 阅读须知（动手前必读）

以下事实决定了本设计的形状，实现时不得违反：

1. **AI 模块是裸 JSON 契约**（`routers/ai.py` 模块头三条铁律）：`/api/ai/**` 一律裸返回 `{"error": ...}`（HTTP 200），**不要抛 HTTPException**（会被全局异常处理器包成 `{code,message,data}` 信封，破坏前端解析）。因此会员配额超额在 AI 端用 `JSONResponse(status_code=429, content={...})` 直接返回，不抛异常、不套信封。
2. **无 alembic**：所有表靠手写 DDL。新增表必须**同时**写入 `sql/init_mysql.sql` 与 `sql/create_tables_from_models.sql`，并同步更新 `init_mysql.sql` 头部注释（表数量 9→12、外键数 +3）与 `docs/fastapi-backend/02-数据库设计.md`。
3. **单 worker 前提**：登录限流 `utils/throttle.py` 已声明单进程部署。本设计的并发限流同样是**进程内**实现，多 worker/多机部署时需换 Redis（代码里注释已注明）。
4. **模型档次只作用于对话链**：`analyze_chain`（结构化输出）与 `bookkeeping_chain` 维持 `ANALYZE_MODEL` 不随等级切换——结构化输出对模型要求不同，升级切换收益低、出错风险高。
5. **约定沿用**：tier/status 用整数标志位（0/1）；money 不涉及；ORM 走 `Base + IdMixin (+ TimestampMixin)`；`*Out` schema 继承 `OrmBase`；`get_current_user` 返回 `user_id: int`。
6. **配额计数的取舍**（写入代码注释）：在**实际触发 LLM 调用之前**计数，调用失败**不回滚**——防刷量优先，与短信/开放平台行业惯例一致。被幂等/去重短路**未触达 LLM** 的请求不计数。

---

## 1. 目标、范围与权益矩阵

### 1.1 P0 目标（本文档）

免费额度保护 LLM 成本；会员以「更高额度 + 并发数 + 高级模型」为核心权益；兑换码 + 管理员开通形成无支付依赖的"付费→开通"闭环。

### 1.2 权益矩阵（数值集中在 `config/settings.py`，可调）

| 权益 | 免费版（tier=0） | 会员（tier=1） |
|---|---|---|
| AI 对话 | 10 次/天 | 100 次/天 |
| 对话并发（流式同时进行） | 1 | 3 |
| AI 消费分析 + 预算规划 | 2 次/天（两类共用） | 30 次/天 |
| 智能记账解析 | 5 次/天 | 50 次/天 |
| 对话模型 | `CHAT_MODEL`（agnes-2.5-flash） | `CHAT_MODEL_PREMIUM`（未配置则回退 `CHAT_MODEL`） |
| 到期语义 | 永久 | `expires_at` 过期即惰性降级为免费（查询时判定，无定时任务） |

### 1.3 不做（P1/P2 留档）

BYOK、预算管理、AI 月度报告、账单导出（P1，见第 10 节 BYOK 专项）；周期记账、提醒、年度账单、家庭账本（P2）。本期**零新增依赖**。

---

## 2. 数据库设计

### 2.1 DDL（追加到 `sql/init_mysql.sql` 的 `ai_bookkeeping_logs` 之后；`create_tables_from_models.sql` 同步）

```sql
-- ---------------------------------------------------------------------------
-- 10. user_membership —— 用户会员表
--    用途：会员等级与到期时间。免费用户可以没有行；过期查询时惰性降级为免费。
--    来源：docs/membership-plan.md §2
--    关系：user_membership.user_id → users.id（1:1）
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `user_membership` (
    `id`         BIGINT      NOT NULL AUTO_INCREMENT           COMMENT '主键 ID',
    `user_id`    BIGINT      NOT NULL                          COMMENT '用户 ID，1:1 唯一',
    `tier`       TINYINT     NOT NULL DEFAULT 0                COMMENT '等级：0=免费 1=会员',
    `expires_at` DATETIME    NULL     DEFAULT NULL             COMMENT '会员到期时间；NULL=永久（仅免费档）',
    `source`     TINYINT     NOT NULL DEFAULT 0                COMMENT '开通来源：0=兑换码 1=管理员开通',
    `created_at` DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_membership_user` (`user_id`),
    CONSTRAINT `fk_membership_user` FOREIGN KEY (`user_id`)
        REFERENCES `users` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4
  COLLATE = utf8mb4_general_ci
  COMMENT = '用户会员表（1:1，免费用户可无行）';


-- ---------------------------------------------------------------------------
-- 11. ai_usage_daily —— AI 每日用量表
--    用途：按 (user_id, usage_date) 唯一计数，跨天自然归零，无需定时重置。
--    来源：docs/membership-plan.md §2
--    关系：ai_usage_daily.user_id → users.id（N:1）
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `ai_usage_daily` (
    `id`                BIGINT   NOT NULL AUTO_INCREMENT           COMMENT '主键 ID',
    `user_id`           BIGINT   NOT NULL                          COMMENT '用户 ID',
    `usage_date`        DATE     NOT NULL                          COMMENT '统计日期',
    `chat_count`        INT      NOT NULL DEFAULT 0                COMMENT '当日 AI 对话次数',
    `analyze_count`     INT      NOT NULL DEFAULT 0                COMMENT '当日分析次数（消费分析+预算规划）',
    `bookkeeping_count` INT      NOT NULL DEFAULT 0                COMMENT '当日智能记账解析次数',
    `created_at`        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at`        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_usage_user_date` (`user_id`, `usage_date`),
    CONSTRAINT `fk_usage_user` FOREIGN KEY (`user_id`)
        REFERENCES `users` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4
  COLLATE = utf8mb4_general_ci
  COMMENT = 'AI 每日用量表（会员配额计数）';


-- ---------------------------------------------------------------------------
-- 12. membership_codes —— 会员兑换码表
--    用途：管理员批量生成、用户核销、运营作废。16 位码去除易混淆字符。
--    来源：docs/membership-plan.md §2
--    关系：membership_codes.used_by → users.id（可空）
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `membership_codes` (
    `id`         BIGINT      NOT NULL AUTO_INCREMENT           COMMENT '主键 ID',
    `code`       CHAR(16)    NOT NULL                          COMMENT '兑换码（16 位大写字母数字，去除 0/O/1/I）',
    `days`       INT         NOT NULL                          COMMENT '兑换天数',
    `status`     TINYINT     NOT NULL DEFAULT 0                COMMENT '状态：0=未使用 1=已使用 2=已作废',
    `batch_no`   VARCHAR(32) NULL     DEFAULT NULL             COMMENT '批次号（默认生成时间戳）',
    `used_by`    BIGINT      NULL     DEFAULT NULL             COMMENT '核销用户 ID',
    `used_at`    DATETIME    NULL     DEFAULT NULL             COMMENT '核销时间',
    `created_at` DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_membership_codes_code` (`code`),
    KEY `idx_membership_codes_status` (`status`),
    CONSTRAINT `fk_codes_user` FOREIGN KEY (`used_by`)
        REFERENCES `users` (`id`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4
  COLLATE = utf8mb4_general_ci
  COMMENT = '会员兑换码表';
```

建库脚本（本地执行一次即可，幂等）：

```bash
mysql -uroot -p bookkeeping_fastapi < <(sed -n '/10. user_membership/,$p' sql/init_mysql.sql)
# 或直接把三段 DDL 粘进 mysql 客户端执行
```

### 2.2 ORM 模型 `fast_backend/models/membership.py`（新建，完整代码）

```python
"""会员模型 — 对应 user_membership / ai_usage_daily / membership_codes 表

字段与索引口径以 sql/init_mysql.sql 与 docs/fastapi-backend/02-数据库设计.md 为准。
约定延续项目风格：tier/status 整数标志位（0/1）、IdMixin/TimestampMixin、显式 Index。
"""

from datetime import date, datetime

from sqlalchemy import (
    BigInteger, Date, DateTime, ForeignKey, Index, Integer, SmallInteger, String,
)
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, IdMixin, TimestampMixin


class UserMembership(Base, IdMixin, TimestampMixin):
    """用户会员表 — 每用户一行；免费用户可以没有行"""

    __tablename__ = "user_membership"

    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        comment="用户 ID，1:1 唯一",
    )
    tier: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, default=0, comment="等级：0=免费 1=会员"
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime, comment="会员到期时间；NULL=永久（仅免费档可能出现）"
    )
    source: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, default=0, comment="开通来源：0=兑换码 1=管理员开通"
    )

    def __repr__(self) -> str:
        return f"<UserMembership(user_id={self.user_id}, tier={self.tier})>"


class AiUsageDaily(Base, IdMixin):
    """AI 每日用量表 — (user_id, usage_date) 唯一，upsert 累加，跨天自然归零"""

    __tablename__ = "ai_usage_daily"

    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        comment="用户 ID",
    )
    usage_date: Mapped[date] = mapped_column(Date, nullable=False, comment="统计日期")
    chat_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="当日 AI 对话次数"
    )
    analyze_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="当日分析次数（消费分析+预算规划）"
    )
    bookkeeping_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="当日智能记账解析次数"
    )

    __table_args__ = (
        Index("uk_usage_user_date", "user_id", "usage_date", unique=True),
    )


class MembershipCode(Base, IdMixin, TimestampMixin):
    """会员兑换码表"""

    __tablename__ = "membership_codes"

    code: Mapped[str] = mapped_column(
        String(16), nullable=False, unique=True,
        comment="兑换码（16 位大写字母数字，去除 0/O/1/I）",
    )
    days: Mapped[int] = mapped_column(Integer, nullable=False, comment="兑换天数")
    status: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, default=0, comment="状态：0=未使用 1=已使用 2=已作废"
    )
    batch_no: Mapped[str | None] = mapped_column(String(32), comment="批次号（默认生成时间戳）")
    used_by: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), comment="核销用户 ID"
    )
    used_at: Mapped[datetime | None] = mapped_column(DateTime, comment="核销时间")

    def __repr__(self) -> str:
        return f"<MembershipCode(code={self.code}, days={self.days}, status={self.status})>"
```

---

## 3. 配置增量 `config/settings.py`

在 `# ---- AI ----` 段之后追加：

```python
# ---- 会员 ----
# 会员对话走的高级模型；未配置时回退 CHAT_MODEL（以 Agnes 平台实际可用模型为准）
CHAT_MODEL_PREMIUM = os.getenv("CHAT_MODEL_PREMIUM", "")

# 权益矩阵：数值即口径，前端权益表从 GET /api/membership/status 动态取，不硬编码
MEMBERSHIP_PLANS = {
    0: {
        "name": "免费版",
        "daily_chat": 10,
        "concurrency": 1,
        "daily_analyze": 2,
        "daily_bookkeeping": 5,
        "premium_model": False,
    },
    1: {
        "name": "会员",
        "daily_chat": 100,
        "concurrency": 3,
        "daily_analyze": 30,
        "daily_bookkeeping": 50,
        "premium_model": True,
    },
}
```

---

## 4. 后端新增文件

### 4.1 `fast_backend/schemas/membership.py`（新建，完整代码）

```python
"""会员模块 Pydantic 模型"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from schemas.base import OrmBase


class UsageItem(BaseModel):
    """单项配额的用量"""

    used: int = Field(..., description="今日已用")
    limit: int = Field(..., description="今日上限")


class MembershipStatusOut(BaseModel):
    """GET /api/membership/status 出参"""

    tier: int = Field(..., description="生效等级：0=免费 1=会员（已过期视为 0）")
    tier_name: str = Field(..., alias="tierName")
    expires_at: Optional[str] = Field(None, alias="expiresAt", description="到期 ISO 时间；免费为 null")
    benefits: dict = Field(..., description="权益矩阵（MEMBERSHIP_PLANS[tier] 原样）")
    usage: dict = Field(..., description="{date, chat: UsageItem, analyze: UsageItem, bookkeeping: UsageItem}")

    model_config = {"populate_by_name": True}


class RedeemIn(BaseModel):
    """兑换码核销入参"""

    code: str = Field(..., min_length=4, max_length=32, description="兑换码；自动去空格/连字符并转大写")


class RedeemOut(BaseModel):
    """核销成功出参"""

    tier: int = 1
    expires_at: Optional[str] = Field(None, alias="expiresAt")

    model_config = {"populate_by_name": True}


class CodeGenerateIn(BaseModel):
    """管理端：批量生成兑换码"""

    count: int = Field(..., ge=1, le=500, description="生成数量")
    days: int = Field(..., ge=1, le=3650, description="每张兑换天数")
    batch_no: Optional[str] = Field(None, max_length=32, alias="batchNo", description="批次号；缺省用时间戳")

    model_config = {"populate_by_name": True}


class MembershipCodeOut(OrmBase):
    """兑换码行输出"""

    id: int
    code: str
    days: int
    status: int
    batch_no: Optional[str] = Field(None, alias="batchNo")
    used_by: Optional[int] = Field(None, alias="usedBy")
    used_at: Optional[datetime] = Field(None, alias="usedAt")
    created_at: Optional[datetime] = Field(None, alias="createdAt")


class CodeIdsIn(BaseModel):
    """管理端：作废入参（单码走路径参数，此模型备用）"""

    id: int


class GrantIn(BaseModel):
    """管理端：手动开通/延期"""

    user_id: int = Field(..., alias="userId", ge=1)
    days: int = Field(..., ge=1, le=3650, description="在现有到期基础上叠加的天数")

    model_config = {"populate_by_name": True}
```

### 4.2 `fast_backend/crud/membership.py`（新建，完整代码）

```python
"""会员模块数据访问 — user_membership / ai_usage_daily / membership_codes

约定：
- 会员生效判定是"惰性"的：expires_at <= now 视为免费（tier 0），不写库、不需要定时任务；
- 每日用量按 (user_id, usage_date) 唯一键 upsert，跨天从零开始；
- 权益数值口径全部来自 config/settings.py::MEMBERSHIP_PLANS，本模块不做硬编码。
"""

import secrets
from datetime import date, datetime, timedelta

from sqlalchemy import select, text
from sqlalchemy.dialects.mysql import insert as mysql_insert
from sqlalchemy.ext.asyncio import AsyncSession

from crud import user as user_crud
from models.membership import AiUsageDaily, MembershipCode, UserMembership

# 兑换码字母表：去除 0/O/1/I 防歧义（用户手抄场景多）
_CODE_ALPHABET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"


def normalize_code(raw: str) -> str:
    """用户输入归一化：去空格/连字符、转大写"""
    return (raw or "").replace(" ", "").replace("-", "").strip().upper()


# ── 等级判定 ────────────────────────────────────────────────────────────

async def get_membership_row(db: AsyncSession, user_id: int) -> UserMembership | None:
    return (await db.execute(
        select(UserMembership).where(UserMembership.user_id == user_id)
    )).scalars().first()


async def get_effective_membership(db: AsyncSession, user_id: int) -> UserMembership | None:
    """生效会员记录：不存在 / tier!=1 / 已过期 → None（免费）。

    过期不写库：查询时判定即可，省掉一个定时任务。
    """
    row = await get_membership_row(db, user_id)
    if row is None or row.tier != 1:
        return None
    if row.expires_at is None or row.expires_at <= datetime.now():
        return None
    return row


async def get_tier(db: AsyncSession, user_id: int) -> int:
    """生效等级：0/1。所有配额判断的唯一入口。"""
    return 1 if await get_effective_membership(db, user_id) else 0


# ── 每日用量 ────────────────────────────────────────────────────────────

_USAGE_FIELDS = {"chat": "chat_count", "analyze": "analyze_count", "bookkeeping": "bookkeeping_count"}


async def get_usage_row(db: AsyncSession, user_id: int, today: date | None = None) -> AiUsageDaily | None:
    d = today or date.today()
    return (await db.execute(
        select(AiUsageDaily).where(
            AiUsageDaily.user_id == user_id, AiUsageDaily.usage_date == d
        )
    )).scalars().first()


async def check_quota(db: AsyncSession, user_id: int, plan: dict, kind: str) -> tuple[bool, int, int]:
    """返回 (是否还有额度, 今日已用, 上限)。不写库。"""
    field = _USAGE_FIELDS[kind]                      # KeyError 由调用方保证 kind 合法
    limit = plan[f"daily_{kind}"]
    row = await get_usage_row(db, user_id)
    used = getattr(row, field) if row is not None else 0
    return used < limit, used, limit


async def incr_usage(db: AsyncSession, user_id: int, kind: str, n: int = 1) -> None:
    """当日用量 +n（MySQL upsert）。kind 来自白名单，n 为 int，text() 拼接安全。"""
    if kind not in _USAGE_FIELDS:
        raise ValueError(f"illegal usage kind: {kind}")
    col = _USAGE_FIELDS[kind]
    d = date.today()
    stmt = mysql_insert(AiUsageDaily).values(
        user_id=user_id, usage_date=d, **{col: n}
    )
    stmt = stmt.on_duplicate_key_update(**{col: text(f"{col} + {int(n)}")})
    await db.execute(stmt)


# ── 兑换码 ──────────────────────────────────────────────────────────────

def _gen_code() -> str:
    return "".join(secrets.choice(_CODE_ALPHABET) for _ in range(16))


async def generate_codes(
    db: AsyncSession, count: int, days: int, batch_no: str | None = None
) -> list[MembershipCode]:
    """批量生成兑换码（去重 + DB 唯一键兜底重试）"""
    batch = batch_no or datetime.now().strftime("%Y%m%d%H%M%S")
    rows: list[MembershipCode] = []
    seen: set[str] = set()
    while len(rows) < count:
        code = _gen_code()
        if code in seen:
            continue
        exists = (await db.execute(
            select(MembershipCode.id).where(MembershipCode.code == code)
        )).first()
        if exists:
            continue
        seen.add(code)
        rows.append(MembershipCode(code=code, days=days, status=0, batch_no=batch))
    db.add_all(rows)
    await db.commit()
    return rows


async def list_codes(
    db: AsyncSession, page: int = 1, size: int = 20, status: int | None = None
) -> dict:
    """兑换码分页列表（created_at 倒序），返回 {"rows": [...], "total": n}"""
    from sqlalchemy import func

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


async def void_code(db: AsyncSession, code_id: int) -> tuple[bool, str]:
    """作废：仅未使用可作废。返回 (ok, 提示)"""
    row = (await db.execute(
        select(MembershipCode).where(MembershipCode.id == code_id)
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


async def redeem_code(db: AsyncSession, user_id: int, raw: str) -> tuple[bool, str, UserMembership | None]:
    """核销：行锁防同一码并发重复核销；开通/延期从 max(now, 现有到期) 起叠加。

    返回 (ok, 提示, 生效后的会员行)。
    """
    code = normalize_code(raw)
    if not code:
        return False, "请输入兑换码", None
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
    row.used_at = datetime.now()

    now = datetime.now()
    m = await get_membership_row(db, user_id)
    if m is None:
        m = UserMembership(
            user_id=user_id, tier=1,
            expires_at=now + timedelta(days=row.days), source=0,
        )
        db.add(m)
    else:
        base = m.expires_at if (m.tier == 1 and m.expires_at and m.expires_at > now) else now
        m.tier = 1
        m.expires_at = base + timedelta(days=row.days)
        m.source = 0
    await db.commit()
    await db.refresh(m)
    return True, f"兑换成功，会员已延长 {row.days} 天", m


# ── 管理端开通 ──────────────────────────────────────────────────────────

async def grant_membership(db: AsyncSession, user_id: int, days: int) -> UserMembership | None:
    """管理员开通/延期：tier=1，从 max(now, 现有到期) 起加 days。用户不存在返回 None。"""
    if await user_crud.get_user_by_id(db, user_id) is None:
        return None
    now = datetime.now()
    m = await get_membership_row(db, user_id)
    if m is None:
        m = UserMembership(
            user_id=user_id, tier=1,
            expires_at=now + timedelta(days=days), source=1,
        )
        db.add(m)
    else:
        base = m.expires_at if (m.tier == 1 and m.expires_at and m.expires_at > now) else now
        m.tier = 1
        m.expires_at = base + timedelta(days=days)
        m.source = 1
    await db.commit()
    await db.refresh(m)
    return m
```

### 4.3 `fast_backend/utils/ai_concurrency.py`（新建，完整代码）

```python
"""AI 流式并发限流 — 进程内 per-user 信号量

⚠️ 与 utils/throttle.py（LoginThrottle）同一部署前提：单 worker 进程。
多 worker / 多机部署时需替换为 Redis（INCR + EXPIRE 或令牌桶），保持函数形状不变即可。

用法（在流式生成器内）：
    release = await try_acquire(user_id, limit)
    if release is None:
        yield sse({"type": "error", "code": "CONCURRENCY_LIMIT", "error": "..."})
        return
    try:
        ...
    finally:
        release()

返回闭包而非裸 Semaphore，是为了规避"用户升级导致 limit 变化、
信号量被重建后旧持有者误释放新信号量"的错位问题。
"""

import asyncio
from collections.abc import Callable

# user_id -> (信号量, 建立时的 limit)；limit 变化（升级/过期）时重建
_slots: dict[int, tuple[asyncio.Semaphore, int]] = {}


async def try_acquire(user_id: int, limit: int) -> Callable[[], None] | None:
    """尝试占用一个并发槽。成功返回 release 闭包；满额返回 None。"""
    entry = _slots.get(user_id)
    if entry is None or entry[1] != limit:
        entry = (asyncio.Semaphore(limit), limit)
        _slots[user_id] = entry
    sem = entry[0]
    if sem.locked():          # 单线程事件循环内 locked() 与 acquire() 之间无 await，判定原子
        return None
    await sem.acquire()
    def _release(_sem: asyncio.Semaphore = sem) -> None:
        _sem.release()
    return _release
```

### 4.4 `fast_backend/ai/llm.py` 改造（完整替换）

```python
"""LLM 客户端构造 — 按模型名缓存实例（会员高级模型 / 默认模型）"""

from langchain_openai import ChatOpenAI

from config.settings import (
    CHAT_MODEL, ANALYZE_MODEL, EMBEDDING_MODEL,
    OPENAI_BASE_URL, AGNES_API_KEY,
)

# 按模型名缓存：CHAT_MODEL 与 CHAT_MODEL_PREMIUM 各一个实例，进程内复用
_chat_llms: dict[str, ChatOpenAI] = {}


def get_chat_llm(model_name: str | None = None) -> ChatOpenAI:
    """对话 LLM：温度稍高，回答自然。model_name 缺省用默认模型（免费档）。"""
    name = (model_name or CHAT_MODEL).strip() or CHAT_MODEL
    llm = _chat_llms.get(name)
    if llm is None:
        llm = ChatOpenAI(
            model=name,
            api_key=AGNES_API_KEY,
            base_url=OPENAI_BASE_URL,
            temperature=0.7,
            streaming=True,          # /chat/stream 需要
        )
        _chat_llms[name] = llm
    return llm


def get_analyze_llm() -> ChatOpenAI:
    """分析 LLM：温度 0，输出稳定（配合 .with_structured_output 用）。
    注意：分析链不随会员等级切换模型（见文档 §0.4）。"""
    return ChatOpenAI(model=ANALYZE_MODEL, api_key=AGNES_API_KEY,
                      base_url=OPENAI_BASE_URL, temperature=0)


def get_embeddings():
    from langchain_openai import OpenAIEmbeddings
    return OpenAIEmbeddings(model=EMBEDDING_MODEL, api_key=AGNES_API_KEY,
                            base_url=OPENAI_BASE_URL)
```

### 4.5 `fast_backend/ai/chat_chain.py` 改造（只改两个函数签名）

```python
async def chat(messages: list[BaseMessage], model_name: str | None = None) -> str:
    """非流式（6.7）：一次拿到完整回复"""
    return (await get_chat_llm(model_name).ainvoke(messages)).content


async def chat_stream(messages: list, model_name: str | None = None):
    """逐块 yield 文本；messages = [system, *history, human]"""
    async for chunk in get_chat_llm(model_name).astream(messages):
        if chunk.content:
            yield chunk.content
```

---

## 5. AI 路由消费点改造（`routers/ai.py`，共 4 处 + 1 个公共闸门）

### 5.1 公共闸门（加在 `ai_error` 函数之后）

```python
# ── 会员配额闸门 ────────────────────────────────────────────────────────
# AI 模块是裸 JSON 契约：超额用 JSONResponse(429) 直返，不抛 HTTPException（会被包成信封）
from fastapi.responses import JSONResponse
from config.settings import MEMBERSHIP_PLANS
from crud import membership as membership_crud

_KIND_LABEL = {"chat": "AI 对话", "analyze": "AI 分析", "bookkeeping": "AI 智能记账"}


async def _quota_gate(db: AsyncSession, user_id: int, kind: str) -> dict | None:
    """配额闸门：通过则当日用量 +1 并返回 None；超额返回 429 响应体。

    计数时机 = 实际触发 LLM 之前；LLM 调用失败不回滚（防刷量优先，行业惯例）。
    幂等/去重短路未触达 LLM 的请求不应调用本闸门（如 bookkeeping 的 duplicate 分支）。
    """
    tier = await membership_crud.get_tier(db, user_id)
    ok, used, limit = await membership_crud.check_quota(db, user_id, MEMBERSHIP_PLANS[tier], kind)
    if not ok:
        return {
            "error": f"今日{_KIND_LABEL[kind]}次数已用完（{used}/{limit}），升级会员解锁更多额度",
            "code": "QUOTA_EXCEEDED",
            "used": used,
            "limit": limit,
        }
    await membership_crud.incr_usage(db, user_id, kind)
    return None
```

### 5.2 消费点 ①：`POST /chat`（非流式）

在**会话归属校验之后、组装消息之前**插入：

```python
    # 会员配额：超额直接 429（裸 JSON，code=QUOTA_EXCEEDED）
    quota_error = await _quota_gate(db, user_id, "chat")
    if quota_error:
        return JSONResponse(status_code=429, content=quota_error)
    tier = await membership_crud.get_tier(db, user_id)
```

`chat_chain.chat(messages)` 改为 `chat_chain.chat(messages, model_name=_resolve_chat_model(tier))`。模型解析函数（同样加在闸门旁）：

```python
def _resolve_chat_model(tier: int) -> str | None:
    """会员 → CHAT_MODEL_PREMIUM（未配置回退 None=默认模型）；免费 → None"""
    from config.settings import CHAT_MODEL_PREMIUM
    if tier == 1 and CHAT_MODEL_PREMIUM:
        return CHAT_MODEL_PREMIUM
    return None
```

### 5.3 消费点 ②：`POST /chat/stream`（流式）

生成器**之前**（会话归属校验之后）插配额闸门（同 ①，`return JSONResponse(status_code=429, content=quota_error)`），并把 tier/concurrency 提出来传给生成器。生成器内改造成：

```python
    tier = await membership_crud.get_tier(db, user_id)
    plan = MEMBERSHIP_PLANS[tier]
    quota_error = await _quota_gate(db, user_id, "chat")
    if quota_error:
        return JSONResponse(status_code=429, content=quota_error)
    model_name = _resolve_chat_model(tier)

    async def event_gen():
        # 0) 并发槽：失败以 SSE error 事件返回（保持流式契约，HTTP 仍 200）
        release = await ai_concurrency.try_acquire(user_id, plan["concurrency"])
        if release is None:
            yield sse({"type": "error", "code": "CONCURRENCY_LIMIT",
                       "error": "您的对话并发已达上限，请等待当前回复完成"})
            return
        try:
            # 1) 落库用户消息（原逻辑不变）
            ...
            # 2) 流式产出（原逻辑不变，仅传入 model_name）
            async for chunk in chat_chain.chat_stream(messages, model_name=model_name):
                ...
            # 3) 落库助手回复 + done（原逻辑不变）
        finally:
            release()
```

顶部 import 增加：`from utils import ai_concurrency`。

### 5.4 消费点 ③：`POST /analyze/expenses` 与 `POST /analyze/budget`

两个端点函数体**第一行**（try 之前）插入：

```python
    quota_error = await _quota_gate(db, user_id, "analyze")
    if quota_error:
        return JSONResponse(status_code=429, content=quota_error)
```

### 5.5 消费点 ④：`POST /bookkeeping`

插在**第 5 步 LLM 解析之前**（即 `parsed = await parse_bookkeeping(...)` 之前、幂等/去重与占位日志之后）：

```python
    # ── 第 4.5 步：会员配额（解析即计费；幂等/duplicate 短路的请求不会走到这里，不计）──
    quota_error = await _quota_gate(db, user_id, "bookkeeping")
    if quota_error:
        return ai_error(quota_error["error"])   # bookkeeping 前端按裸 error 消费；也可与 chat 一致用 429
```

> 取舍说明：bookkeeping 前端目前只消费 `{"error"}`，为少改一处前端，这里用 HTTP 200 + error 文案（含升级引导文字）；若想统一 429，把该行换成 `JSONResponse(status_code=429, content=quota_error)` 并在前端 `sendMessage` 同样处理。**二选一，不要两处都做。**

### 5.6 前端不受影响的部分

`faq/rebuild`、`feedback`、会话 CRUD、消息列表**不设配额**（无 LLM 成本或成本可控）。

---

## 6. 会员路由 `fast_backend/routers/membership.py`（新建，完整代码）

```python
"""会员模块路由 — 用户侧 /api/membership + 管理侧 /api/admin/membership

用户侧与 AI 模块不同，走标准 {code, message, data} 信封（前端 request.js 拦截器解包）。
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from config.db_config import get_db
from config.settings import MEMBERSHIP_PLANS
from crud import membership as membership_crud
from schemas.membership import (
    CodeGenerateIn, GrantIn, MembershipCodeOut, MembershipStatusOut, RedeemIn,
)
from utils.auth import get_current_user, get_current_admin
from utils.response import success_response

router = APIRouter(prefix="/api/membership", tags=["membership"])
admin_router = APIRouter(prefix="/api/admin/membership", tags=["membership-admin"])


@router.get("/status", summary="我的会员状态与今日用量")
async def membership_status(
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """返回 {tier, tierName, expiresAt, benefits, usage{date, chat, analyze, bookkeeping}}

    benefits 直接下发 MEMBERSHIP_PLANS[tier]，前端权益表动态渲染、不硬编码数值。
    """
    tier = await membership_crud.get_tier(db, user_id)
    plan = MEMBERSHIP_PLANS[tier]
    m = await membership_crud.get_effective_membership(db, user_id)
    usage_row = await membership_crud.get_usage_row(db, user_id)

    def _item(kind: str) -> dict:
        used = getattr(usage_row, f"{kind}_count", 0) if usage_row is not None else 0
        return {"used": used, "limit": plan[f"daily_{kind}"]}

    data = MembershipStatusOut(
        tier=tier,
        tier_name=plan["name"],
        expires_at=m.expires_at.isoformat() if m else None,
        benefits=plan,
        usage={
            "date": datetime.now().strftime("%Y-%m-%d"),
            "chat": _item("chat"),
            "analyze": _item("analyze"),
            "bookkeeping": _item("bookkeeping"),
        },
    ).model_dump(by_alias=True)
    return success_response(data=data)


@router.post("/redeem", summary="兑换码开通/续费")
async def redeem(
    body: RedeemIn,
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ok, msg, m = await membership_crud.redeem_code(db, user_id, body.code)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return success_response(message=msg, data={
        "tier": 1,
        "expiresAt": m.expires_at.isoformat() if m else None,
    })


# ── 管理侧 ──────────────────────────────────────────────────────────────

@admin_router.post("/codes", summary="批量生成兑换码")
async def generate_codes(
    body: CodeGenerateIn,
    _: int = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    rows = await membership_crud.generate_codes(db, body.count, body.days, body.batch_no)
    return success_response(message=f"已生成 {len(rows)} 张兑换码", data={
        "batchNo": rows[0].batch_no if rows else None,
        "codes": [MembershipCodeOut.model_validate(r).model_dump(by_alias=True) for r in rows],
    })


@admin_router.get("/codes", summary="兑换码列表")
async def list_codes(
    _: int = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    status: int | None = Query(None, description="0未使用 1已使用 2已作废；缺省全部"),
):
    result = await membership_crud.list_codes(db, page, size, status)
    total = result["total"]
    return success_response(data={
        "records": [MembershipCodeOut.model_validate(r).model_dump(by_alias=True) for r in result["rows"]],
        "total": total,
        "pages": (total + size - 1) // size,
        "current": page,
        "size": size,
    })


@admin_router.put("/codes/{code_id}/void", summary="作废兑换码")
async def void_code(
    code_id: int,
    _: int = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    ok, msg = await membership_crud.void_code(db, code_id)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return success_response(message=msg)


@admin_router.post("/grant", summary="手动开通/延期会员")
async def grant(
    body: GrantIn,
    _: int = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    m = await membership_crud.grant_membership(db, body.user_id, body.days)
    if m is None:
        raise HTTPException(status_code=404, detail="用户不存在")
    return success_response(message=f"已为用户 {body.user_id} 开通/延期 {body.days} 天", data={
        "userId": m.user_id,
        "tier": m.tier,
        "expiresAt": m.expires_at.isoformat() if m.expires_at else None,
    })
```

`main.py` 注册（追加到 `app.include_router(ai.router)` 之后）：

```python
from routers import membership
app.include_router(membership.router)
app.include_router(membership.admin_router)
```

---

## 7. 用户信息与管理端列表注入会员标识

### 7.1 `schemas/user.py::UserOut` 追加两个字段

```python
    membership_tier: int = Field(0, description="生效会员等级：0=免费 1=会员（过期已惰性降级）")
    membership_expires_at: Optional[datetime] = None
```

### 7.2 `routers/user.py` GET /info 返回前注入

```python
    # 会员标识（get_current_user 返回的 user_id 即当前用户）
    from crud import membership as membership_crud
    membership = await membership_crud.get_effective_membership(db, user_id)
    out = UserOut.model_validate(user_info)
    out.membership_tier = 1 if membership else 0
    out.membership_expires_at = membership.expires_at if membership else None
    return success_response(data=out.model_dump())
```

> `UserOut` 无 camelCase alias，前端 AuthContext 的 user 对象本来就是 snake_case（`user.role`、`user.created_at`），直接读 `user.membership_tier` 即可。

### 7.3 `crud/admin.py::list_users`（管理端用户列表带会员标识）

不改 SQL 的 count 查询；查完 rows 后批量补查、router 组包时注入：

```python
    # crud/admin.py::list_users 末尾、return 前追加
    rows = result.scalars().all()
    member_map: dict[int, object] = {}
    if rows:
        from datetime import datetime as _dt
        from models.membership import UserMembership as _UM
        mrows = (await db.execute(
            select(_UM).where(_UM.user_id.in_([u.id for u in rows]))
        )).scalars().all()
        now = _dt.now()
        member_map = {
            m.user_id: m for m in mrows
            if m.tier == 1 and m.expires_at and m.expires_at > now
        }
    return {"rows": rows, "total": total, "member_map": member_map}
```

`routers/admin.py` 的 GET /users 端点组 `UserOut` 时：`out.membership_tier = 1 if u.id in member_map else 0`（expires_at 同理）。

---

## 8. 前端实施（personal-ledger-frontend，React 18 + antd 5 + 既有 token 体系）

### 8.1 `src/api/membership.js`（新建，完整）

```js
import request from './request'

// 我的会员状态（含今日用量与权益矩阵）
export const getMembershipStatus = () => request.get('/membership/status')
// 兑换码开通/续费
export const redeemMembership = (code) => request.post('/membership/redeem', { code })
// —— 管理端 ——
export const generateCodes = (data) => request.post('/admin/membership/codes', data)   // {count, days, batchNo?}
export const listCodes = (params) => request.get('/admin/membership/codes', { params }) // {page,size,status?}
export const voidCode = (id) => request.put(`/admin/membership/codes/${id}/void`)
export const grantMembership = (data) => request.post('/admin/membership/grant', data) // {userId, days}
```

### 8.2 `src/styles/design-tokens.css` 追加宽进度条（会员中心用量条用）

```css
/* 全宽进度条（会员中心配额用量行） */
.progress-bar-track--wide {
  width: 100%;
}
```

### 8.3 新页 `src/pages/Membership.jsx`（会员中心，规格 + 关键结构）

**布局**（复用 `PageHeader` / `card-base` / `gradient-icon` / `PageHeader`，照 Dashboard 模式）：

```
PageHeader「会员中心」
├─ Card 等级卡：gradient-icon--primary（CrownOutlined）+ tierName + expiresAt（会员时显示「YYYY-MM-DD 到期」）
│   └─ 兑换输入行：Input（16 位码，自动去空格连字符转大写）+ Button「兑换」（loading）
├─ Card 今日用量（免费与会员都显示，数据来自 status.usage）：
│   每行：label「AI 对话」+ .progress-bar-track--wide/.progress-bar-fill(width=min(100,used/limit*100)%)
│         + 「used / limit」.money 数字
│   额度用尽的行 fill 用 var(--color-expense)，否则 var(--color-primary)
└─ Card 权益对比：antd Table 两列（权益 / 当前档位值），或简单 Descriptions；
    数据来自 status.benefits（dailyChat/concurrency/dailyAnalyze/dailyBookkeeping/premiumModel）
```

**关键交互**：
- 挂载时 `getMembershipStatus()`，`SkeletonCard` 三个占位；失败 `EmptyState`。
- 兑换成功：`message.success` + 重新拉 status；失败（400）`message.error(res.message)`。
- 兑换输入规范化在前端也做一份（粘贴友好）：`code.replace(/[\s-]/g, '').toUpperCase()`。

### 8.4 新页 `src/pages/AdminMembership.jsx`（兑换码管理，照 AdminFaq 页面模式）

```
PageHeader「会员管理」
└─ Card（variant="borderless" className="card-base"）
    ├─ ListToolbar：Button「生成兑换码」（primary，打开 Modal）+ Select 状态筛选（全部/未使用/已使用/已作废）
    ├─ Table（rowKey=id, scroll={{x:720}}）：ID(responsive md) / 兑换码(.money 等宽，4-4-4-4 分组展示) /
    │   天数 / 状态 Tag（0=default未使用 1=success已使用 2=error已作废）/ 批次号(md) / 核销用户(md) / 核销时间(格式化 md) / 操作(未使用→Popconfirm作废)
    └─ 生成 Modal：count(InputNumber 1-500, 默认10) + days(InputNumber, 默认30) → generateCodes
        → 成功后弹结果 Modal：TextArea 只读，展示每行一个 code（纯码，方便整批复制），并刷新表格
```

状态筛选走 `listCodes({page, size, status})`；分页用 antd Table pagination（`showTotal`）。

### 8.5 改动点清单（既有文件）

| 文件 | 改动 |
|---|---|
| `src/App.jsx` | 加两条路由：`<Route path="membership" element={<Membership />} />`、`<Route path="admin/membership" element={<AdminRoute><AdminMembership /></AdminRoute>} />`；顶部 import |
| `src/components/MainLayout.jsx` | ① `menuItems` 在 AI助手 之后加 `{ key: '/membership', icon: <CrownOutlined />, label: '会员中心' }`；② `adminMenuItems` 末尾加 `{ key: '/admin/membership', icon: <TagsOutlined />, label: '会员管理' }`；③ `breadcrumbMap` 加 `/membership: '会员中心'`、`'/admin/membership': '会员管理'`；④ 用户下拉按钮里，昵称 Text 前加 `user?.membership_tier === 1 && <CrownOutlined style={{ color: '#feca57', marginRight: 4 }} />`（user 来自 AuthContext，字段由 §7.2 注入） |
| `src/pages/AiChat.jsx` | ① 挂载时 `getMembershipStatus()`，存 `usage`（chat.used/limit）与 `tierName`；② 输入栏上方加一行小字：`今日对话 {used}/{limit} · {tierName}`（`.money` 数字、超限红色），会员额外显示 `premiumModel ? '已启用高级模型' : ''`；③ `sendMessage` 里 fetch 后、读流前加 `if (res.status === 429) { const err = await res.json().catch(() => ({})); if (err.code === 'QUOTA_EXCEEDED') { setUpgradeOpen(true) } else { message.error(err.error || '请求过于频繁') } setLoading(false); return }`；④ SSE 收到 `{type:'error', code:'CONCURRENCY_LIMIT'}` 时 `message.warning(err.error)`（现有 error 分支已处理文案，加 code 判断可选）；⑤ 每次流式 done 后本地 `used + 1`（免重拉）；⑥ 升级引导 Modal：`open=upgradeOpen`，内容「今日免费对话次数已用完」，`okText='升级会员'` → `navigate('/membership')`，`cancelText='知道了'`；额度用尽时发送按钮 `disabled` |
| `src/pages/AdminUsers.jsx` | ① columns 在「角色」后加「会员」列：`membership_tier === 1 ? <Tag color="gold">会员</Tag> : <Tag>免费</Tag>`（数据来自 §7.3 注入的列表接口）；② 操作列加「开通/延期」链接按钮（所有行可见，包括管理员），点击开 Modal（显示用户名 + InputNumber 天数）→ `grantMembership({userId, days})` → `message.success` + 刷新列表 |
| `src/pages/UserInfo.jsx` | 账户信息 Descriptions 追加一行：`<Descriptions.Item label="会员等级">{user.membership_tier === 1 ? <Text strong>会员{user.membership_expires_at ? `（${formatDateTime(user.membership_expires_at)} 到期）` : ''}</Text> : <Text>免费版</Text>}</Descriptions.Item>`，并加一个跳转 `/membership` 的次级按钮 |

---

## 9. 测试（`fast_backend/tests/test_membership.py`，新建）

沿用现有模式：不依赖真实 MySQL；纯单元测纯逻辑，路由流程用 `dependency_overrides[get_db]` + `monkeypatch` crud。关键用例清单：

| 层 | 用例 | 断言要点 |
|---|---|---|
| 纯单元 | `normalize_code` | 去空格/连字符、转大写、小写输入归一 |
| 纯单元 | `MEMBERSHIP_PLANS` 完整性 | 两档都含全部权益键；会员各项 > 免费各项 |
| 纯单元 | `_gen_code`（导入私有函数可测） | 16 位、字母表内无 `0O1I` |
| 路由 | 路由注册（照 test_app 模式） | `/api/membership/status`、`/api/membership/redeem`、`/api/admin/membership/codes`、`/api/admin/membership/grant` 存在于 `{r.path for r in app.routes}` |
| 路由 | status 信封 | override `get_current_user`→固定 id、monkeypatch `get_tier`/`get_effective_membership`/`get_usage_row`；断言 `code==200`、`data.tierName=="免费版"`、`data.usage.chat.limit==10` |
| 路由 | 兑换 400 分支 | monkeypatch `redeem_code` → `(False, "该兑换码已被使用", None)`；断言 400 + `message` 文案 |
| 路由 | 兑换成功 | monkeypatch → `(True, "兑换成功", fake_m)`；断言 `data.expiresAt` 非 null |
| 路由 | 管理端鉴权 | `/codes` 用非 admin token 依赖（get_current_admin 抛 403 的 monkeypatch）→ 403 |
| AI 闸门 | 超额 429（照 test_sqli 的 TestClient 模式） | override get_db 为假 session；monkeypatch `_quota_gate` 所用 crud：`get_tier→0`、`check_quota→(False, 10, 10)`；POST `/api/ai/chat`（需同时 monkeypatch 会话查询通过）→ 断言 `status_code==429`、`code=="QUOTA_EXCEEDED"`、响应体**无** `code:200 信封`（裸 JSON 契约） |
| AI 闸门 | 通过即计数 | `check_quota→(True, 3, 10)`；monkeypatch `incr_usage` 记录调用参数；断言被调用一次且 kind=="chat" |

骨架（节选，两个代表用例）：

```python
"""会员模块测试 — 配额闸门 / 兑换 / 管理端

约定：不连真实 MySQL。路由流程用 dependency_overrides + monkeypatch；
AI 端断言裸 JSON 契约（429 不得被包成信封）。
"""
from fastapi.testclient import TestClient

from config.db_config import get_db
from crud import membership as membership_crud
from main import app


class FakeDB:
    async def commit(self): pass
    async def refresh(self, obj): pass
    async def execute(self, *a, **k): raise AssertionError("测试未 monkeypatch 的查询不应触库")


def _client():
    app.dependency_overrides[get_db] = lambda: FakeDB()
    return TestClient(app)


def test_quota_gate_returns_bare_429(monkeypatch):
    """超额 → 429 裸 JSON，QUOTA_EXCEEDED，无信封"""
    async def fake_tier(db, user_id): return 0
    async def fake_quota(db, user_id, plan, kind): return (False, 10, 10)
    async def fake_session(db, sid, uid): return object()   # 会话归属通过
    monkeypatch.setattr(membership_crud, "get_tier", fake_tier)
    monkeypatch.setattr(membership_crud, "check_quota", fake_quota)
    import routers.ai as ai_router
    monkeypatch.setattr(ai_router.ai_crud, "get_user_session", fake_session)

    client = _client()
    try:
        res = client.post(
            "/api/ai/chat",
            json={"sessionId": "s1", "message": "你好"},
            headers={"Authorization": "Bearer test"},
        )
        assert res.status_code == 429
        body = res.json()
        assert body["code"] == "QUOTA_EXCEEDED"
        assert "code" not in body or body.get("code") != 200   # 确认不是信封
    finally:
        app.dependency_overrides.clear()


def test_status_envelope(monkeypatch):
    async def fake_tier(db, user_id): return 0
    async def fake_none(db, user_id): return None
    monkeypatch.setattr(membership_crud, "get_tier", fake_tier)
    monkeypatch.setattr(membership_crud, "get_effective_membership", fake_none)
    monkeypatch.setattr(membership_crud, "get_usage_row", fake_none)

    client = _client()
    try:
        res = client.get("/api/membership/status", headers={"Authorization": "Bearer test"})
        assert res.status_code == 200
        body = res.json()
        assert body["code"] == 200
        assert body["data"]["tierName"] == "免费版"
        assert body["data"]["usage"]["chat"] == {"used": 0, "limit": 10}
    finally:
        app.dependency_overrides.clear()
```

> 注意：`routers/ai.py` 内 `from crud import membership as membership_crud` 是函数内 import 还是模块顶层，会影响 monkeypatch 目标路径——**建议在 routers/ai.py 顶层 import**（本文档片段即是），monkeypatch `routers.ai.membership_crud` 或直接 patch `crud.membership` 的函数皆可（patch `crud.membership` 函数属性对所有引用方生效，最稳）。

---

## 10. 实施顺序（按此推进，每步可独立验证）

1. [ ] 建表：三段 DDL 追加进 `sql/init_mysql.sql`（同步头部注释）与 `sql/create_tables_from_models.sql`，并在本地 MySQL 执行；更新 `docs/fastapi-backend/02-数据库设计.md`（表清单 9→12 + 三表说明 + 外键 +3）
2. [ ] `models/membership.py` + `settings.py` 配置增量
3. [ ] `schemas/membership.py` + `crud/membership.py` + `utils/ai_concurrency.py`
4. [ ] `ai/llm.py` 参数化 + `ai/chat_chain.py` 签名（此时全站行为不变，回归点）
5. [ ] `routers/ai.py`：公共闸门 + 四个消费点（chat → stream → analyze×2 → bookkeeping）
6. [ ] `routers/membership.py` + `main.py` 注册 + `schemas/user.py`/`routers/user.py`/`crud/admin.py` 注入
7. [ ] 前端：api/membership.js → Membership / AdminMembership 两页 → App.jsx 路由 → MainLayout 菜单徽标 → AiChat 配额交互 → AdminUsers 会员列/开通 → UserInfo 会员行 → design-tokens.css 宽进度条
8. [ ] `tests/test_membership.py`；`pytest` 全绿
9. [ ] 手动验收（见 §11）；`npm run build` 零错误
10. [ ] （可选）`.env` 增加注释行 `# CHAT_MODEL_PREMIUM=agnes-2.5-pro`（以平台实际可用模型为准；不配置=权益自动回退）

## 11. 验收标准（全部满足才算完成）

- [ ] 免费用户第 11 次对话：流式返回 429 裸 JSON `QUOTA_EXCEEDED`，前端弹「升级会员」引导，可跳转会员中心；次日自动恢复 10 次（跨天无需重启/定时任务）
- [ ] 会员中心显示：当前等级、今日用量进度条（对话/分析/记账三行）、权益对比表
- [ ] 管理员生成 10 张 30 天兑换码 → 表格可见、状态"未使用"→ 作废一张后该码兑换报"已作废"
- [ ] 用户兑换成功 → 会员中心立即显示会员 + 到期日；顶栏出现金色皇冠；AiChat 显示"今日对话 0/100 · 会员"；若配置了 `CHAT_MODEL_PREMIUM`，对话请求实际走高级模型（后端日志/抓包确认），未配置则回退默认模型且不报错
- [ ] 分析与智能记账分别按 2/5 次拦截（免费档）
- [ ] 并发：免费用户开两个标签页同时发流式对话，第二路收到 `CONCURRENCY_LIMIT` 提示
- [ ] 管理员在用户管理页对任意用户「开通/延期」→ 列表「会员」列即时变化
- [ ] `pytest` 全绿（含既有用例）；`npm run build` 零错误；会员中心/AiChat/AdminMembership 桌面+移动双档截图无布局问题

---

## 12. P1 留档 · 用户自带 API Key（BYOK）专项评估

**结论**：中等难度，无架构级硬点；与会员"模型档次"对 `llm.py` 的参数化改造合并做可省一半工作量。**产品规则建议**：自带 key 的调用平台零成本 → **不占平台每日次数**（仍限并发，保服务器资源），与会员形成"升级 或 自带 key"双通道。

| 改动点 | 难度 | 说明 |
|---|---|---|
| 新表 `user_ai_config`（user_id 唯一、base_url、api_key 加密、model、enabled） | 低 | 照 router→schema→crud 三层模式 |
| **密钥安全**：`cryptography` Fernet 加密 + env 主密钥；GET 只回脱敏 `sk-****last4` | 中 | 唯一新增依赖；不做加密答辩会被追问 |
| `llm.py` 请求级实例 + 三条链签名传参 + 5 端点穿线 | 中（量大难度低） | 漏一个端点就会"配了 key 还走平台额度" |
| 用户 key 失效的错误区分 | 中 | 上游 401/429 要与平台故障区分文案 |
| 测试连接接口 | 低 | 用用户 key 发极小请求 |
| 前端：UserInfo「AI 接入设置」卡片 + AiChat 徽标 | 低 | — |
| **范围划界** | — | FAQ 向量检索/embedding **不走**用户 key（索引按用户隔离复杂度翻倍、演示价值低） |

## 13. P1/P2 其余留档（一句话备忘）

- **预算管理**（中）：新表 budgets + CRUD + Dashboard 进度条；AI 侧 `plan_budget` 链已存在可直接挂接；免费 1 个总预算/会员分类不限
- **AI 月度消费报告**（中低）：基于 `analyze_expenses` 存档回看；免费 1 次/月
- **账单导出 CSV**（低）：流式生成；免费 2 次/月
- **周期记账**（中）：固定账单自动入账，需惰性生成或调度器
- **记账提醒**（中）：SMTP + APScheduler（`tasks/purge.py` 占位已留）
- **年度账单页**（中）：纯统计 + 前端展示，传播点
- **家庭共享账本**（高）：权限模型大改，远期

## 14. 风险与注意事项汇总

1. AI 裸 JSON 契约：429 必须用 `JSONResponse` 直返，**不得抛 HTTPException**（会被全局处理器包成信封，前端 AiChat 解析崩）。
2. DDL 双文件 + 头部注释 + 02 文档四处同步；先建表再起服务（AI 路由首请求即查 membership 表）。
3. 并发限流是进程内的：`--workers > 1` 或多机部署时失效（代码注释已声明，答辩可主动讲这是已知边界与 Redis 演进路径）。
4. `incr_usage` 的 `text()` 拼接：kind 必须过白名单、n 必须 `int()`，不要把用户输入拼进去。
5. 兑换码核销必须 `with_for_update()` 行锁，否则并发同码可双重核销。
6. 前端 AiChat 的 fetch 目前不检查 `res.status`，必须补 429 分支（见 §8.5）。
7. `UserOut` 是 snake_case（无 alias），前端 AuthContext 直接读 `user.membership_tier`。
8. 过期惰性降级不写库：所有判定走 `get_tier` 单一入口，不要在别处自行比较 `expires_at`。
