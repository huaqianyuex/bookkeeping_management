"""AI 模块 Pydantic 模型 — /api/ai

⚠️ 铁律（10-实现骨架.md §六 / 05 §0）：
- `/api/ai/**` 一律**裸返回**，不套 `{code,message,data}` 信封；
- 会话/消息时间戳是 **int 毫秒**（createdAt/updatedAt/deletedAt/timestamp 皆是）；
- 业务失败统一 `{"error": "中文"}`（HTTP 200），勿抛 HTTPException；
- 例外：鉴权 401 由依赖抛出，是唯一带 Result 结构的形态。

⚠️ 消费分析 / 预算规划的 `data` **内部字段是 snake_case**（total_expense / savings_rate /
monthly_budget...），与业务模块「对外 camelCase」的约定不同——前端 AiChat.jsx 按此读取，
不要自作主张改成驼峰。
"""

from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from schemas.base import OrmBase


class ErrorOut(BaseModel):
    """AI 模块统一失败结构（HTTP 200 裸返回）"""
    error: str


# ── 会话 ──────────────────────────────────────────────────────────────

class SessionCreateIn(BaseModel):
    """创建会话请求体（6.1）"""
    title: Optional[str] = Field(None, max_length=50, description="会话标题，缺省「新对话」，服务端截断 50 字")


class SessionRenameIn(BaseModel):
    """重命名会话请求体（6.3）"""
    title: str = Field(..., description="新标题，trim 后 1–50 字")


class SessionOut(OrmBase):
    """会话出参（裸 Session 对象，6.1 / 6.3 使用）

    字段名与 ChatSession ORM 属性一一对应；时间戳为 int 毫秒。
    """
    id: str
    user_id: Optional[int] = Field(None, alias="userId")
    title: str
    auto_title: int = Field(1, alias="autoTitle", description="1=AI 可覆盖标题，0=用户已重命名锁定")
    created_at: int = Field(..., alias="createdAt")
    updated_at: int = Field(..., alias="updatedAt")
    deleted_at: int = Field(0, alias="deletedAt", description="0=未删；>0=软删毫秒")


class SessionListItem(BaseModel):
    """会话列表项（6.2）"""
    id: str
    title: str
    preview: str = Field(..., description="最后一条消息，前缀「你: 」/「AI: 」，内容截 50 字")
    message_count: int = Field(0, alias="messageCount")
    created_at: int = Field(..., alias="createdAt")
    updated_at: int = Field(..., alias="updatedAt")


class SessionListOut(BaseModel):
    """会话列表出参 — 注意是裸 {items, total}，**不是**业务 PageResult 的 records/total"""
    items: List[SessionListItem] = Field(default_factory=list)
    total: int = 0


class SessionIdsIn(BaseModel):
    """AI 批量删除会话请求体（6.5）—— 元素是 **string**，勿与 admin 模块 int 版 IdsIn 混用"""
    ids: List[str] = Field(..., min_length=1, description="会话 ID 数组，单次最多 50 条")


# ── 消息 / 对话 ────────────────────────────────────────────────────────

class MessageOut(OrmBase):
    """消息出参（6.6，裸数组元素，按 timestamp 升序）"""
    id: str
    session_id: str = Field(..., alias="sessionId")
    role: str = Field(..., description="user | assistant")
    content: str
    timestamp: int = Field(..., description="毫秒时间戳")


class ChatIn(BaseModel):
    """对话请求体（6.7 非流式 / 6.8 流式共用）"""
    session_id: str = Field(..., alias="sessionId")
    message: str = Field(..., min_length=1)

    model_config = ConfigDict(populate_by_name=True)


class ChatOut(BaseModel):
    """非流式对话出参（6.7）— 字段名是 content，不是 answer"""
    content: str


# ── 分析 / 预算 ────────────────────────────────────────────────────────

class ExpenseAnalyzeIn(BaseModel):
    """消费分析请求体（6.9）— 财务数据由服务端查库组包，前端只传诉求文本"""
    query: Optional[str] = Field("请分析我的消费情况", description="自然语言诉求，作为提示词 human 片段")


class BudgetPlanIn(BaseModel):
    """预算规划请求体（6.10）"""
    monthly_income: float = Field(..., alias="monthlyIncome", gt=0, description="月收入，必填")
    savings_goal: Optional[float] = Field(None, alias="savingsGoal", description="月储蓄目标；不传按 50/30/20 推导")

    model_config = ConfigDict(populate_by_name=True)


class ExpenseAnalysis(BaseModel):
    """消费分析出参结构（6.9 data）— snake_case 是契约，勿改驼峰"""
    summary: str = ""
    total_expense: float = 0
    top_categories: List[dict] = Field(default_factory=list, description="元素含 name/amount/percentage/trend")
    insights: List[str] = Field(default_factory=list, description="洞察，≥3 条")
    suggestions: List[str] = Field(default_factory=list, description="建议，≥3 条")
    savings_rate: float = 0
    risk_level: str = "一般"


class BudgetPlan(BaseModel):
    """预算规划出参结构（6.10 data）— snake_case 是契约，勿改驼峰"""
    monthly_budget: float = 0
    category_limits: List[dict] = Field(default_factory=list, description="元素含 category/limit/reason")
    savings_target: float = 0
    alerts: List[str] = Field(default_factory=list)


class UserFinanceContext(BaseModel):
    """用户财务上下文 — 传给 LLM 的用户数据摘要（ai/context.py 组包）"""
    total_income: float = 0
    total_expense: float = 0
    recent_records: List[dict] = Field(default_factory=list)
    top_categories: List[dict] = Field(default_factory=list)


# ── FAQ / 反馈 ────────────────────────────────────────────────────────

class FeedbackIn(BaseModel):
    """保存反馈请求体（6.13）— 对应 feedback 表 {message_id, rating, comment, timestamp}"""
    message_id: str = Field(..., alias="messageId", description="被评价的消息 ID（msg_...）")
    rating: int = Field(..., ge=1, le=5, description="评分 1–5")
    comment: Optional[str] = Field(None, description="文字反馈")

    model_config = ConfigDict(populate_by_name=True)


# ── 自然语言记账 ────────────────────────────────────────────────────────

class BookkeepingIn(BaseModel):
    """自然语言记账请求体（6.15）

    - client_msg_id 是强幂等键：重发同一条消息必须带同一个值；
    - draft_id 用于追问续写：把本次内容补进指定草稿（ai_bookkeeping_logs.id）；
    - dry_run=true 只解析不入账，返回 preview。
    """
    message: str = Field(..., min_length=1, max_length=500, description="原始口语化文本，trim 后 1–500 字")
    session_id: Optional[str] = Field(None, alias="sessionId", description="AI 会话 ID；传入时消息写入 messages")
    client_msg_id: Optional[str] = Field(None, alias="clientMsgId", description="客户端 UUID 强幂等键")
    draft_id: Optional[int] = Field(None, alias="draftId", description="追问续写：目标草稿日志 ID")
    dry_run: bool = Field(False, alias="dryRun", description="true=只解析不入账")
    force: bool = Field(False, alias="force", description="true=跳过 5 分钟弱幂等窗口")
    now: Optional[str] = Field(None, description="ISO datetime，覆盖服务端「今天」，仅联调用")

    model_config = ConfigDict(populate_by_name=True)


class BookkeepingAmendIn(BaseModel):
    """修改 AI 记账记录请求体（6.16）— 至少一项非空；显式字段与 message 同给时以显式字段为准"""
    amount: Optional[float] = Field(None, gt=0, description="新金额，>0 且 ≤99999999.99")
    category_id: Optional[int] = Field(None, alias="categoryId", description="新分类，须归属本人且 type 与原记录一致")
    date: Optional[str] = Field(None, alias="recordDate", description="新日期 yyyy-MM-dd")
    remark: Optional[str] = Field(None, max_length=200, description="新备注，超 200 截断")
    message: Optional[str] = Field(None, description="自然语言修正指令，如「改成45块5」")

    model_config = ConfigDict(populate_by_name=True)
