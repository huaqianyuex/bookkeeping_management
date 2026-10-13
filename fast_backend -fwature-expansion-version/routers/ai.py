"""AI 助手路由 — /api/ai（17 个端点骨架，契约见 10-实现骨架.md §六）

⚠️ **本模块返回裸 JSON，不套 `{code,message,data}` 信封**（05 §0 铁律）。

原因（已核对前端）：`src/api/request.js` 的响应拦截器是 `return response.data`，
拿到的就是**整个响应体**；而 `pages/AiChat.jsx` 直接按裸结构消费：
    - `const res  = await listSessions(...)   → res.items / res.total`
    - `const data = await createSession(...)  → data.id`
    - `const msgs = await getSessionMessages(...) → msgs || []`
若用 success_response 包一层，前端拿到的是 `{code,message,data}`，
`res.items` / `data.id` 全是 undefined —— 会话列表空白、创建会话拿不到 id。

三条铁律（违反即前端崩）：
1. 一律裸返回；业务失败统一 `return ai_error("中文")`（HTTP 200），**勿抛 HTTPException**
   （会被全局异常处理器包成 Result 信封，破坏裸契约）；
2. 会话/消息时间戳是 **int 毫秒**，不是 ISO 字符串（前端 Date.now() 直接比对）；
3. SSE 事件行 `data: {"type":"content"|"done"|"error",...}\n\n`（6.8）。

⚠️ 路由注册顺序：`/sessions/batch-delete` 必须在 `/sessions/{session_id}` **之前**，
Starlette 按注册顺序匹配，否则 "batch-delete" 会被当成 session_id 吃掉。

⚠️ **权限边界（管理员不参与 AI 对话与记账）**：
本模块绝大多数端点是「用户侧业务功能」，统一挂 `get_current_regular_user` ——
**管理员账号（role=1）调用一律 403**（矩阵见 utils/auth.py 模块 docstring）。
仅两个端点是管理员专用，挂 `get_current_admin`，**不要改成普通用户依赖**：
- `POST /faq/rebuild`（全量 Embedding 有真金白银成本，需管理员触发）；
- `GET  /admin/stats`（全站跨用户聚合统计，不适用普通用户）。
"""
import hashlib
import json
import logging
import struct
from typing import Any

from fastapi import APIRouter, Depends, Query, HTTPException, File, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse
from langchain_core.messages import HumanMessage, SystemMessage
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ai import memory, chat_chain, analyze_chain, faq_retriever
from ai import context as ai_context
from ai import normalizers as bk_norm
from ai import category_alias as bk_alias
from ai import security as ai_security
from ai import observability as ai_obs
from ai import retry as ai_retry
from ai import stt as ai_stt
from ai.stt import ProviderNotConfigured
from ai.bookkeeping_chain import parse_bookkeeping
from config.db_config import get_db, AsyncSessionLocal
from config.settings import (
    MEMBERSHIP_PLANS, STT_ENABLED, STT_MAX_SECONDS, STT_MAX_SIZE_MB,
    VOICE_RATE_LIMIT_PER_MIN, FAQ_INJECT_ENABLED, FAQ_RATE_LIMIT_PER_MIN,
    BK_LOW_CONFIDENCE, BK_PREVIEW_RATE_LIMIT_PER_MIN,
    BK_PREVIEW_CACHE_TTL_SECONDS, BK_PREVIEW_CACHE_MAX_ENTRIES,
)
from crud import ai as ai_crud
from crud import membership as membership_crud
from models.bookkeeping import AiBookkeepingLog
from models.record import Record
from schemas.ai import (
    SessionCreateIn,
    SessionIdsIn,
    SessionOut,
    SessionListItem,
    SessionRenameIn, ChatIn,
    FeedbackIn, BookkeepingIn, BookkeepingAmendIn,
    ExpenseAnalyzeIn, BudgetPlanIn,
    BkCreatedOut, BkIgnoredOut, BkClarifyOut, BkDuplicateOut, BkRecordItem, BkPreviewItem, MessageOut,
)
from utils import ai_concurrency
from utils.auth import get_current_admin, get_current_regular_user
from utils.throttle import voice_rate_limiter, SlidingWindowRateLimiter, TtlCache

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ai", tags=["ai"])


def ai_error(msg: str, *, code: str | None = None) -> dict[str, Any]:
    """AI 业务失败统一返回：HTTP 200 + 裸 {"error": "中文"}

    ``code`` 可选：裸 error 契约下前端只依赖 ``error`` 即可，故默认不带；
    但「配额超限」这类前端需要分支处理的场景带上机器可读 code 更省事。
    纯增量字段——旧前端不读也不受影响。
    """
    body: dict[str, Any] = {"error": msg}
    if code is not None:
        body["code"] = code
    return body


# ── 会员配额闸门 ────────────────────────────────────────────────────────
# AI 模块是裸 JSON 契约：超额用 JSONResponse(429) 直返，不抛 HTTPException
# （抛异常会被全局处理器包成 {code,message,data} 信封，破坏前端解析）。
_KIND_LABEL = {"chat": "AI 对话", "analyze": "AI 分析", "bookkeeping": "AI 智能记账"}


async def _quota_gate(db: AsyncSession, user_id: int, kind: str,
                      plan: dict | None = None) -> dict | None:
    """配额闸门：通过则当日用量 +1 并返回 None；超额返回 429 响应体。

    用 consume_quota（单语句原子「校验 + 自增」）：先 check 再 incr 的两步写法在并发下
    会放行一批超额请求（配额形同虚设）。
    计数时机 = 实际触发 LLM 之前；LLM 调用失败不回滚（防刷量优先，行业惯例）。
    幂等/去重短路未触达 LLM 的请求不应调用本闸门（如 bookkeeping 的 duplicate 分支）。
    等级判定只走 membership_crud.get_tier 单一入口，勿在此自行比较 expires_at。
    plan 可由调用方传入（已算过 tier 时避免重复查询）。

    例外：bookkeeping 的 dryRun=true 预览**不走本闸门**——它只解析不入账，若也扣一次
    daily_bookkeeping，「预览→确认」确认框流程会让一次记账扣 2 次额度；预览改走
    bookkeeping_preview_rate_limiter（见 bookkeeping() 第 3.5 步）。
    """
    if plan is None:
        tier = await membership_crud.get_tier(db, user_id)
        plan = MEMBERSHIP_PLANS[tier]
    ok, used, limit = await membership_crud.consume_quota(
        db, user_id, plan, kind
    )
    if not ok:
        return {
            "error": f"今日{_KIND_LABEL[kind]}次数已用完（{used}/{limit}），升级会员解锁更多额度",
            "code": "QUOTA_EXCEEDED",
            "used": used,
            "limit": limit,
        }
    return None

# ── 会话 ────────────────────────────────────────────────────────────────

@router.post("/sessions", summary="创建会话")
async def create_session(
    body: SessionCreateIn,
    user: int = Depends(get_current_regular_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    title = (body.title or "").strip() or "新对话"[:50]
    session = await ai_crud.create_session(db, user, title)
    return SessionOut.model_validate(session).model_dump(by_alias=True)


@router.get("/sessions", summary="会话列表")
async def list_sessions(
    user_id: int = Depends(get_current_regular_user),
    db: AsyncSession = Depends(get_db),
    keyword: str = Query(""),
    sort: str = Query("updated"),   # 仅 updated / created
    order: str = Query("desc"),     # 仅 asc / desc
    page: int = Query(1, ge=1),
    size: int = Query(20),
):
    """6.2 会话列表：返回裸 {items, total}（**不是** PageResult 的 records/total/pages）"""
    rows, total = await ai_crud.list_sessions(db, user_id, keyword, sort, order, page, size)
    items = []
    for session, preview_content, preview_role, message_count in rows:
        preview = preview_content or ""
        prefix = "你: " if preview_role == "user" else "AI: "
        items.append(SessionListItem(
            id=session.id,
            title=session.title,
            preview=(prefix + preview)[:50],
            message_count=message_count,
            created_at=session.created_at,
            updated_at=session.updated_at,
        ).model_dump(by_alias=True))
    return {"items": items, "total": total}


# ⚠️ 必须注册在 `/sessions/{session_id}` 之前（见模块头说明）
@router.post("/sessions/batch-delete", summary="批量删除会话")
async def batch_delete_sessions(
    body: SessionIdsIn,
    user_id: int = Depends(get_current_regular_user),
    db: AsyncSession = Depends(get_db),
):
    ids=list(dict.fromkeys(body.ids)) #去重
    if not ids or len(ids)>50:
        return ai_error("最多删除50条")

    delete=await ai_crud.batch_soft_delete_sessions(db,user_id,ids)
    return {"success": True, "deleted": delete}


@router.patch("/sessions/{session_id}", summary="重命名会话")
async def rename_session(
    session_id: str,
    body: SessionRenameIn,
    user_id: int = Depends(get_current_regular_user),
    db: AsyncSession = Depends(get_db),
):
    """6.3 重命名：返回 {success: true, session: {...}}；改名后 autoTitle 置 0（锁定标题）"""
    session = await ai_crud.rename_session(db, session_id, user_id, body.title)
    if session is None:
        return ai_error("会话不存在")
    return {"success": True, "session": SessionOut.model_validate(session).model_dump(by_alias=True)}


@router.delete("/sessions/{session_id}", summary="删除会话")
async def delete_session(
    session_id: str,
    user_id: int = Depends(get_current_regular_user),
    db: AsyncSession = Depends(get_db),
):

    """6.4 软删单个会话（deleted_at=毫秒）：返回 {success: bool}"""
    ok = await ai_crud.soft_delete_session(db, session_id, user_id)
    return {"success": ok}


@router.get("/sessions/{session_id}/messages", summary="会话消息")
async def session_messages(
    session_id: str,
    user_id: int = Depends(get_current_regular_user),
    db: AsyncSession = Depends(get_db),
):
    """6.6 会话消息：返回**裸数组**（MessageOut 列表，按 timestamp 升序）；
    会话不存在/非本人/已删返回 []"""
    session = await ai_crud.get_user_session(db, session_id, user_id)
    if session is None:
        return []

    msgs = await ai_crud.list_messages(db, session_id)
    return [
        MessageOut.model_validate(m).model_dump(by_alias=True)
        for m in msgs
    ]


# ── 对话 ────────────────────────────────────────────────────────────────

async def _build_system_prompt(db: AsyncSession, user_id: int, query: str) -> str:
    """组装对话用 system prompt = 基础约束 + 财务数据块 + 知识库块。

    两块都是「有则注入、无则跳过」，任一块构造失败都不阻断对话：
    - 财务数据块：ai/context.py，查库失败会返回显式的「查不到」口径块；
    - 知识库块：ai/faq_retriever.build_knowledge_block，内部有规则闸门，
      只有像「预算怎么设」「支持哪些分类」这类知识库问句才会真的发起一次
      Embedding 检索，其余消息零额外成本。

    之所以抽成公共函数：/chat 与 /chat/stream 原本各自复制了一份拼接逻辑，
    两边很容易改一处漏一处。
    """
    blocks: list[str] = []
    try:
        blocks.append(await ai_context.build_finance_block(db, user_id))
    except Exception:
        logger.exception("build_finance_block failed, user_id=%s", user_id)
    if FAQ_INJECT_ENABLED:
        try:
            blocks.append(await faq_retriever.build_knowledge_block(query))
        except Exception:
            # 检索失败静默降级：对话本身不依赖知识库
            logger.exception("build_knowledge_block failed, user_id=%s", user_id)
    return chat_chain.build_system_prompt(*blocks)


def _safe_user_text(text: str) -> str:
    """用户输入送入 Prompt 前的统一清洗（方案 §3.5 P0）。

    手机号 / 银行卡 / 身份证 / 邮箱本地脱敏为占位符，同时过滤提示词注入话术。
    落库仍保留原文（用户要看到自己发过什么），**只有上云的那一份是脱敏的**。
    """
    cleaned = ai_security.sanitize(text)
    if cleaned != (text or ""):
        # 记录命中类型与脱敏后长度即可，绝不把原文写进日志
        logger.info("ai input sanitized: raw_len=%d clean_len=%d injection=%s",
                    len(text or ""), len(cleaned),
                    ai_security.has_injection_risk(text))
    return cleaned


@router.post("/chat", summary="非流式对话")
async def chat(
    body: ChatIn,
    user_id: int = Depends(get_current_regular_user),
    db: AsyncSession = Depends(get_db),
):
    if not (body.session_id or "").strip() or not (body.message or "").strip():
        raise HTTPException(400, "sessionId 和 message 不能为空")

    # 会话归属校验：非本人/已删 → 裸 error（HTTP 200）
    session = await ai_crud.get_user_session(db, body.session_id, user_id)
    if session is None:
        return ai_error("会话不存在")

    # 会员配额：超额直接 429（裸 JSON，code=QUOTA_EXCEEDED）
    tier = await membership_crud.get_tier(db, user_id)
    plan = MEMBERSHIP_PLANS[tier]

    # 先占并发槽再扣额度：顺序反了会在并发满时白扣一次额度
    release = await ai_concurrency.try_acquire(user_id, plan["concurrency"])
    if release is None:
        return JSONResponse(status_code=429, content={
            "error": "您的对话并发已达上限，请等待当前回复完成",
            "code": "CONCURRENCY_LIMIT",
        })
    try:
        quota_error = await _quota_gate(db, user_id, "chat", plan=plan)
        if quota_error:
            return JSONResponse(status_code=429, content=quota_error)

        # 组装消息：system(含财务数据块 + 知识库块) + 历史窗口 + 本次 human
        history = await memory.build_history(db, body.session_id)
        system_prompt = await _build_system_prompt(db, user_id, body.message)
        messages = [SystemMessage(content=system_prompt), *history,
                    HumanMessage(content=_safe_user_text(body.message))]

        # 落库用户消息
        await ai_crud.add_message(db, body.session_id, "user", body.message)

        # 调 LLM（非流式，一次拿全）
        try:
            content = await chat_chain.chat(messages, premium=plan["premium_model"], user_id=user_id)
        except Exception as e:
            logger.exception("chat failed, user_id=%s", user_id)
            if ai_retry.is_upstream_busy(e):
                return ai_error("AI 助手当前繁忙，请稍后重试", code="UPSTREAM_BUSY")
            return ai_error("AI 服务暂不可用，请稍后重试")

        # 落库助手消息
        ai_msg = await ai_crud.add_message(db, body.session_id, "assistant", content)

        return {"content": content, "messageId": ai_msg.id}
    finally:
        release()


@router.post("/chat/stream", summary="流式对话（SSE）")
async def chat_stream(
    body: ChatIn,
    user_id: int = Depends(get_current_regular_user),
    db: AsyncSession = Depends(get_db),
):
    """6.8 流式对话：text/event-stream

    SSE 事件行固定 `data: {"type":"content"|"done"|"error",...}\\n\\n`；
    前端手写 ReadableStream 解析。缺 sessionId/message 是本模块唯一 HTTP 400 的场景。
    """
    if not (body.session_id or "").strip() or not (body.message or "").strip():
        raise HTTPException(400, "sessionId 和 message 不能为空")

    # 会话归属校验（生成器启动前完成，否则错误只能以 SSE error 事件发出）
    session = await ai_crud.get_user_session(db, body.session_id, user_id)
    if session is None:
        return ai_error("会话不存在")

    def sse(d: dict) -> str:
        return f"data: {json.dumps(d, ensure_ascii=False)}\n\n"

    # 会员配额（同样在生成器之前判定：进入 SSE 后 HTTP 状态码已发出，只能发 error 事件）
    tier = await membership_crud.get_tier(db, user_id)
    plan = MEMBERSHIP_PLANS[tier]

    # 先占并发槽、后扣额度：反序会在并发满时白扣一次配额（用户既没结果又被计费）。
    # 满额仍以 SSE error 事件返回（HTTP 200，保持流式契约，与 utils/ai_concurrency 用法一致）。
    release = await ai_concurrency.try_acquire(user_id, plan["concurrency"])
    if release is None:
        return StreamingResponse(
            iter([sse({
                "type": "error",
                "code": "CONCURRENCY_LIMIT",
                "error": "您的对话并发已达上限，请等待当前回复完成",
            })]),
            media_type="text/event-stream",
        )

    quota_error = await _quota_gate(db, user_id, "chat", plan=plan)
    if quota_error:
        release()
        return JSONResponse(status_code=429, content=quota_error)

    async def event_gen():
        # Depends(get_db) 的会话在响应头发出后即被关闭（FastAPI>=0.106 yield 依赖的
        # 生命周期只到 response start），流式期间复用会隐式重开事务并泄漏连接；
        # 这里为生成器单独建会话，随流结束关闭。add_message 内部自带 commit。
        async with AsyncSessionLocal() as gen_db:
            try:
                # 1) 落库用户消息
                try:
                    await ai_crud.add_message(gen_db, body.session_id, "user", body.message)
                except Exception:
                    logger.exception("stream: save user message failed, user_id=%s", user_id)
                    yield sse({"type": "error", "error": "消息保存失败"})
                    return

                # 2) 组装消息并流式产出（注入实时财务数据，模型才能分析当月账单）
                history = await memory.build_history(gen_db, body.session_id)
                system_prompt = await _build_system_prompt(gen_db, user_id, body.message)
                messages = [SystemMessage(content=system_prompt), *history,
                    HumanMessage(content=_safe_user_text(body.message))]

                full = []
                try:
                    async for chunk in chat_chain.chat_stream(messages, premium=plan["premium_model"], user_id=user_id):
                        full.append(chunk)
                        yield sse({"type": "content", "content": chunk})
                except Exception as e:
                    logger.exception("stream: LLM failed, user_id=%s", user_id)
                    # 上游过载与「服务故障」分开报，前端可据此展示「稍后重试」而不是
                    # 让用户怀疑自己的输入（P1-6）。code 为附加字段，旧前端只读 error 不受影响。
                    if ai_retry.is_upstream_busy(e):
                        yield sse({"type": "error", "code": "UPSTREAM_BUSY",
                                   "error": "AI 助手当前繁忙，请稍后重试"})
                    else:
                        yield sse({"type": "error", "error": "AI 服务暂不可用，请稍后重试"})
                    return

                # 3) 全部产出后，落库助手完整回复，再发 done
                try:
                    ai_msg = await ai_crud.add_message(gen_db, body.session_id, "assistant", "".join(full))
                except Exception:
                    logger.exception("stream: save assistant message failed, user_id=%s", user_id)
                    ai_msg = None
                yield sse({"type": "done", "messageId": ai_msg.id if ai_msg else None})
            finally:
                release()

    return StreamingResponse(event_gen(), media_type="text/event-stream")


# ── 分析 / 预算 ────────────────────────────────────────────────────────

@router.post("/analyze/expenses", summary="消费分析")
async def analyze_expenses(
    body: ExpenseAnalyzeIn,
    user_id: int = Depends(get_current_regular_user),
    db: AsyncSession = Depends(get_db),
):
    """6.9 消费分析：返回 {success: true, data: ExpenseAnalysis}

    财务数据由服务端查库组包（ai/context.py），前端不传金额；data 内字段是 snake_case。
    """
    plan = MEMBERSHIP_PLANS[await membership_crud.get_tier(db, user_id)]
    release = await ai_concurrency.try_acquire(user_id, plan["concurrency"])
    if release is None:
        return JSONResponse(status_code=429, content={
            "error": "您的 AI 并发已达上限，请等待当前请求完成", "code": "CONCURRENCY_LIMIT",
        })
    try:
        quota_error = await _quota_gate(db, user_id, "analyze", plan=plan)
        if quota_error:
            return JSONResponse(status_code=429, content=quota_error)
        ctx = await ai_context.build_user_context(db, user_id)
        # body.query 此前收而不传，用户诉求被丢弃（analyze_chain 内硬编码默认文案）
        # P0-3：诉求原文含手机号/卡号等 PII，上云前统一走 _safe_user_text 脱敏
        data = await analyze_chain.analyze_expense(
            ctx, query=_safe_user_text(body.query), user_id=user_id
        )
        return {"success": True, "data": data.model_dump()}
    except Exception:
        # 不用回显原始异常：DB/LLM 报错可能含 SQL 语句、内部路径、API key 提示
        logger.exception("analyze expenses failed, user_id=%s", user_id)
        return ai_error("分析失败，请稍后重试")
    finally:
        release()


@router.post("/analyze/budget", summary="预算规划")
async def analyze_budget(
    body: BudgetPlanIn,
    user_id: int = Depends(get_current_regular_user),
    db: AsyncSession = Depends(get_db),
):
    """6.10 预算规划：返回 {success: true, data: BudgetPlan}"""
    plan = MEMBERSHIP_PLANS[await membership_crud.get_tier(db, user_id)]
    release = await ai_concurrency.try_acquire(user_id, plan["concurrency"])
    if release is None:
        return JSONResponse(status_code=429, content={
            "error": "您的 AI 并发已达上限，请等待当前请求完成", "code": "CONCURRENCY_LIMIT",
        })
    try:
        quota_error = await _quota_gate(db, user_id, "analyze", plan=plan)
        if quota_error:
            return JSONResponse(status_code=429, content=quota_error)
        ctx = await ai_context.build_user_context(db, user_id)
        data = await analyze_chain.plan_budget(
            body.monthly_income, body.savings_goal, ctx, user_id=user_id
        )
        return {"success": True, "data": data.model_dump()}
    except Exception:
        logger.exception("budget plan failed, user_id=%s income=%s goal=%s",
                         user_id, body.monthly_income, body.savings_goal)
        return ai_error("预算规划失败")
    finally:
        release()


# ── FAQ ────────────────────────────────────────────────────────────────

# /faq/search 是认证用户可直调的 Embedding 计费口：cache miss 即一次 Embedding 调用
# （真金白银）。挂独立滑动窗口限流（P0-4，口径同语音转写），端点必须直接引用模块全局，
# 否则测试对 ai_router.faq_search_rate_limiter 的 monkeypatch 不生效。
faq_search_rate_limiter = SlidingWindowRateLimiter(
    max_calls=FAQ_RATE_LIMIT_PER_MIN, window=60
)


@router.get("/faq/search", summary="FAQ 语义检索")
async def faq_search(
    query: str,
    user: int = Depends(get_current_regular_user),
    db: AsyncSession = Depends(get_db),
):
    """6.11 FAQ 检索：正常 {"results":[...], "mode": ...}

    mode 口径：
    - "vector"  向量检索命中（score 为归一化余弦，0~1）
    - "keyword" 降级为字符重合度检索（Embedding 不可用或向量索引未构建）
    - "empty"   空 query / 索引为空，无从检索
    - "stale"   知识库已变更但索引未重建，结果不可信，故不返回结果

    两种失败形态要区分：无命中**没有** fallback 键；整体抛异常才有。
    历史问题：top_k 硬编码 3，绕过 FAQ_TOP_K 配置；且降级是静默的，
    前端拿到 score 却无从判断它是余弦分还是字符重合度分（两者量纲不可比）。

    P0-4：per-user 滑动窗口限流，防止认证用户无限刷 Embedding 计费。
    """
    ok, retry_after = faq_search_rate_limiter.allow(f"faq:{user}")
    if not ok:
        return JSONResponse(status_code=429, content={
            "error": f"检索太频繁，请 {retry_after} 秒后再试",
            "code": "RATE_LIMIT",
        })
    try:
        # top_k 不传，用 search_faq_detailed 默认值（读 FAQ_TOP_K）
        results, mode = await faq_retriever.search_faq_detailed(query)
        return {"results": results, "mode": mode}
    except Exception:
        # 失败不产生 Embedding 计费 → 退还本次占位，避免把用户的每分钟名额
        # 耗在注定失败的请求上（占位在 allow 里是原子的，不存在 check→record 并发窗口）
        faq_search_rate_limiter.refund(f"faq:{user}")
        logger.exception("faq search failed, query_len=%d", len(query or ""))
        return {"results": [], "fallback": True}


@router.post("/faq/rebuild", summary="重建 FAQ 向量索引")
async def faq_rebuild(
    user_id: int = Depends(get_current_admin),   # 仅管理员可触发：embedding 成本/频率防护
    db: AsyncSession = Depends(get_db),
):
    """6.12 重建 FAQ 索引：成功 {success: true, count: n}；失败 {error: "重建失败"}

    重建会调全量 embedding，需仅管理员调用；异常详情只记日志，不透出原始报错。

    并发保护：faq_retriever.rebuild 内部是 single-flight + 60s 冷却，
    多个管理员同时点「重建」只有第一个真正执行（否则重复付费），
    其余返回 RebuildBusy 的中文提示而不是系统错误。
    """
    try:
        rows = await ai_crud.list_faq(db)
        count = await faq_retriever.rebuild(rows)   # 清空->重载->算向量->存内存
        return {"success": True, "count": count}
    except faq_retriever.RebuildBusy as e:
        # 并发/冷却：属正常业务提示，不是系统故障
        return {"error": str(e), "retryAfter": await faq_retriever.rebuild_cooldown_left()}
    except Exception:
        logger.exception("FAQ rebuild failed, user_id=%s", user_id)
        return {"error": "重建失败"}


# ── 语音 ────────────────────────────────────────────────────────────────

_ALLOWED_AUDIO_EXT = {"mp3", "m4a", "wav", "aac", "webm", "ogg"}


def _looks_like_audio(data: bytes, ext: str) -> bool:
    """按扩展名核对魔数：Content-Type/文件名均可伪造，防止任意字节消耗外部 ASR 计费"""
    if len(data) < 12:
        return False
    if ext == "wav":
        return data[:4] == b"RIFF" and data[8:12] == b"WAVE"
    if ext == "mp3":
        return data[:3] == b"ID3" or (data[0] == 0xFF and (data[1] & 0xE0) == 0xE0)
    if ext in ("m4a", "aac"):
        return data[4:8] == b"ftyp" or (data[0] == 0xFF and (data[1] & 0xF6) == 0xF0)
    if ext == "webm":
        return data[:4] == b"\x1a\x45\xdf\xa3"
    if ext == "ogg":
        return data[:4] == b"OggS"
    return False


def _wav_duration_seconds(data: bytes) -> float | None:
    """从 WAV 容器解析时长（秒）；无法可靠解析时返回 None。

    为什么需要（审查报告 P1-7）：STT_MAX_SECONDS 此前只是下发给前端的录音上限，
    服务端不校验，客户端可以绕过直接上传长音频，外部 ASR 按音频时长计费。

    实现要点：
    - 只认 RIFF/WAVE 容器，从 offset 12 起逐个子块扫描——不假设 fmt 块一定是 16 字节、
      也不假设 data 紧跟在 fmt 之后（扩展 fmt / LIST 块都常见）；
    - 用 fmt 块的 byte_rate 与 data 块的**实际字节数**推算时长，**不采信客户端可控的
      data 块声明长度**——伪造 RIFF 头（声明 1 秒、实传 10 分钟）不能绕过时长守卫；
    - **返回 None 表示「未校验」**（非 WAV、头损坏、缺 fmt/byte_rate），
      绝不因解析失败而阻断转写——其余格式（mp3/m4a/webm/ogg）无统一时长头，
      由 provider 侧超时兜底。
    """
    if len(data) < 12 or data[:4] != b"RIFF" or data[8:12] != b"WAVE":
        return None
    byte_rate = 0
    pos = 12
    while pos + 8 <= len(data):
        chunk_id = data[pos:pos + 4]
        chunk_size = struct.unpack_from("<I", data, pos + 4)[0]
        body = pos + 8
        if chunk_id == b"fmt ":
            # PCM WAV 的 byte_rate 在 fmt 块偏移 8 处（4 字节）
            if chunk_size < 16 or body + 16 > len(data):
                return None
            byte_rate = struct.unpack_from("<I", data, body + 8)[0]
        elif chunk_id == b"data":
            if byte_rate <= 0:
                return None
            # 时长只按**实际字节数**算，不采信 data 块的声明长度。
            # 声明长度是客户端可控的 RIFF 头字段：伪造「声明 1 秒、实际传 10 分钟」
            # 即可绕过 STT_MAX_SECONDS；而真实音频长度本就等于容器中 data 块的
            # 字节数，声明值没有任何可信度。截断上传同样按实际长度算（偏短，安全方向）。
            return max(len(data) - body, 0) / byte_rate
        # 子块按声明长度前进；奇数长度需 1 字节对齐 padding
        pos = body + chunk_size + (chunk_size & 1)
    return None


# 语音是按次计费的外部调用：免费/会员两档滑动窗口限流（内存态，口径同 ai_concurrency）。
# 注意：端点里必须直接引用模块全局（而非装进 dict），否则测试对
# ai_router.voice_rate_limiter 的 monkeypatch 不生效。
voice_rate_limiter_member = SlidingWindowRateLimiter(
    max_calls=VOICE_RATE_LIMIT_PER_MIN * 4, window=60
)


@router.get("/voice/config", summary="语音功能开关")
async def voice_config(user_id: int = Depends(get_current_regular_user)):
    """6.18 前端据此决定是否渲染话筒按钮（实施指南 §2.4 的开关下发）"""
    return {"enabled": STT_ENABLED, "maxSeconds": STT_MAX_SECONDS}


@router.post("/voice/transcribe", summary="语音转写")
async def voice_transcribe(
    file: UploadFile = File(...),
    user_id: int = Depends(get_current_regular_user),
    db: AsyncSession = Depends(get_db),
):
    """6.19 语音转写：裸 {text, language, confidence}；失败 ai_error

    音频只在内存流转，不落盘、不写库。转写空文本返回 {"text": ""}（不是故障），
    由前端提示「没听清」。

    审查报告 P1-7 的两处修正：
    - 限流口径：转写失败不产生 ASR 计费，不该白占用户每分钟的名额。但「成功才记」
      的 check+record 写法两次加锁、中间隔着 await，N 个并发请求可全部通过 check
      再依次执行，把放行量放大 N 倍——而并发刷量正是限流要防的攻击形态。
      故改为 allow（原子查+记，占位置于本地校验之后、转写之前）+ 失败 refund 退还，
      既守住并发额度，又保住「失败不占槽」。
    - STT_MAX_SECONDS 此前只下发给前端、服务端不校验，客户端可绕过上传长音频。
      对可解析的 WAV 补一道服务端时长校验（其余格式无统一时长头，不校验）。
    """
    if not STT_ENABLED:
        return ai_error("语音识别未启用")

    # 1) 会员分档决定限流额度（ASR 是按次计费的外部调用，需独立成本防护）。
    #    占位动作推迟到步骤 4 转写**之前**原子完成（allow = 查+记一次锁内完成），
    #    失败由 refund 退还；上面的本地校验全部先于占位，不会白烧用户名额。
    tier = await membership_crud.get_tier(db, user_id)
    limiter = voice_rate_limiter_member if tier == 1 else voice_rate_limiter

    # 2) 扩展名白名单（含 webm：H5 MediaRecorder 产出 webm/opus）
    filename = (file.filename or "audio.m4a").strip()
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in _ALLOWED_AUDIO_EXT:
        return ai_error("不支持的音频格式，请使用 mp3 / m4a / wav / aac / webm")

    # 分块读取：超过上限立即断开，不把超大文件整体读进内存（防打爆进程）
    limit = STT_MAX_SIZE_MB * 1024 * 1024
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await file.read(256 * 1024)
        if not chunk:
            break
        total += len(chunk)
        if total > limit:
            return ai_error(f"音频过大，请控制在 {STT_MAX_SIZE_MB}MB 以内")
        chunks.append(chunk)
    data = b"".join(chunks)
    if not data:
        return ai_error("音频内容为空")

    # 3) 魔数核对：拒绝改了后缀的任意字节
    if not _looks_like_audio(data, ext):
        return ai_error("音频内容与格式不符，请重新录音后再试")

    # 3.5) 服务端时长校验（P1-7）：仅 WAV 能可靠解析时长；解析不出（None）
    # 视为「未校验」放行，由 provider 的 timeout 兜底，避免误伤正常录音。
    if ext == "wav":
        duration = _wav_duration_seconds(data)
        if duration is not None and duration > STT_MAX_SECONDS:
            return ai_error(f"录音过长，请控制在 {STT_MAX_SECONDS} 秒以内")

    # 4) 原子占位后转写（异常不回显底层报错：URL/key 提示可能泄露）。
    #    allow 与后续 await 之间无检查-记录窗口，并发刷量不会被放大 N 倍。
    ok, retry_after = limiter.allow(f"voice:{user_id}")
    if not ok:
        return ai_error(f"说话太频繁，请 {retry_after} 秒后再试")
    try:
        provider = ai_stt.get_stt_provider()
        result = await provider.transcribe(data, filename)
    except ProviderNotConfigured:
        limiter.refund(f"voice:{user_id}")
        return ai_error("语音识别未启用")
    except Exception:
        limiter.refund(f"voice:{user_id}")
        logger.exception("voice transcribe failed user_id=%s size=%s", user_id, len(data))
        return ai_error("语音识别暂不可用，请稍后重试")

    return {"text": result.text, "language": result.language, "confidence": result.confidence}


# ── 反馈 / 统计 ────────────────────────────────────────────────────────

@router.post("/feedback", summary="保存反馈")
async def submit_feedback(
    body: FeedbackIn,
    user_id: int = Depends(get_current_regular_user),
    db: AsyncSession = Depends(get_db),
):
    # submit_feedback 里，写库前加一步归属校验
    msg_ok = await ai_crud.check_message_owner(db, body.message_id, user_id)
    if not msg_ok:
        return ai_error("消息不存在")
    """6.13 保存反馈：返回 {success: true}；写库失败 {"error": "保存失败"}"""
    try:
        await ai_crud.create_feedback(db, user_id, body.message_id, body.rating, body.comment)
        return {"success": True}
    except Exception:
        logger.exception("feedback save failed, user_id=%s message_id=%s", user_id, body.message_id)
        return ai_error("保存失败")


@router.get("/admin/stats", summary="AI 会话统计")
async def ai_admin_stats(
    user_id: int = Depends(get_current_admin),   # 6.14：仅管理员可见（路径带 admin 前缀，权限应一致）
    db: AsyncSession = Depends(get_db),
):
    """6.14 AI 使用统计（仅管理员）：会话/消息/反馈计数 + Token 与延迟报表

    返回的是全站总体统计（带跨用户聚合数据），不适用普通用户。
    历史版本挂 get_current_user 且存在签名错位，已修正为 admin 专用。

    usage 字段是「本次进程启动后」的 Token/TTFT 聚合（ai/observability.py），
    单 worker 内存态，**进程重启即清零**，且不跨实例累加。
    它用于排障与调优的即时可见性，不是财务级账单；要长期核算需把 token
    落库（ai_usage_daily 加列）。usage 为 {} 表示本次启动后尚无调用。
    """
    stats = await ai_crud.ai_stats(db)   # 全量 COUNT 不过滤 deleted_at；AVG(rating) 空回 0
    return {
        "totalSessions": stats["totalSessions"],
        "totalMessages": stats["totalMessages"],
        "totalFeedback": stats["totalFeedback"],
        "averageRating": stats["averageRating"],
        "usage": ai_obs.recorder.snapshot(),
    }


# ── 自然语言记账 ────────────────────────────────────────────────────────

# 确认框（前端「金额确认卡」）的预览限流：dryRun=true 不写库、不计 daily_bookkeeping
# 配额，故必须另有成本闸门——预览仍会真实跑一次 LLM 解析。口径同 FAQ / 语音限流：
# 进程内滑动窗口，单 worker 语义。端点内必须直接引用模块全局，否则测试的
# monkeypatch 不生效。
bookkeeping_preview_rate_limiter = SlidingWindowRateLimiter(
    max_calls=BK_PREVIEW_RATE_LIMIT_PER_MIN, window=60
)

# 预览结果缓存：dryRun 预览已经真实跑过一次 LLM 解析，确认时按 previewId 读回同一份
# Parsed，**省掉第二次模型调用**——「确认」从「1 次 LLM + 若干 DB」降到「若干 DB」，
# 耗时由秒级降到毫秒级。
#
# 未命中一律回退重新解析（只影响速度、不影响正确性）：进程重启、多 worker、TTL 过期、
# 换用户/换消息、客户端未回传 previewId —— 这些情况都必须走回退分支。
# 与限流器同属进程内存态，端点内必须直接引用模块全局，否则测试 monkeypatch 不生效。
bookkeeping_preview_cache = TtlCache(
    ttl=BK_PREVIEW_CACHE_TTL_SECONDS, max_entries=BK_PREVIEW_CACHE_MAX_ENTRIES
)


def _cached_preview_parsed(preview_id: str | None, user_id: int, message: str):
    """按 previewId 取回预览时的解析结果；任一校验不过返回 None（调用方回退重新解析）。

    三重校验缺一不可：
    - ``user_id`` —— 防串号（A 的 previewId 被 B 拿来复用会读到 A 的解析结果）；
    - ``message``  —— 防「同一 previewId 换了另一条消息」，否则会把旧消息的解析结果
      套到新消息上，比慢更糟；
    - TTL（由缓存自身保证）—— 防陈旧结果被无限期复用。
    """
    if not preview_id:
        return None
    entry = bookkeeping_preview_cache.get(preview_id)
    if not entry:
        return None
    if entry.get("user_id") != user_id or entry.get("message") != message:
        return None
    parsed = entry.get("parsed")
    # 返回深拷贝：第 7 步会就地改写 item.type，直接交出缓存对象会让缓存被污染，
    # 同一 previewId 被复用第二次时读到已被改过的结果。
    return parsed.model_copy(deep=True) if parsed is not None else None


async def _duplicate_response(db: AsyncSession, hit, user_id: int) -> dict:
    """按命中的首次日志组包 duplicate 响应（预检查与 IntegrityError 兜底共用）

    传入 user_id 后 get_records_by_ids 会附加归属过滤，避免日志中 record_ids
    被拼入他人 ID 后回显（P2-4.5）。
    """
    dup_records = await ai_crud.get_records_by_ids(db, hit.record_ids or [], user_id=user_id)
    first = dup_records[0] if dup_records else None
    return BkDuplicateOut(
        request_id=ai_crud.new_id("bk"),
        origin_request_id=hit.request_id,
        records=[
            BkRecordItem(
                id=r.id,
                amount=float(r.amount),
                record_date=r.date.isoformat(),
                remark=r.remark,
            )
            for r in dup_records
        ],
        echo=(
            f"这条我已经记过啦（#{first.id} · ¥{float(first.amount):.2f}），没有重复记账。"
            if first else "这条我已经记过啦，没有重复记账。"
        ),
        hint="如果确实要再记一笔，请重新发送并带上 force=true。",
    ).model_dump(by_alias=True)


@router.post("/bookkeeping", summary="自然语言记账")
async def bookkeeping(
    body: BookkeepingIn,
    user_id: int = Depends(get_current_regular_user),
    db: AsyncSession = Depends(get_db),
):
    """6.15 自然语言记账：五种 action 形态 preview/created/clarify/ignored/duplicate + {"error"}

    解析链 BookkeepingChain 见 06 §11；幂等日志表 ai_bookkeeping_logs（models/bookkeeping.py 已有）。

    ── 「金额确认卡」两步契约（dryRun 预览 → overrides 确认）──
    前端在语音/文字输入后先发一次 ``dryRun=true`` 拿到 ``action="preview"``，把
    ``preview.items[]``（含 ``index / amount / amountRaw / categoryName / date /
    confidence``）渲染成可编辑的金额确认卡；用户改完金额后，再发一次
    ``dryRun=false`` 并携带 ``overrides=[{index, amount}]`` 落到对应条目上。

    四条必须遵守的约定：
    1. **``index`` 是覆盖键**：``overrides`` 按 ``preview.items[].index`` 定位，对应
       LLM 输出顺序（不是数组下标——缺金额的条目也在 items 里占一个 index）。改错
       index 会写到别的条目上。
    2. **两次请求必须复用同一个 ``clientMsgId``**：预览不写日志、不占幂等键，真正
       落库只发生在确认那次；确认连点两次会被 ``find_log_by_client_msg`` 拦成
       ``duplicate``，因此不会重复入账。若两次用了不同的 key，连点就会入账两笔。
    3. **配额只在确认那次扣一次**：``dryRun=true`` 不计 ``daily_bookkeeping``，
       改走 ``bookkeeping_preview_rate_limiter`` 防刷。
    4. **确认请求应回传 ``previewId``（= 预览响应的 ``requestId``）**：命中
       ``bookkeeping_preview_cache`` 时直接复用预览的解析结果，**跳过第二次 LLM 调用**
       （确认耗时由秒级降到毫秒级）。未命中（重启/多 worker/TTL 过期/换用户/换消息/
       未回传）一律回退到重新解析，因此**只是变慢、不会算错**，客户端可以不传。
    """


    message = (body.message or "").strip()
    if not message:
        return ai_error("缺少参数: message")
    if len(message) > 500:
        return ai_error("消息过长，最多 500 字")

    # 会话归属校验（sessionId 可空：不传则不落会话消息）
    if body.session_id:
        session = await ai_crud.get_user_session(db, body.session_id, user_id)
        if session is None:
            return ai_error("会话不存在")

    # ── 追问续写：draftId 命中时，将草稿 raw_text 拼接到本次消息前面重新解析 ──
    # 历史版本该参数收而不使用，导致「缺金额 → 追问 → 回复金额 → 人账」链路断裂（P1-4）。
    draft_log = None
    if body.draft_id is not None:
        draft_log = await ai_crud.get_bookkeeping_log(db, body.draft_id)
        if (
            draft_log is None
            or draft_log.user_id != user_id
            or draft_log.status != 0
            or draft_log.action != "clarify"
        ):
            return ai_error("草稿不存在或已过期")
        # 拼接为一条完整描述（限 500 字，与 BookkeepingIn.message 上限一致）
        combined = f"{draft_log.raw_text} {message}".strip()[:500]
        message = combined

    import hashlib

    # ── 第 3 步：幂等检查（force=true 跳过弱幂等窗口，强幂等仍生效）──
    normalized = " ".join(message.split())
    dedup_hash = hashlib.sha256(f"{user_id}|{normalized}".encode()).hexdigest()
    hit = None
    if body.client_msg_id:
        hit = await ai_crud.find_log_by_client_msg(db, user_id, body.client_msg_id)
    if hit is None and not body.force:
        hit = await ai_crud.find_recent_by_dedup(db, user_id, dedup_hash, 300)

    if hit is not None and hit.record_ids:
        return await _duplicate_response(db, hit, user_id)

    # ── 第 3.5 步：成本闸门（dryRun 预览 / 真正落库 两种口径，勿混用）──
    # 幂等/duplicate 短路的请求在上面已 return，走不到这里，不计费。
    #
    # 配额只在**真正落库**的那一次计：dryRun=true 只解析不入账，若它也扣一次
    # daily_bookkeeping，则「预览 → 确认」确认框流程会让一次记账扣掉 2 次额度
    # （免费档 daily_bookkeeping=5 → 实际只剩 2.5 次），属额度口径回归。
    # 但预览仍要真实调用一次 LLM 解析，不是免费操作，因此改用独立滑动窗口限流防刷。
    #
    # 这两条都必须在日志占位 INSERT 之前判定：占位 commit 后才发现超额，会留下
    # action='created' 的假成功脏日志。
    # bookkeeping 前端只消费裸 {"error"}，故用 HTTP 200 + error 文案（与 chat 的 429 二选一，勿混用）
    if body.dry_run:
        ok, retry_after = bookkeeping_preview_rate_limiter.allow(f"bk-preview:{user_id}")
        if not ok:
            return ai_error(
                f"预览太频繁，请 {retry_after} 秒后再试", code="RATE_LIMIT"
            )
    else:
        quota_error = await _quota_gate(db, user_id, "bookkeeping")
        if quota_error:
            return ai_error(quota_error["error"], code=quota_error["code"])

    # ── 第 4 步：先 INSERT 日志占位（唯一键 uk_abk_client_msg 兜底并发）──
    # dry_run 不写日志、不参与去重
    log = None
    request_id = ai_crud.new_id("bk")
    if not body.dry_run:
        try:
            log = await ai_crud.create_bookkeeping_log(
                db,
                request_id=request_id,
                user_id=user_id,
                session_id=body.session_id,
                client_msg_id=body.client_msg_id,
                dedup_hash=dedup_hash,
                raw_text=message,
                source=body.source if body.source in ("text", "voice") else "text",
                intent="bookkeeping",   # 占位，第 6/9 步按解析结果回写
                action="created",       # 占位，第 9 步回写为准
                status=1,
                parent_id=draft_log.id if draft_log else None,
            )
            # 新日志已建立，同事务将旧草稿标记为已消费（status=2），避免下一次重复续写
            if draft_log is not None:
                await ai_crud.update_bookkeeping_log(db, draft_log.id, status=2)
            await db.commit()           # 占位必须先落库，撞键才有意义
        except IntegrityError:
            # 撞 uk_abk_client_msg。分两种情况，必须区分，否则用户会被永久卡死：
            #  a) 首次请求真的还在处理中/已完成 -> 回显 duplicate
            #  b) 首次请求已经死了（进程被 kill、OOM、断电），日志占着键但没产出
            #     record —— find_log_by_client_msg 刻意只认 status=1 且 record_ids
            #     非空，所以查不到。此时必须释放该键并让用户重试，
            #     否则同一 clientMsgId 永远返回「请求处理中」。
            first = await ai_crud.find_log_by_client_msg(db, user_id, body.client_msg_id)
            if first and first.record_ids:
                return await _duplicate_response(db, first, user_id)
            dead = await ai_crud.find_any_by_client_msg(db, user_id, body.client_msg_id)
            if dead is not None and not dead.record_ids:
                # 死日志：无 record 说明从未成功入账，释放幂等键
                await ai_crud.release_client_msg_id(db, dead.id)
                await db.commit()
                logger.warning(
                    "released stale idempotency key: log_id=%s user_id=%s action=%s",
                    dead.id, user_id, dead.action,
                )
                return ai_error("上一次请求未完成，请重新发送")
            return ai_error("请求处理中，请稍后重试")

    async def _bk_fail(msg: str, *, stage: str = "unknown",
                       code: str | None = None) -> dict:
        """解析/校验失败善后：占位日志回写 error（status=0），被消费的草稿恢复为 0，
        避免留下 action='created' 的脏日志或断掉追问续写链。配额不回退（防刷惯例）。

        error_msg 记录「阶段:中文原因」，用于事后分析失败率与失败类型分布——
        此前该列全项目零写入，所有失败只回前端一句文案，运营侧完全黑盒。
        落库前用 security.mask_for_log 压长度，防止上游报错把内部路径/连接串带进库。

        code 为附加的机器可读标记（如 UPSTREAM_BUSY），旧前端只读 error 不受影响。
        """
        detail = f"{stage}: {msg}"[:200]
        try:
            if log is not None:
                await ai_crud.update_bookkeeping_log(
                    db, log.id, action="error", status=0, error_msg=detail,
                    # ⚠️ 必须释放幂等键：本条没产出 record，却占着 uk_abk_client_msg。
                    # 两个去重查询都要求 status=1 且 record_ids 非空，查不到它；
                    # 用户若用**同一个 clientMsgId** 重试（这正是客户端幂等键的用途
                    # ——弱网重发），会直接撞唯一键，走到 IntegrityError 分支后
                    # 又查不到成功日志，于是永远返回「请求处理中」，再也记不进去。
                    client_msg_id=None,
                )
            if draft_log is not None:
                await ai_crud.update_bookkeeping_log(db, draft_log.id, status=0)
            if log is not None or draft_log is not None:
                await db.commit()
        except Exception:
            await db.rollback()
            logger.exception("bookkeeping fail-log cleanup error, user_id=%s", user_id)
        return ai_error(msg, code=code)

    # ── 第 5 步：LLM 解析（确认时若命中预览缓存则跳过，省掉第二次模型调用）──
    from datetime import date as _date
    from models.category import Category

    today = _date.today()
    # 预览请求自己就是缓存产出方，不走缓存；只有确认请求才尝试复用。
    # 命中后「确认」路径不再调用 LLM，耗时由秒级降到毫秒级。
    cached_parsed = None if body.dry_run else _cached_preview_parsed(
        body.preview_id, user_id, message
    )
    try:
        cat_rows = (await db.execute(
            select(Category).where(
                Category.status == 1,   # 禁用分类不可被 AI 选中入账（与创建账单口径一致）
                or_(Category.user_id == user_id, Category.user_id.is_(None))
            )
        )).scalars().all()
        # 用户自定义分类放前面，resolve_category 的精确匹配优先命中自定义
        user_cats = [c for c in cat_rows if c.user_id == user_id]
        sys_cats = [c for c in cat_rows if c.user_id != user_id]
        if cached_parsed is not None:
            # 命中预览缓存：直接复用解析结果。分类仍走上面的实时分类表，
            # 因此用户在预览与确认之间新增/禁用的分类同样生效。
            parsed = cached_parsed
        else:
            parsed = await parse_bookkeeping(
                _safe_user_text(message), today.isoformat(), [c.name for c in cat_rows], user_id=user_id
            )
    except Exception as e:
        logger.exception("bookkeeping parse failed, user_id=%s", user_id)
        # 上游过载 ≠ 用户说法有问题：过载时让用户「换个说法」纯属误导（改了也一样失败），
        # 且会在审计日志里把上游故障记成用户的解析失败（P1-6）。
        if ai_retry.is_upstream_busy(e):
            return await _bk_fail("AI 助手当前繁忙，请稍后重试",
                                  stage="upstream_busy", code="UPSTREAM_BUSY")
        return await _bk_fail("记账解析失败，请换个说法再试", stage="parse")

    # 审计载荷：parse_json 全项目只写不读，用保留键追加 overrides 记录是安全的
    parse_payload = parsed.model_dump()
    if body.overrides:
        parse_payload["_applied_overrides"] = [
            o.model_dump(by_alias=True) for o in body.overrides
        ]

    # ── 第 6 步：意图过滤 -> ignored ──
    if parsed.intent in ("query", "chitchat") or (
        parsed.intent == "bookkeeping"
        and not any(i.is_expense_related for i in parsed.items)
    ):
        if log is not None:
            await ai_crud.update_bookkeeping_log(
                db, log.id, action="ignored",
                intent=parsed.intent, parse_json=parse_payload,
            )
            await db.commit()
        return BkIgnoredOut(
            request_id=request_id,
            reason="not_expense",
            echo="这不像一笔消费记录，我没有记账。想记账可以说「今天打车花了18块」。",
        ).model_dump(by_alias=True)

    # ── 第 7 步：条目数校验 + 逐条归一化（保留 parsed.items 原始下标）──
    # 原实现用 continue 跳过缺金额条目时把下标丢了，确认卡（overrides）无法定位
    # 第 N 笔，因此 ok_items 从 4 元组扩为 (idx, item, amount, rec_date, cat) 5 元组。
    if len(parsed.items) > 10:
        return await _bk_fail("一次最多识别 10 笔消费，请分开发送", stage="too_many_items")

    ov_map = {o.index: o for o in (body.overrides or [])}
    ok_items: list[tuple] = []
    skipped_idx: list[int] = []
    warnings: list[str] = []
    fallback_count = 0     # 归入「其他」的条目数
    low_conf_count = 0     # 低于 BK_LOW_CONFIDENCE 的条目数

    for idx, item in enumerate(parsed.items):
        ov = ov_map.get(idx)
        override_type = ov is not None and ov.type is not None

        # 金额：override 优先，走同一套范围校验（超限会被归 None，进 clarify 不猜测）
        amount = bk_norm.normalize_amount(item.amount_raw, item.amount)
        if ov is not None and ov.amount is not None:
            amount = bk_norm.normalize_amount(None, ov.amount)
        if amount is None:
            skipped_idx.append(idx)
            continue

        # 日期
        if ov is not None and ov.date:
            try:
                rec_date = _date.fromisoformat(ov.date)
            except ValueError:
                return await _bk_fail("日期格式应为 yyyy-MM-dd", stage="bad_date")
        else:
            rec_date = bk_norm.normalize_date(item.date_expr, item.date, today)

        # 收支类型：用户显式 override 优先；LLM 漏传时不再默认「收入」，改由分类推导
        if override_type:
            item.type = ov.type

        # 分类：override 指定时做归属 + 类型一致性校验（对齐 amend 的口径）
        if ov is not None and ov.category_id is not None:
            cat = next((c for c in cat_rows if c.id == ov.category_id), None)
            if cat is None:
                return await _bk_fail("分类不存在或不可用", stage="bad_category_override")
            if override_type and cat.type != item.type:
                return await _bk_fail("分类类型与收支类型不一致", stage="category_type_mismatch")
            fallback = False
        else:
            cat, fallback = bk_alias.resolve_category(item.category_name, user_cats + sys_cats)

        if ov is not None and ov.remark is not None:
            item.remark = ov.remark[:200] or None

        if fallback:
            cat = next((c for c in cat_rows if c.name == "其他"), None)
            if cat is None:
                # 归类失败且系统没有「其他」分类：中止本单。
                # 继续走会在 NOT NULL 列 records.category_id 插 NULL 触发 IntegrityError（P0）
                return await _bk_fail("未识别到明确分类，且系统缺少「其他」分类，请先创建后重试", stage="no_fallback_category")
            fallback_count += 1

        # 无显式 override 类型时，以最终入账分类为准（分类是强数据约束，
        # 比 LLM 的收支猜测可信；两者都缺信息才回落支出）
        if not override_type:
            item.type = cat.type if cat is not None else 0

        # confidence 此前只被解析/落库/返回，从不参与任何决策。这里做两件事：
        # 统计低置信条目，供 warnings 汇总提示用户核对。
        # 注意两点：
        # 1) 不因低置信阻断入账——用户已经明确发了记账语句，阻断会变成
        #    "说了不记"，比"记错了可改"更糟；
        # 2) confidence == 0 视为「模型没给」而非「零置信」：schema 默认值就是 0.0，
        #    若照单全收，任何不返回该字段的模型都会让每笔记账都挂一条假警告。
        if 0 < item.confidence < BK_LOW_CONFIDENCE:
            low_conf_count += 1

        ok_items.append((idx, item, amount, rec_date, cat))

    # warnings 汇总：原先每条 fallback 都 append 一句完全相同的话，
    # 一单 10 笔全落「其他」就是 10 条重复文案。改为按类别聚合成一条。
    if fallback_count:
        warnings.append(
            f"{fallback_count} 笔未识别到明确分类，已归入「其他」"
            if fallback_count > 1 else "未识别到明确分类，已归入「其他」"
        )
    if low_conf_count:
        warnings.append(
            f"{low_conf_count} 笔识别把握不大，请核对金额与分类"
            if low_conf_count > 1 else "识别把握不大，请核对金额与分类"
        )

    # ── 第 8 步：dry_run / clarify / created 三分支 ──
    def _preview_items():
        rows = [
            (idx, BkPreviewItem(
                index=idx,
                amount=amt,
                amount_raw=it.amount_raw,
                type=it.type,
                category_name=cat.name if cat else None,
                category_id=cat.id if cat else None,
                date=rd.isoformat(),
                date_expr=it.date_expr,
                remark=it.remark,
                confidence=it.confidence,
            ).model_dump(by_alias=True))
            for idx, it, amt, rd, cat in ok_items
        ] + [
            (idx, BkPreviewItem(
                index=idx,
                amount=None,
                amount_raw=it.amount_raw,
                type=it.type,
                category_name=it.category_name,
                date_expr=it.date_expr,
                remark=it.remark,
                confidence=it.confidence,
            ).model_dump(by_alias=True))
            for idx in skipped_idx
            for it in [parsed.items[idx]]
        ]
        rows.sort(key=lambda x: x[0])   # 卡片顺序与 LLM 输出顺序一致
        return [r for _, r in rows]

    if body.dry_run:
        # 把解析结果连同「属于谁 / 解析的是哪条消息」暂存，确认时按 requestId 读回，
        # 省掉第二次 LLM 调用。deep copy 是必须的：第 7 步会就地改写 item.type，
        # 不复制会让缓存与本次返回值共享同一批可变对象。
        bookkeeping_preview_cache.set(request_id, {
            "user_id": user_id,
            "message": message,
            "parsed": parsed.model_copy(deep=True),
        })
        return {"action": "preview", "requestId": request_id,
                "preview": {"items": _preview_items()},
                "warnings": warnings, "records": []}

    if not ok_items:    # 全部缺金额 -> clarify + 草稿（status=0）
        if log is not None:
            await ai_crud.update_bookkeeping_log(
                db, log.id, action="clarify", status=0,
                intent=parsed.intent, parse_json=parse_payload,
            )
            await db.commit()
        return BkClarifyOut(
            request_id=request_id,
            draft_id=log.id if log is not None else None,
            question="这笔消费的金额是多少？比如「35元」。",
            missing=["amount"],
            preview={"items": _preview_items()},
        ).model_dump(by_alias=True)

    # 正常入账：同一事务逐条 INSERT records + 回写日志（第 9 步）
    records = []
    for idx, item, amount, rec_date, cat in ok_items:
        rec = Record(
            user_id=user_id,
            category_id=cat.id if cat else None,
            type=item.type,
            amount=amount,
            date=rec_date,
            remark=(item.remark or "")[:200] or None,
            status=1,
        )
        db.add(rec)
        records.append(rec)
    await db.flush()
    record_ids = [r.id for r in records]

    echo = "已记下：" + "；".join(
        f"{(cat.name if cat else '其他')} ¥{amount:.2f} · {rec_date.isoformat()}"
        + (f" · 备注「{item.remark}」" if item.remark else "")
        + f" · 记录 #{rid}"
        for (idx, item, amount, rec_date, cat), rid in zip(ok_items, record_ids)
    ) + "\n回复「改成45块」可修改，回复「删掉」可撤销。"

    if log is not None:
        await ai_crud.update_bookkeeping_log(
            db, log.id, record_ids=record_ids,
            parse_json=parse_payload, action="created",
            intent=parsed.intent, status=1,
        )
    # P2-14：审计链补全——ai_bookkeeping_logs.message_id 列（FK 指向 messages.id）
    # 此前从未赋值，日志↔消息无法追溯，已建 FK 形同虚设。created 路径把助手
    # 消息 ID 回写到日志，并在出参 BkCreatedOut.messageId 透出。
    ai_msg = None
    if body.session_id:
        await ai_crud.add_message(db, body.session_id, "user", message)
        ai_msg = await ai_crud.add_message(db, body.session_id, "assistant", echo)
        if log is not None:
            await ai_crud.update_bookkeeping_log(db, log.id, message_id=ai_msg.id)
    await db.commit()

    return BkCreatedOut(
        request_id=request_id,
        records=[
            BkRecordItem(
                id=rid,
                amount=amt,
                type=it.type,
                category_id=cat.id if cat else None,
                category_name=cat.name if cat else "其他",
                record_date=rd.isoformat(),
                remark=it.remark,
            )
            for (idx, it, amt, rd, cat), rid in zip(ok_items, record_ids)
        ],
        total_amount=round(sum(amt for _, _, amt, _, _ in ok_items), 2),
        echo=echo,
        warnings=warnings,
        session_id=body.session_id,
        message_id=ai_msg.id if ai_msg else None,
    ).model_dump(by_alias=True)


@router.patch("/bookkeeping/{record_id}", summary="修改 AI 记账记录")
async def amend_bookkeeping(
    record_id: int,
    body: BookkeepingAmendIn,
    user_id: int = Depends(get_current_regular_user),
    db: AsyncSession = Depends(get_db),
):
    """6.16 修改 AI 记账：返回 {success, record, changes, echo}；changes 只列实际变动字段"""
    import hashlib
    from datetime import date as _date
    from models.category import Category

    rec = (await db.execute(
        select(Record).where(
            Record.id == record_id,
            Record.user_id == user_id,
            Record.status == 1,
        )
    )).scalars().first()
    if rec is None:
        return ai_error("记录不存在")

    # ── 1) 显式字段优先收集 ──
    # 金额统一 Decimal：float 直接赋给 Numeric 列会写入二进制精度垃圾（0.1 → 0.1000000000000000055511）
    new_amount = bk_norm.to_decimal(body.amount) if body.amount is not None else None
    new_category_id = body.category_id
    new_date = None
    if body.date:
        try:
            new_date = _date.fromisoformat(body.date)
        except ValueError:
            return ai_error("日期格式应为 yyyy-MM-dd")
    new_remark = body.remark

    # ── 2) message 解析链取增量字段（显式字段优先覆盖）──
    # P0-2：此路径调 LLM（parse_bookkeeping），此前**不走配额、不走并发闸门**，
    # 认证用户可无限刷修改请求烧 token，护栏口径与对话/记账不一致。补齐：
    #   取 plan → try_acquire 并发槽 → _quota_gate 扣 bookkeeping 配额。
    # 超额按 bookkeeping 既有口径返回 HTTP 200 裸 error（与 POST /bookkeeping 一致，
    # 不用 429）；配额失败不回滚（防刷量优先，既定取舍）。
    if body.message:
        msg = body.message.strip()
        if len(msg) > 500:
            return ai_error("消息过长，最多 500 字")
        plan = MEMBERSHIP_PLANS[await membership_crud.get_tier(db, user_id)]
        release = await ai_concurrency.try_acquire(user_id, plan["concurrency"])
        if release is None:
            return JSONResponse(status_code=429, content={
                "error": "您的 AI 并发已达上限，请等待当前请求完成",
                "code": "CONCURRENCY_LIMIT",
            })
        try:
            quota_error = await _quota_gate(db, user_id, "bookkeeping", plan=plan)
            if quota_error:
                return ai_error(quota_error["error"], code=quota_error["code"])

            cat_rows = (await db.execute(
                select(Category).where(
                    Category.status == 1,   # 禁用分类不可被 AI 选中入账
                    or_(Category.user_id == user_id, Category.user_id.is_(None))
                )
            )).scalars().all()
            user_cats = [c for c in cat_rows if c.user_id == user_id]
            sys_cats = [c for c in cat_rows if c.user_id != user_id]
            try:
                parsed = await parse_bookkeeping(
                    _safe_user_text(msg), _date.today().isoformat(), [c.name for c in cat_rows], user_id=user_id
                )
            except Exception:
                logger.exception("amend parse failed, user_id=%s record_id=%s", user_id, record_id)
                return ai_error("修改解析失败，请换个说法再试")
            item = next(
                (i for i in parsed.items
                 if i.is_expense_related and (i.amount_raw or i.amount is not None)),
                None,
            )
            if item is not None:
                if new_amount is None:
                    amt = bk_norm.normalize_amount(item.amount_raw, item.amount)
                    if amt is not None:
                        new_amount = amt
                if new_category_id is None and item.category_name:
                    cat, _ = bk_alias.resolve_category(
                        item.category_name, user_cats + sys_cats
                    )
                    if cat is not None:
                        new_category_id = cat.id
                if new_date is None and (item.date or item.date_expr):
                    new_date = bk_norm.normalize_date(
                        item.date_expr, item.date, _date.today()
                    )
                if new_remark is None and item.remark:
                    new_remark = item.remark
        finally:
            release()

    if all(v is None for v in (new_amount, new_category_id, new_date, new_remark)):
        return ai_error("缺少修改内容")

    # ── 3) 校验并构造变更集 ──
    changes: dict[str, dict] = {}
    if new_amount is not None:
        if new_amount <= 0 or new_amount > bk_norm.MAX_AMOUNT:
            return ai_error("金额需大于 0 且不超过 99999999.99")
        new_amount = bk_norm.quantize_amount(new_amount)
        if rec.amount != new_amount:
            changes["amount"] = {"from": float(rec.amount), "to": float(new_amount)}
            rec.amount = new_amount
    if new_category_id is not None:
        cat = (await db.execute(
            select(Category).where(
                Category.id == new_category_id,
                Category.status == 1,
                or_(Category.user_id == user_id, Category.user_id.is_(None)),
            )
        )).scalars().first()
        if cat is None:
            return ai_error("分类不存在或不可用")
        if cat.type != rec.type:
            return ai_error("分类类型与原记录收支类型不一致")
        if cat.id != rec.category_id:
            old_cat = (await db.execute(
                select(Category).where(Category.id == rec.category_id)
            )).scalars().first()
            changes["categoryId"] = {
                "from": rec.category_id,
                "to": cat.id,
            }
            changes.setdefault("_names", {})["categoryId"] = {
                "from": old_cat.name if old_cat else str(rec.category_id),
                "to": cat.name,
            }
            rec.category_id = cat.id
    if new_date is not None and new_date != rec.date:
        changes["recordDate"] = {"from": rec.date.isoformat(), "to": new_date.isoformat()}
        rec.date = new_date
    if new_remark is not None:
        new_remark = new_remark[:200] or None
        if (new_remark or "") != (rec.remark or ""):
            changes["remark"] = {"from": rec.remark, "to": new_remark}
            rec.remark = new_remark

    if not changes:
        # 内容与原记录一致：视为无变动，仍返回成功
        record_out = {
            "id": rec.id,
            "amount": float(rec.amount),
            "type": rec.type,
            "categoryId": rec.category_id,
            "recordDate": rec.date.isoformat(),
            "remark": rec.remark,
        }
        return {"success": True, "record": record_out, "changes": {}, "echo": "记录没有需要修改的内容"}

    # ── 4) 追加日志 action='amend'，parent_id 指向原记账日志 ──
    parent = (await db.execute(
        select(AiBookkeepingLog).where(
            AiBookkeepingLog.user_id == user_id,
            AiBookkeepingLog.action == "created",
            AiBookkeepingLog.status == 1,
        ).order_by(AiBookkeepingLog.id.desc()).limit(50)
    )).scalars().all()
    parent_log = next(
        (lg for lg in parent
         if isinstance(lg.record_ids, list) and record_id in lg.record_ids),
        None,
    )
    amend_text = (body.message or "").strip() or f"修改记录 #{record_id}"
    await ai_crud.create_bookkeeping_log(
        db,
        request_id=ai_crud.new_id("bk"),
        user_id=user_id,
        session_id=parent_log.session_id if parent_log else None,
        client_msg_id=None,
        dedup_hash=hashlib.sha256(
            f"{user_id}|amend|{record_id}|{json.dumps(changes, ensure_ascii=False, sort_keys=True, default=str)}".encode()
        ).hexdigest(),
        raw_text=amend_text[:500],
        intent="amend",
        action="amend",
        parse_json={"changes": {k: v for k, v in changes.items() if not k.startswith("_")}},
        record_ids=[record_id],
        status=1,
        parent_id=parent_log.id if parent_log else None,
    )
    await db.commit()

    # ── 5) echo + 出参 ──
    names = changes.pop("_names", {}).get("categoryId", {})
    rec_cat = (await db.execute(
        select(Category).where(Category.id == rec.category_id)
    )).scalars().first()
    parts = []
    for field, ch in changes.items():
        if field == "categoryId":
            parts.append(f"分类 {names.get('from')} → {names.get('to')}")
        elif field == "amount":
            parts.append(f"金额 ¥{ch['from']:.2f} → ¥{ch['to']:.2f}")
        elif field == "recordDate":
            parts.append(f"日期 {ch['from']} → {ch['to']}")
        else:
            parts.append(f"备注 {ch['from'] or '空'} → {ch['to'] or '空'}")
    echo = f"已修改 #{rec.id}（{rec_cat.name if rec_cat else '其他'} ¥{float(rec.amount):.2f} · {rec.date.isoformat()}）：{'；'.join(parts)}"

    record_out = {
        "id": rec.id,
        "amount": float(rec.amount),
        "type": rec.type,
        "categoryId": rec.category_id,
        "recordDate": rec.date.isoformat(),
        "remark": rec.remark,
    }
    return {"success": True, "record": record_out, "changes": changes, "echo": echo}


@router.delete("/bookkeeping/{record_id}", summary="删除 AI 记账记录")
async def delete_bookkeeping(
    record_id: int,
    user_id: int = Depends(get_current_regular_user),
    db: AsyncSession = Depends(get_db),
):
    """6.17 删除 AI 记账（软删 status=0）：返回 {success, echo}"""
    from models.category import Category

    rec = (await db.execute(
        select(Record).where(
            Record.id == record_id,
            Record.user_id == user_id,
            Record.status == 1,
        )
    )).scalars().first()
    if rec is None:
        return ai_error("记录不存在")

    cat = (await db.execute(
        select(Category).where(Category.id == rec.category_id)
    )).scalars().first()

    # ── 软删记录（与账单模块口径一致）──
    rec.status = 0

    # ── 找到原记账日志：回滚标记 + 追加 delete 日志 ──
    parent_log = None
    parent = (await db.execute(
        select(AiBookkeepingLog).where(
            AiBookkeepingLog.user_id == user_id,
            AiBookkeepingLog.action == "created",
            AiBookkeepingLog.status == 1,
        ).order_by(AiBookkeepingLog.id.desc()).limit(50)
    )).scalars().all()
    for lg in parent:
        if isinstance(lg.record_ids, list) and record_id in lg.record_ids:
            parent_log = lg
            break

    if parent_log is not None:
        parent_log.status = 2    # 已回滚
    await ai_crud.create_bookkeeping_log(
        db,
        request_id=ai_crud.new_id("bk"),
        user_id=user_id,
        session_id=parent_log.session_id if parent_log else None,
        client_msg_id=None,
        dedup_hash=hashlib.sha256(f"{user_id}|delete|{record_id}".encode()).hexdigest(),
        raw_text=f"删除记录 #{record_id}"[:500],
        intent="delete",
        action="delete",
        record_ids=[record_id],
        status=1,
        parent_id=parent_log.id if parent_log else None,
    )
    await db.commit()

    echo = (
        f"已删除 #{rec.id}（{cat.name if cat else '其他'} ¥{float(rec.amount):.2f}"
        f" · {rec.date.isoformat()}）"
    )
    return {"success": True, "echo": echo}
