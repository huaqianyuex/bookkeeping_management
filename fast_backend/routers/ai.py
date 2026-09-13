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

import json

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from config.db_config import get_db
from crud import ai as ai_crud
from schemas.ai import (
    BookkeepingAmendIn,
    BookkeepingIn,
    BudgetPlanIn,
    ChatIn,
    ExpenseAnalyzeIn,
    FeedbackIn,
    SessionCreateIn,
    SessionIdsIn,
    SessionOut,
    SessionRenameIn,
)
from utils.auth import get_current_user

router = APIRouter(prefix="/api/ai", tags=["ai"])


def ai_error(msg: str) -> dict:
    """AI 业务失败统一返回：HTTP 200 + 裸 {"error": "中文"}"""
    return {"error": msg}


# ── 会话 ────────────────────────────────────────────────────────────────

@router.post("/sessions", summary="创建会话")
async def create_session(
    body: SessionCreateIn,
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """6.1 创建会话：返回**裸 Session 对象**，前端读 data.id"""
    # 步骤 1：清洗标题 —— 前端可能传 null / 空串 / 纯空格，统一兜底为「新对话」
    #        （再截 50 字是双保险，Pydantic 的 max_length 只拦超长，不拦空格）
    title = (body.title or "").strip() or "新对话"

    # 步骤 2：落库 —— id/time 全部由 crud 层生成（new_id("session") / now_ms()），
    #        路由层不碰主键和时间戳，保证全模块口径一致
    session = await ai_crud.create_session(db, user_id, title)

    # 步骤 3：出参序列化 —— ORM 对象 → SessionOut（from_attributes 自动按属性取值）
    #        → model_dump(by_alias=True) 输出 camelCase（userId/createdAt/...），
    #        **裸 return**，不套 success_response 信封（模块头铁律）
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
    # TODO:
    # 1) sort 不在 {"updated","created"} -> return ai_error("sort 参数非法")
    # 2) order 不在 {"asc","desc"}       -> return ai_error("order 参数非法")
    # 3) size 夹取 1..100
    # 4) rows, total = await ai_crud.list_sessions(db, user_id, keyword, sort, order, page, size)
    # 5) items 组包：preview = ("你: "/"AI: ") + 末条消息 content 截 50 字，messageCount 计数
    # 6) return {"items": [...], "total": total}    # 裸返回
    return {"items": [], "total": 0}


# ⚠️ 必须注册在 `/sessions/{session_id}` 之前（见模块头说明）
@router.post("/sessions/batch-delete", summary="批量删除会话")
async def batch_delete_sessions(
    body: SessionIdsIn,
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """6.5 批量软删会话：返回 {success: true, deleted: N}"""
    # TODO:
    # 1) ids 去重；为空或 > 50 -> return ai_error("单次最多删除 50 条")
    #    （对外以网关口径为准：ids 为空也返回这条文案，不是「ids 不能为空」）
    # 2) deleted = await ai_crud.batch_soft_delete_sessions(db, user_id, ids)
    # 3) return {"success": True, "deleted": deleted}
    return {"success": True, "deleted": 0}


@router.patch("/sessions/{session_id}", summary="重命名会话")
async def rename_session(
    session_id: str,
    body: SessionRenameIn,
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """6.3 重命名：返回 {success: true, session: {...}}；改名后 autoTitle 置 0（锁定标题）"""
    # TODO:
    # 1) title = body.title.strip()；长度不在 1..50 -> return ai_error("标题需 1-50 字")
    # 2) session = await ai_crud.rename_session(db, session_id, user_id, title)
    #    session is None -> return {"success": False}
    # 3) return {"success": True, "session": SessionOut.model_validate(session).model_dump(by_alias=True)}
    return {"success": True, "session": None}


@router.delete("/sessions/{session_id}", summary="删除会话")
async def delete_session(
    session_id: str,
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """6.4 软删单个会话（deleted_at=毫秒）：返回 {success: bool}"""
    # TODO:
    # ok = await ai_crud.soft_delete_session(db, session_id, user_id)
    # return {"success": ok}     # 会话不存在/非本人/已删 -> {"success": False}
    return {"success": True}


@router.get("/sessions/{session_id}/messages", summary="会话消息")
async def list_messages(
    session_id: str,
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """6.6 会话消息：返回**裸数组**（MessageOut 列表，按 timestamp 升序）"""
    # TODO:
    # 1) session = await ai_crud.get_user_session(db, session_id, user_id)
    #    session is None -> return ai_error("会话不存在")
    # 2) msgs = await ai_crud.list_messages(db, session_id)
    # 3) return [MessageOut.model_validate(m).model_dump(by_alias=True) for m in msgs]
    return []


# ── 对话 ────────────────────────────────────────────────────────────────

@router.post("/chat", summary="非流式对话")
async def chat(
    body: ChatIn,
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """6.7 非流式对话：返回 {content: "..."}（字段名是 content，不是 answer）"""
    # TODO:
    # 1) session = await ai_crud.get_user_session(db, body.session_id, user_id)
    #    session is None -> return ai_error("会话不存在")
    # 2) await ai_crud.add_message(db, body.session_id, "user", body.message)
    # 3) history = await ai_crud.list_messages(db, body.session_id)  # 或 ai/memory.py 取窗口
    # 4) content = await ai/chat_chain 的非流式入口（LLM 调用，见 06 §5）
    # 5) await ai_crud.add_message(db, body.session_id, "assistant", content)
    # 6) return {"content": content}
    # 异常兜底：except Exception as e -> return ai_error(f"对话失败: {e}")
    return {"content": ""}


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
    # TODO:
    # 1) body.message 为空 / sessionId 为空 -> HTTPException(400)
    # 2) 校验会话归属，非本人 -> return ai_error("会话不存在")
    # 3) async def event_gen():
    #        yield sse({"type": "content", "content": chunk})   # LLM 逐块产出
    #        ... 落库 user / assistant 两条消息（ai_crud.add_message）
    #        yield sse({"type": "done", "messageId": ...})
    #    其中 sse(d) = f"data: {json.dumps(d, ensure_ascii=False)}\n\n"
    # 4) return StreamingResponse(event_gen(), media_type="text/event-stream")
    return StreamingResponse(
        iter([f"data: {json.dumps({'type': 'error', 'message': '未实现'}, ensure_ascii=False)}\n\n"]),
        media_type="text/event-stream",
    )


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
    # TODO:
    # try:
    #     query = body.query or "请分析我的消费情况"
    #     ctx = await ai_context.build_user_context(user_id)        # 本月+上月汇总、Top5
    #     data = await ai_analyze_chain.analyze_expense(user_id, ...)  # LLM 结构化输出
    #     return {"success": True, "data": data.model_dump()}
    # except Exception as e:
    #     return ai_error(f"分析失败: {e}")
    return {"success": True, "data": None}


@router.post("/analyze/budget", summary="预算规划")
async def analyze_budget(
    body: BudgetPlanIn,
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """6.10 预算规划：返回 {success: true, data: BudgetPlan}"""
    # TODO:
    # try:
    #     ctx = await ai_context.build_user_context(user_id)
    #     data = await ai_analyze_chain.plan_budget(body.monthly_income, body.savings_goal, ctx)
    #     return {"success": True, "data": data.model_dump()}
    # except Exception as e:
    #     return ai_error(f"预算规划失败: {e}")
    return {"success": True, "data": None}


# ── FAQ ────────────────────────────────────────────────────────────────

@router.get("/faq/search", summary="FAQ 语义检索")
async def faq_search(
    query: str,
    user_id: int = Depends(get_current_user),
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
    return {"results": []}


@router.post("/faq/rebuild", summary="重建 FAQ 向量索引")
async def faq_rebuild(
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """6.12 重建 FAQ 索引：成功 {success: true, count: n}；失败 {error, detail}"""
    # TODO:
    # try:
    #     rows = await ai_crud.list_faq(db)
    #     count = await ai_faq_retriever.rebuild(rows)   # 清空->重载->算向量->持久化
    #     return {"success": True, "count": count}
    # except Exception as e:
    #     return {"error": "重建失败", "detail": str(e)}
    return {"success": True, "count": 0}


# ── 反馈 / 统计 ────────────────────────────────────────────────────────

@router.post("/feedback", summary="保存反馈")
async def submit_feedback(
    body: FeedbackIn,
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """6.13 保存反馈：返回 {success: true}；写库失败 {"error": "保存失败"}

    注意：feedback 表没有 user_id 列，无法按用户隔离（02 §3.3 已知限制）。
    """
    # TODO:
    # try:
    #     await ai_crud.create_feedback(db, body.message_id, body.rating, body.comment)
    #     return {"success": True}
    # except Exception:
    #     return ai_error("保存失败")
    return {"success": True}


@router.get("/admin/stats", summary="AI 会话统计")
async def ai_admin_stats(
    user_id: int = Depends(get_current_user),   # 6.14：仅登录，非管理员（差异表 #9）
    db: AsyncSession = Depends(get_db),
):
    """6.14 AI 使用统计：{totalSessions, totalMessages, totalFeedback, averageRating}"""
    # TODO:
    # stats = await ai_crud.ai_stats(db)   # 全量 COUNT 不过滤 deleted_at；AVG(rating) 空回 0
    # return stats
    return {"totalSessions": 0, "totalMessages": 0, "totalFeedback": 0, "averageRating": 0}


# ── 自然语言记账 ────────────────────────────────────────────────────────

@router.post("/bookkeeping", summary="自然语言记账")
async def bookkeeping(
    body: BookkeepingIn,
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """6.15 自然语言记账：四种 action 形态 created/clarify/ignored/duplicate + {"error"}

    解析链 BookkeepingChain 见 06 §11；幂等日志表 ai_bookkeeping_logs（models/bookkeeping.py 已有）。
    """
    # TODO（流程较长，按序实现）:
    # 1) message = (body.message or "").strip()
    #    为空 -> ai_error("缺少参数: message")；>500 字 -> ai_error("消息过长，最多 500 字")
    # 2) body.session_id 非空时 ai_crud.get_user_session 校验归属 -> ai_error("会话不存在")
    # 3) 幂等：client_msg_id -> find_log_by_client_msg()；否则
    #    dedup_hash=sha256(f"{user_id}|{归一化文本}") + find_recent_by_dedup(300s 窗口)
    #    命中 -> 反查 record_ids -> return {"action": "duplicate", "originRequestId": ..., ...}
    # 4) 先 INSERT 日志（request_id=new_id("bk")）拿 id；捕获 IntegrityError -> 回查 -> duplicate
    #    （幂等靠 uk_abk_client_msg 唯一键兜底，禁止先 SELECT 再 INSERT）
    # 5) parsed = await get_bookkeeping_chain().parse(message, today, category_names)
    #    LLM 失败 -> ai_error("记账解析失败，请换个说法再试")
    # 6) intent ∈ {query, chitchat} 或非消费 -> action="ignored" + reason + echo
    # 7) 条目 > 10 -> ai_error("一次最多识别 10 笔消费，请分开发送")
    #    逐条 normalize_amount / normalize_date / resolve_category（06 §11.3-11.5）
    # 8) dry_run -> preview（不写 records、不参与去重）
    #    全部缺金额 -> action="clarify" + draftId（日志 status=0）
    #    否则同一事务逐条 INSERT records -> action="created" + totalAmount + echo
    # 9) 回写日志 record_ids/parse_json/action；sessionId 非空则 add_message 落库 user+assistant
    return {"action": "ignored", "records": []}


@router.patch("/bookkeeping/{record_id}", summary="修改 AI 记账记录")
async def amend_bookkeeping(
    record_id: int,
    body: BookkeepingAmendIn,
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """6.16 修改 AI 记账：返回 {success, record, changes, echo}；changes 只列实际变动字段"""
    # TODO:
    # 1) 查 records：id + user_id + status=1，无 -> ai_error("记录不存在")
    # 2) body 全空 -> ai_error("缺少修改内容")
    # 3) body.message 存在时走解析链取增量字段（显式字段优先覆盖）
    # 4) 校验 amount>0 且≤99999999.99 / categoryId 归属本人且 type 与原记录一致 / remark 截 200
    # 5) UPDATE records；追加日志 action='amend', parent_id=原记账日志
    # 6) changes = {字段: {"from": 旧, "to": 新}}（仅变动项）-> return {"success": True, ...}
    return {"success": False}


@router.delete("/bookkeeping/{record_id}", summary="删除 AI 记账记录")
async def delete_bookkeeping(
    record_id: int,
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """6.17 删除 AI 记账（软删 status=0）：返回 {success, echo}"""
    # TODO:
    # 1) 查 records：id + user_id + status=1，无 -> ai_error("记录不存在")
    # 2) UPDATE records SET status=0（软删，与账单模块口径一致）
    # 3) 追加日志 action='delete'，原记账日志 status=2（已回滚）
    # 4) return {"success": True, "echo": "已删除 #128（餐饮 ¥79.00 · 2026-09-10）"}
    return {"success": False}
