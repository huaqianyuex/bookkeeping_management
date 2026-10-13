"""AI 模块 Pydantic 模型 — /api/ai

⚠️ 铁律（10-实现骨架.md §六 / 05 §0）：
- `/api/ai/**` 一律**裸返回**，不套 `{code,message,data}` 信封；
- 会话/消息时间戳是 **int 毫秒**（createdAt/updatedAt/deletedAt/timestamp 皆是）；
- 业务失败统一 `{"error": "中文"}`（HTTP 200），勿抛 HTTPException；
- 例外：鉴权 401 由依赖抛出，是唯一带 Result 结构的形态。

⚠️ 消费分析 / 预算规划的 `data` **内部字段是 snake_case**（total_expense / savings_rate /
monthly_budget...），与业务模块「对外 camelCase」的约定不同——前端 AiChat.jsx 按此读取，
不要自作主张改成驼峰。

历史清理（审查报告 P2-10）：本文件顶部原有一整段被 `#` 注释掉的旧定义，其字段约束
（如 SessionOut.user_id 可空、ChatIn 无长度上限）与现行契约不同，在被注释的状态下仍会被
误读为现行契约。已删除该注释死代码，并把其中的铁律说明提升为本模块 docstring 保留；
同时删除 207-211 行的重复 import、修正 `ChatOut` 缺失的 messageId。现行契约只看下方活跃类。
"""

from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from schemas.base import OrmBase


class ExpenseAnalyzeIn(BaseModel):
    """消费分析请求体（6.9）— 财务数据由服务端查库组包，前端只传诉求文本"""
    query: Optional[str] = Field("请分析我的消费情况", description="自然语言诉求，作为提示词 human 片段")


class BudgetPlanIn(BaseModel):
    """预算规划请求体（6.10）"""
    monthly_income: float = Field(..., alias="monthlyIncome", gt=0, description="月收入，必填")
    savings_goal: Optional[float] = Field(None, alias="savingsGoal", gt=0, description="月储蓄目标，>0；不传按 50/30/20 推导")

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
    """用户财务上下文 — 传给 LLM 的用户数据摘要（ai/context.py 组包）

    ⚠️ 历史不一致（已修）：本模型原先只有 4 个字段，而 ai/context.py 的
    build_user_context 实际返回 5 个键（多出 this_month / last_month_expense），
    且 analyze_chain.py 按 dict 下标消费 ctx['this_month'] / ['last_month_expense']。
    模型与真实契约不符 = 类型形同虚设，字段拼错也不会报错。现补齐真实字段。

    注：build_user_context 目前返回 dict 而非本模型（消费方 analyze_chain 用下标
    访问，改成模型要同步改两处调用）。本模型作为契约文档保留，改组包逻辑时须同步。
    """
    this_month: str = ""                                    # 统计月份 yyyy-MM
    total_income: float = 0
    total_expense: float = 0
    last_month_expense: float = 0                           # 环比用
    recent_records: List[dict] = Field(default_factory=list)  # 预留，当前组包未填充
    top_categories: List[dict] = Field(default_factory=list)


class FeedbackIn(BaseModel):
    """保存反馈请求体（6.13）— 对应 feedback 表 {message_id, rating, comment, timestamp}"""
    message_id: str = Field(..., alias="messageId", description="被评价的消息 ID（msg_...）")
    rating: int = Field(..., ge=1, le=5, description="评分 1–5")
    comment: Optional[str] = Field(None, description="文字反馈")

    model_config = ConfigDict(populate_by_name=True)


class BookkeepingOverride(BaseModel):
    """确认卡上用户改过的字段（按下标定位，不触发二次 LLM 解析）"""
    index: int = Field(..., ge=0, description="对应 parsed.items 的下标")
    amount: Optional[float] = Field(None, gt=0, le=99999999.99)
    category_id: Optional[int] = Field(None, alias="categoryId")
    date: Optional[str] = Field(None, description="yyyy-MM-dd")
    remark: Optional[str] = Field(None, max_length=200)
    type: Optional[int] = Field(None, ge=0, le=1, description="0=支出 1=收入")

    model_config = ConfigDict(populate_by_name=True)


class BookkeepingIn(BaseModel):
    """自然语言记账请求体（6.15）

    - client_msg_id 是强幂等键：重发同一条消息必须带同一个值；
    - draft_id 用于追问续写：把本次内容补进指定草稿（ai_bookkeeping_logs.id）；
    - dry_run=true 只解析不入账，返回 preview；
    - source 标记来源（text=手输 / voice=语音），仅落审计日志；
    - overrides 为确认卡字段覆盖（按 preview.items[].index 定位）。
    """
    message: str = Field(..., min_length=1, max_length=500, description="原始口语化文本，trim 后 1–500 字")
    session_id: Optional[str] = Field(None, alias="sessionId", description="AI 会话 ID；传入时消息写入 messages")
    client_msg_id: Optional[str] = Field(None, alias="clientMsgId", description="客户端 UUID 强幂等键")
    draft_id: Optional[int] = Field(None, alias="draftId", description="追问续写：目标草稿日志 ID")
    dry_run: bool = Field(False, alias="dryRun", description="true=只解析不入账")
    force: bool = Field(False, alias="force", description="true=跳过 5 分钟弱幂等窗口")
    source: str = Field("text", description="text=手输 / voice=语音")
    overrides: Optional[List[BookkeepingOverride]] = Field(None, description="确认卡字段覆盖")
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


class ErrorOut(BaseModel):
    """AI 模块统一失败结构（HTTP 200）"""
    error: str


class SessionCreateIn(BaseModel):
    """创建会话请求体"""
    title: Optional[str] = Field(None, max_length=50, description="会话标题，缺省「新对话」")


class SessionRenameIn(BaseModel):
    """重命名会话请求体"""
    title: str = Field(..., min_length=1, max_length=50, description="新标题，trim 后 1–50 字")


class SessionOut(OrmBase):
    """会话出参（裸 Session 对象）"""
    id: str
    user_id: int = Field(..., alias="userId")
    title: str
    auto_title: int = Field(1, alias="autoTitle", description="1=AI 可覆盖标题，0=用户已重命名锁定")
    created_at: int = Field(..., alias="createdAt")
    updated_at: int = Field(..., alias="updatedAt")
    deleted_at: int = Field(0, alias="deletedAt", description="0=未删；>0=软删毫秒")


class SessionListItem(BaseModel):
    """会话列表项"""
    id: str
    title: str
    preview: str = Field(..., description="最后一条消息，前缀「你: 」/「AI: 」，内容截 50 字")
    message_count: int = Field(0, alias="messageCount")
    created_at: int = Field(..., alias="createdAt")
    updated_at: int = Field(..., alias="updatedAt")

    model_config = ConfigDict(populate_by_name=True)


class SessionListOut(BaseModel):
    """会话列表出参（注意：与业务 PageResult 结构不同）"""
    items: List[SessionListItem] = Field(default_factory=list)
    total: int = 0


class MessageOut(OrmBase):
    """消息出参（裸数组元素）"""
    id: str
    session_id: str = Field(..., alias="sessionId")
    role: str = Field(..., description="user | assistant")
    content: str
    timestamp: int = Field(..., description="毫秒")


class ChatIn(BaseModel):
    """对话请求体（非流式 / 流式共用）"""
    session_id: str = Field(..., alias="sessionId")
    message: str = Field(..., min_length=1, max_length=2000,
                          description="1–2000 字，防止 token/费用放大")

    model_config = ConfigDict(populate_by_name=True)


class ChatOut(BaseModel):
    """非流式对话出参（字段名是 content，不是 answer）

    ⚠️ 契约漂移修正（审查报告 P2-10）：/chat 实际返回 `{"content", "messageId"}`，
    而此前本模型只声明 content。端点未声明 response_model，故此前只影响契约文档与
    构造校验；补上 message_id 后模型与真实响应一致。
    """
    content: str
    message_id: Optional[str] = Field(None, alias="messageId")

    model_config = ConfigDict(populate_by_name=True)


class SessionIdsIn(BaseModel):
    """AI 批量删除会话请求体（元素为 string，与业务模块 int 版 IdsIn 不同）"""
    ids: List[str] = Field(..., min_length=1, description="会话 ID 数组，单次最多 50 条")


# ── 自然语言记账出参（6.15）────────────────────────────────────────────
# 仅用于「构造」响应再 .model_dump(by_alias=True) 裸返回，端点仍不声明 response_model；
# 字段名对外是 camelCase，与 05 §6.2 的四种 action 契约一致。


class BkRecordItem(BaseModel):
    """入账/重复明细（created.records 与 duplicate.records 共用）"""
    id: int
    amount: float
    type: int = Field(1, description="0=支出 1=收入")
    category_id: Optional[int] = Field(None, alias="categoryId")
    category_name: Optional[str] = Field(None, alias="categoryName")
    record_date: str = Field(..., alias="recordDate", description="yyyy-MM-dd")
    remark: Optional[str] = None

    model_config = ConfigDict(populate_by_name=True)


class BkPreviewItem(BaseModel):
    """preview/clarify 里的预览条目（未入账，可缺金额）"""
    index: int = Field(0, description="对应 parsed.items 的下标，确认卡按此回传 overrides")
    amount: Optional[float] = None
    amount_raw: Optional[str] = Field(None, alias="amountRaw")
    type: Optional[int] = Field(None, description="0=支出 1=收入；预览条目可能尚未推导（不默认收入）")
    category_name: Optional[str] = Field(None, alias="categoryName")
    category_id: Optional[int] = Field(None, alias="categoryId")
    date: Optional[str] = None
    date_expr: Optional[str] = Field(None, alias="dateExpr")
    remark: Optional[str] = None
    confidence: float = 0.0

    model_config = ConfigDict(populate_by_name=True)


class BkCreatedOut(BaseModel):
    """action=created：已入账（可能多笔）"""
    action: str = "created"
    request_id: str = Field(..., alias="requestId")
    records: List[BkRecordItem] = Field(default_factory=list)
    total_amount: float = Field(0, alias="totalAmount")
    echo: str
    warnings: List[str] = Field(default_factory=list)
    errors: List[Any] = Field(default_factory=list)
    session_id: Optional[str] = Field(None, alias="sessionId")
    message_id: Optional[str] = Field(None, alias="messageId")

    model_config = ConfigDict(populate_by_name=True)


class BkIgnoredOut(BaseModel):
    """action=ignored：非消费类消息"""
    action: str = "ignored"
    request_id: str = Field(..., alias="requestId")
    reason: str = Field("not_expense", description="not_expense/query/income_unsupported/too_ambiguous/no_recent_record")
    echo: str
    records: List[Any] = Field(default_factory=list)

    model_config = ConfigDict(populate_by_name=True)


class BkClarifyOut(BaseModel):
    """action=clarify：缺金额追问"""
    action: str = "clarify"
    request_id: str = Field(..., alias="requestId")
    draft_id: Optional[int] = Field(None, alias="draftId")
    question: str
    missing: List[str] = Field(default_factory=list)
    preview: dict = Field(default_factory=dict, description='{"items": [...]}')
    records: List[Any] = Field(default_factory=list)

    model_config = ConfigDict(populate_by_name=True)


class BkDuplicateOut(BaseModel):
    """action=duplicate：命中幂等，未重复入账"""
    action: str = "duplicate"
    request_id: str = Field(..., alias="requestId")
    origin_request_id: str = Field(..., alias="originRequestId")
    records: List[BkRecordItem] = Field(default_factory=list)
    echo: str
    hint: Optional[str] = None

    model_config = ConfigDict(populate_by_name=True)