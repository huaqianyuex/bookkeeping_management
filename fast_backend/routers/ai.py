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
"""
import hashlib
import json
import logging
from typing import Any

from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage, SystemMessage
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ai import memory, chat_chain, analyze_chain, faq_retriever
from ai import context as ai_context
from ai import normalizers as bk_norm
from ai import category_alias as bk_alias
from ai.bookkeeping_chain import parse_bookkeeping
from config.db_config import get_db
from crud import ai as ai_crud
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
from utils.auth import get_current_user, get_current_admin

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ai", tags=["ai"])


def ai_error(msg: str) -> dict:
    """AI 业务失败统一返回：HTTP 200 + 裸 {"error": "中文"}"""
    return {"error": msg}

# ── 会话 ────────────────────────────────────────────────────────────────

@router.post("/sessions", summary="创建会话")
async def create_session(
    body: SessionCreateIn,
    user: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    title = (body.title or "").strip() or "新对话"[:50]
    session = await ai_crud.create_session(db, user, title)
    return SessionOut.model_validate(session).model_dump(by_alias=True)


@router.get("/sessions", summary="会话列表")
async def list_sessions(
    user_id: int = Depends(get_current_user),
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
    user_id: int = Depends(get_current_user),
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
    user_id: int = Depends(get_current_user),
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
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):

    """6.4 软删单个会话（deleted_at=毫秒）：返回 {success: bool}"""
    ok = await ai_crud.soft_delete_session(db, session_id, user_id)
    return {"success": ok}


@router.get("/sessions/{session_id}/messages", summary="会话消息")
async def session_messages(
    session_id: str,
    user_id: int = Depends(get_current_user),
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

@router.post("/chat", summary="非流式对话")
async def chat(
    body: ChatIn,
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not (body.session_id or "").strip() or not (body.message or "").strip():
        raise HTTPException(400, "sessionId 和 message 不能为空")

    # 会话归属校验：非本人/已删 → 裸 error（HTTP 200）
    session = await ai_crud.get_user_session(db, body.session_id, user_id)
    if session is None:
        return ai_error("会话不存在")

    # 组装消息：system + 财务数据块 + 历史窗口 + 本次 human
    history = await memory.build_history(db, body.session_id)
    finance_block = await ai_context.build_finance_block(db, user_id)
    messages = [SystemMessage(content=chat_chain.SYSTEM_PROMPT + finance_block), *history, HumanMessage(content=body.message)]

    # 落库用户消息
    await ai_crud.add_message(db, body.session_id, "user", body.message)

    # 调 LLM（非流式，一次拿全）
    try:
        content = await chat_chain.chat(messages)
    except Exception:
        return ai_error("AI 服务暂不可用，请稍后重试")

    # 落库助手消息
    ai_msg = await ai_crud.add_message(db, body.session_id, "assistant", content)

    return {"content": content, "messageId": ai_msg.id}


@router.post("/chat/stream", summary="流式对话（SSE）")
async def chat_stream(
    body: ChatIn,
    user_id: int = Depends(get_current_user),
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

    async def event_gen():
        # 1) 落库用户消息
        try:
            await ai_crud.add_message(db, body.session_id, "user", body.message)
        except Exception:
            yield sse({"type": "error", "error": "消息保存失败"})
            return

        # 2) 组装消息并流式产出（注入实时财务数据，模型才能分析当月账单）
        history = await memory.build_history(db, body.session_id)
        finance_block = await ai_context.build_finance_block(db, user_id)
        messages = [SystemMessage(content=chat_chain.SYSTEM_PROMPT + finance_block), *history, HumanMessage(content=body.message)]

        full = []
        try:
            async for chunk in chat_chain.chat_stream(messages):
                full.append(chunk)
                yield sse({"type": "content", "content": chunk})
        except Exception:
            yield sse({"type": "error", "error": "AI 服务暂不可用，请稍后重试"})
            return

        # 3) 全部产出后，落库助手完整回复，再发 done
        try:
            ai_msg = await ai_crud.add_message(db, body.session_id, "assistant", "".join(full))
        except Exception:
            ai_msg = None
        yield sse({"type": "done", "messageId": ai_msg.id if ai_msg else None})

    return StreamingResponse(event_gen(), media_type="text/event-stream")


# ── 分析 / 预算 ────────────────────────────────────────────────────────

@router.post("/analyze/expenses", summary="消费分析")
async def analyze_expenses(
    body: ExpenseAnalyzeIn,
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """6.9 消费分析：返回 {success: true, data: ExpenseAnalysis}

    财务数据由服务端查库组包（ai/context.py），前端不传金额；data 内字段是 snake_case。
    """
    try:
        ctx = await ai_context.build_user_context(db, user_id)
        data = await analyze_chain.analyze_expense(ctx)
        return {"success": True, "data": data.model_dump()}
    except Exception:
        # 不用回显原始异常：DB/LLM 报错可能含 SQL 语句、内部路径、API key 提示
        logger.exception("analyze expenses failed, user_id=%s", user_id)
        return ai_error("分析失败，请稍后重试")


@router.post("/analyze/budget", summary="预算规划")
async def analyze_budget(
    body: BudgetPlanIn,
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """6.10 预算规划：返回 {success: true, data: BudgetPlan}"""
    try:
        ctx = await ai_context.build_user_context(db, user_id)
        data = await analyze_chain.plan_budget(body.monthly_income, body.savings_goal, ctx)
        return {"success": True, "data": data.model_dump()}
    except Exception:
        logger.exception("budget plan failed, user_id=%s income=%s goal=%s",
                         user_id, body.monthly_income, body.savings_goal)
        return ai_error("预算规划失败")


# ── FAQ ────────────────────────────────────────────────────────────────

@router.get("/faq/search", summary="FAQ 语义检索")
async def faq_search(
    query: str,
    user: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """6.11 FAQ 检索：正常 {"results":[...]}；检索抛异常 {"results":[], "fallback": true}

    两种失败形态要区分：无命中**没有** fallback 键；异常才有。
    """
    # TODO:
    # try:
    #     results = await ai_faq_retriever.search_faq(query, top_k=3)  # score 降序
    #     return {"results": results}
    # except Exception:
    #     return {"results": [], "fallback": True}

    try:
         results=await faq_retriever.search_faq(query,top_k=3)
         return {"results":results}
    except Exception:
        return {"results": [],"fallback":True}


@router.post("/faq/rebuild", summary="重建 FAQ 向量索引")
async def faq_rebuild(
    user_id: int = Depends(get_current_admin),   # 仅管理员可触发：embedding 成本/频率防护
    db: AsyncSession = Depends(get_db),
):
    """6.12 重建 FAQ 索引：成功 {success: true, count: n}；失败 {error: "重建失败"}

    重建会调全量 embedding，需仅管理员调用；异常详情只记日志，不透出原始报错。
    """
    try:
        rows = await ai_crud.list_faq(db)
        count = await faq_retriever.rebuild(rows)   # 清空->重载->算向量->存内存
        return {"success": True, "count": count}
    except Exception:
        logger.exception("FAQ rebuild failed, user_id=%s", user_id)
        return {"error": "重建失败"}


# ── 反馈 / 统计 ────────────────────────────────────────────────────────

@router.post("/feedback", summary="保存反馈")
async def submit_feedback(
    body: FeedbackIn,
    user_id: int = Depends(get_current_user),
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
        return ai_error("保存失败")


@router.get("/admin/stats", summary="AI 会话统计")
async def ai_admin_stats(
    user_id: int = Depends(get_current_admin),   # 6.14：仅管理员可见（路径带 admin 前缀，权限应一致）
    db: AsyncSession = Depends(get_db),
):
    """6.14 AI 使用统计（仅管理员）：{totalSessions, totalMessages, totalFeedback, averageRating}

    返回的是全站总体统计（带跨用户聚合数据），不适用普通用户。
    历史版本挂 get_current_user 且存在签名错位，已修正为 admin 专用。
    """
    stats = await ai_crud.ai_stats(db)   # 全量 COUNT 不过滤 deleted_at；AVG(rating) 空回 0
    return {
        "totalSessions": stats["totalSessions"],
        "totalMessages": stats["totalMessages"],
        "totalFeedback": stats["totalFeedback"],
        "averageRating": stats["averageRating"],
    }


# ── 自然语言记账 ────────────────────────────────────────────────────────

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
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """6.15 自然语言记账：四种 action 形态 created/clarify/ignored/duplicate + {"error"}

    解析链 BookkeepingChain 见 06 §11；幂等日志表 ai_bookkeeping_logs（models/bookkeeping.py 已有）。
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
                intent="bookkeeping",   # 占位，第 6/9 步按解析结果回写
                action="created",       # 占位，第 9 步回写为准
                status=1,
                parent_id=draft_log.id if draft_log else None,
            )
            await db.commit()           # 占位必须先落库，撞键才有意义
            # 新日志已建立，将旧草稿标记为已消费（status=2），避免下一次重复续写
            if draft_log is not None:
                await ai_crud.update_bookkeeping_log(db, draft_log.id, status=2)
                await db.commit()
        except IntegrityError:
            # 并发重发同一 client_msg_id：回查首次日志走 duplicate
            first = await ai_crud.find_log_by_client_msg(db, user_id, body.client_msg_id)
            if first and first.record_ids:
                return await _duplicate_response(db, first, user_id)
            return ai_error("请求处理中，请稍后重试")

    # ── 第 5 步：LLM 解析 ──
    from datetime import date as _date
    from models.category import Category

    today = _date.today()
    try:
        cat_rows = (await db.execute(
            select(Category).where(
                or_(Category.user_id == user_id, Category.user_id.is_(None))
            )
        )).scalars().all()
        # 用户自定义分类放前面，resolve_category 的精确匹配优先命中自定义
        user_cats = [c for c in cat_rows if c.user_id == user_id]
        sys_cats = [c for c in cat_rows if c.user_id != user_id]
        parsed = await parse_bookkeeping(
            message, today.isoformat(), [c.name for c in cat_rows]
        )
    except Exception:
        return ai_error("记账解析失败，请换个说法再试")

    # ── 第 6 步：意图过滤 -> ignored ──
    if parsed.intent in ("query", "chitchat") or (
        parsed.intent == "bookkeeping"
        and not any(i.is_expense_related for i in parsed.items)
    ):
        if log is not None:
            await ai_crud.update_bookkeeping_log(
                db, log.id, action="ignored",
                intent=parsed.intent, parse_json=parsed.model_dump(),
            )
            await db.commit()
        return BkIgnoredOut(
            request_id=request_id,
            reason="not_expense",
            echo="这不像一笔消费记录，我没有记账。想记账可以说「今天打车花了18块」。",
        ).model_dump(by_alias=True)

    # ── 第 7 步：条目数校验 + 逐条归一化 ──
    if len(parsed.items) > 10:
        return ai_error("一次最多识别 10 笔消费，请分开发送")

    ok_items, warnings = [], []
    for item in parsed.items:
        amount = bk_norm.normalize_amount(item.amount_raw, item.amount)
        if amount is None:
            continue    # 缺金额，进 clarify
        rec_date = bk_norm.normalize_date(item.date_expr, item.date, today)
        cat, fallback = bk_alias.resolve_category(item.category_name, user_cats + sys_cats)
        if fallback:
            cat = next((c for c in cat_rows if c.name == "其他"), None)
            warnings.append("未识别到明确分类，已归入「其他」")
        ok_items.append((item, amount, rec_date, cat))

    # ── 第 8 步：dry_run / clarify / created 三分支 ──
    def _preview_items():
        return [
            BkPreviewItem(
                amount=amt,
                amount_raw=it.amount_raw,
                type=it.type,
                category_name=cat.name if cat else None,
                category_id=cat.id if cat else None,
                date=rd.isoformat(),
                date_expr=it.date_expr,
                remark=it.remark,
                confidence=it.confidence,
            ).model_dump(by_alias=True)
            for it, amt, rd, cat in ok_items
        ] + [
            BkPreviewItem(
                amount=None,
                amount_raw=it.amount_raw,
                type=it.type,
                category_name=it.category_name,
                date_expr=it.date_expr,
                remark=it.remark,
                confidence=it.confidence,
            ).model_dump(by_alias=True)
            for it in parsed.items
            if bk_norm.normalize_amount(it.amount_raw, it.amount) is None
        ]

    if body.dry_run:
        return {"action": "preview", "requestId": request_id,
                "preview": {"items": _preview_items()}, "records": []}

    if not ok_items:    # 全部缺金额 -> clarify + 草稿（status=0）
        if log is not None:
            await ai_crud.update_bookkeeping_log(
                db, log.id, action="clarify", status=0,
                intent=parsed.intent, parse_json=parsed.model_dump(),
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
    for item, amount, rec_date, cat in ok_items:
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
        for (item, amount, rec_date, cat), rid in zip(ok_items, record_ids)
    ) + "\n回复「改成45块」可修改，回复「删掉」可撤销。"

    if log is not None:
        await ai_crud.update_bookkeeping_log(
            db, log.id, record_ids=record_ids,
            parse_json=parsed.model_dump(), action="created",
            intent=parsed.intent, status=1,
        )
    if body.session_id:
        await ai_crud.add_message(db, body.session_id, "user", message)
        await ai_crud.add_message(db, body.session_id, "assistant", echo)
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
            for (it, amt, rd, cat), rid in zip(ok_items, record_ids)
        ],
        total_amount=round(sum(amt for _, amt, _, _ in ok_items), 2),
        echo=echo,
        warnings=warnings,
        session_id=body.session_id,
    ).model_dump(by_alias=True)


@router.patch("/bookkeeping/{record_id}", summary="修改 AI 记账记录")
async def amend_bookkeeping(
    record_id: int,
    body: BookkeepingAmendIn,
    user_id: int = Depends(get_current_user),
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
    new_amount = body.amount
    new_category_id = body.category_id
    new_date = None
    if body.date:
        try:
            new_date = _date.fromisoformat(body.date)
        except ValueError:
            return ai_error("日期格式应为 yyyy-MM-dd")
    new_remark = body.remark

    # ── 2) message 解析链取增量字段（显式字段优先覆盖）──
    if body.message:
        msg = body.message.strip()
        if len(msg) > 500:
            return ai_error("消息过长，最多 500 字")
        cat_rows = (await db.execute(
            select(Category).where(
                or_(Category.user_id == user_id, Category.user_id.is_(None))
            )
        )).scalars().all()
        user_cats = [c for c in cat_rows if c.user_id == user_id]
        sys_cats = [c for c in cat_rows if c.user_id != user_id]
        try:
            parsed = await parse_bookkeeping(
                msg, _date.today().isoformat(), [c.name for c in cat_rows]
            )
        except Exception:
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

    if all(v is None for v in (new_amount, new_category_id, new_date, new_remark)):
        return ai_error("缺少修改内容")

    # ── 3) 校验并构造变更集 ──
    changes: dict[str, dict] = {}
    if new_amount is not None:
        if new_amount <= 0 or new_amount > bk_norm.MAX_AMOUNT:
            return ai_error("金额需大于 0 且不超过 99999999.99")
        old_amount = float(rec.amount)
        if round(old_amount, 2) != round(new_amount, 2):
            changes["amount"] = {"from": old_amount, "to": round(new_amount, 2)}
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
    user_id: int = Depends(get_current_user),
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
