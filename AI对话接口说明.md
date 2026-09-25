# AI 对话接口说明

> 本文档从《10-实现骨架.md》§六（AI 模块 `/api/ai`）中抽取全部 AI 对话相关接口，按接口逐节整理，供后端实现与前端联调单独查阅。术语、命名、契约与原文档保持一致；更细的设计背景见 05（接口规范）、06（模块设计）、02（数据库）。
>
> ⚠️ 文件路径已按实际工程结构（`fast_backend/`）校正：原骨架文档使用 `app/api/v1/`、`app/schemas/` 等 Java 风格占位路径，实际代码为 `routers/`、`schemas/`、`crud/`、`ai/`、`models/`、`config/`、`utils/` 扁平结构，鉴权依赖为 `utils/auth.py` 的 `get_current_user`，数据库会话为 `config/db_config.py` 的 `get_db`。

## 模块级约定（先读，所有接口通用）

- **放置**：`routers/ai.py`（`from routers import ai`，`main.py` 中 `app.include_router(ai.router)`），`APIRouter(prefix="/api/ai", tags=["ai"])`；**全部接口需登录**（`get_current_user`）。
- **铁律**（违反即前端崩）：
  1. `/api/ai/**` 一律**裸返回，禁止套 `Result`**——前端 `AiChat.jsx` 用原生 `fetch` 直接读裸结构；
  2. 会话/消息时间戳为 **int 毫秒**（`createdAt` / `updatedAt` / `deletedAt` / `timestamp` 皆是），非 ISO 字符串；
  3. SSE 事件行必须是 `data: {"type":"content"|"done"|"error",...}\n\n`。
- **错误处理**：业务失败一律 `return ai_error("中文")`（HTTP 200），**勿抛 `BizError`**——那会被全局处理器包成 `{code,message,data}`，破坏裸契约。
- **数据表**：`sessions` / `messages` / `feedback`（02 §3），时间均为毫秒 `BIGINT`；字符串 ID 生成规则 `session_/msg_/feedback_{毫秒}_{随机≤9位}`；记账相关另有 `records` 与 `ai_bookkeeping_logs`（02 §3.5）。
- **response_model 约定**：本模块端点**刻意不声明 `response_model`**（值为 `None`）。每个端点都有「成功结构」与「`{"error":...}` 失败结构」两种返回形态，声明单一模型会让失败分支被 FastAPI 校验拦下并转成 500。若需 OpenAPI 展示，用 `response_model=Union[XxxOut, ErrorOut]`。
- **模块级依赖**：FastAPI、SQLAlchemy `AsyncSession`（`config/db_config.py` 的 `get_db`）、Pydantic v2（`alias` 序列化 camelCase）、`ai/` 下的 Chain 与 LLM 单例（LangChain `ChatOpenAI`）、`utils/auth.py` 的 `get_current_user`。

### 公共入参/出参模型（`schemas/ai.py`）

```python
from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.base import OrmBase


class ErrorOut(BaseModel):
    """AI 模块统一失败结构（HTTP 200）"""
    error: str


class SessionCreateIn(BaseModel):
    """创建会话请求体"""
    title: Optional[str] = Field(None, max_length=50, description="会话标题，缺省「新对话」")


class SessionRenameIn(BaseModel):
    """重命名会话请求体"""
    title: str = Field(..., description="新标题，trim 后 1–50 字")


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
    message: str = Field(..., min_length=1)

    model_config = ConfigDict(populate_by_name=True)


class ChatOut(BaseModel):
    """非流式对话出参（字段名是 content，不是 answer）"""
    content: str


class SessionIdsIn(BaseModel):
    """AI 批量删除会话请求体（元素为 string，与业务模块 int 版 IdsIn 不同）"""
    ids: List[str] = Field(..., min_length=1, description="会话 ID 数组，单次最多 50 条")
```

> ⚠️ 模型拆分注意：业务模块的 `IdsIn`（`schemas/admin.py`）元素是 **int**，AI 会话批删的元素是 **string**。**不要复用同一个类名**。

### 公共错误助手

```python
import json

from fastapi.responses import StreamingResponse

ai = APIRouter(prefix="/api/ai", tags=["ai"])


def ai_error(msg: str) -> dict:
    """AI 业务失败统一返回：HTTP 200 + 裸 {"error": "中文"}"""
    return {"error": msg}
```

> TODO（需补充）：原骨架规划的 `get_chat_chain()` / `get_analyze_chain()` / `get_faq_retriever()` / `build_minimal_context` 等工厂式签名与 06 对齐后再落代码；当前实际实现为函数式调用：`ai/chat_chain.py`（`chat_stream`）、`ai/analyze_chain.py`（`analyze_expense`）、`ai/faq_retriever.py`（`search_faq`）、`ai/context.py`（`build_user_context`）、`ai/llm.py`（`get_chat_llm` / `get_analyze_llm` / `get_embeddings`）、`ai/memory.py`（`get_history_messages`）。仓储函数（`get_session` / `create_session` / `list_sessions` / `rename_session` / `soft_delete_session` / `add_message` / `list_messages`）位于 `crud/ai.py`（06 §7）。

---

## 6.1 创建会话

**接口**：`POST /api/ai/sessions`　**登录**：是　**标签**：`ai`　**成功状态码**：`200`

**功能描述**：用户点开 AI 助手面板时新建一个对话会话。前端 `createSession` 读返回的 `data`/裸对象的 `id` 字段后续发消息。

**依赖注入**：`body: SessionCreateIn`、`user: int = Depends(get_current_user)`、`db: AsyncSession = Depends(get_db)`；`response_model: None`（裸返回）。

### 请求体 `SessionCreateIn`

| 字段 | JSON 键 | 类型 | 必填 | 默认值 | 含义与约束 |
|------|---------|------|------|--------|------------|
| title | title | str \| null | 否 | `"新对话"` | 会话标题。服务端**截断 50 字符**（库列 `VARCHAR(50)`） |

```json
{ "title": "新对话" }
```

### 返回结果

```json
{
  "id": "session_1725700000000_ab12cd34x",
  "userId": 1,
  "title": "新对话",
  "autoTitle": 1,
  "createdAt": 1725700000000,
  "updatedAt": 1725700000000,
  "deletedAt": 0
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| id | string | 主键。格式 `session_{毫秒}_{随机段}`（随机段对应 JS `substring(2,11)`，最长 9 位） |
| autoTitle | int | 新建恒为 `1`（允许 AI 自动改标题） |
| createdAt / updatedAt | int | **毫秒时间戳**，两者相等 |
| deletedAt | int | 新建恒为 `0` |

### 错误场景

| 场景 | HTTP | 响应体 |
|------|------|--------|
| 未登录 / Token 无效 | 401 | `{"code":401,"message":"未登录","data":null}`（由鉴权依赖抛出，**唯一会套 Result 的情况**） |
| 数据库写入失败 | 200 | `{"error": "..."}` |

### 实现依赖

- 数据表：`sessions`；
- 模块：`schemas/ai.py`（`SessionCreateIn` / `SessionOut`）、`crud/ai.py`（`create_session`）、ID 生成（毫秒 + 随机段）。

### 具体实现

```python
@ai.post("/sessions", summary="创建会话")
async def create_session(body: SessionCreateIn, user: int = Depends(get_current_user),
                         db: AsyncSession = Depends(get_db)) -> Any:
    # 1) title = (body.title or "新对话")[:50]
    # 2) now_ms = int(time.time() * 1000)
    # 3) INSERT sessions(id=f"session_{now_ms}_{rand9}", user_id=user.id, title=title,
    #                    auto_title=1, created_at=now_ms, updated_at=now_ms, deleted_at=0)
    # 4) return 裸 Session dict（勿套 Result）
    return None
```

---

## 6.2 会话列表

**接口**：`GET /api/ai/sessions`　**登录**：是　**标签**：`ai`　**成功状态码**：`200`

**功能描述**：AI 助手侧边栏的会话历史列表，支持关键词搜索、按更新时间/创建时间排序、翻页。

**依赖注入**：`user: int = Depends(get_current_user)`、`db: AsyncSession = Depends(get_db)`；`response_model: None`（裸返回）。

### 请求参数（query）

| 参数 | 类型 | 必填 | 默认值 | 含义与约束 |
|------|------|------|--------|------------|
| keyword | str | 否 | `""` | 搜索词。命中 `sessions.title LIKE %kw%` **或** 该会话下任意 `messages.content LIKE %kw%` |
| sort | str | 否 | `"updated"` | 排序字段。仅 `updated` / `created`，其他值返回 `{"error":"sort 参数非法"}` |
| order | str | 否 | `"desc"` | 排序方向。仅 `asc` / `desc`，其他值返回 `{"error":"order 参数非法"}` |
| page | int | 否 | `1` | 页码。`< 1` → 视为 `1`（Java 行为，非 400） |
| size | int | 否 | `20` | 每页条数。**夹取到 `1..100`**（超范围不报错，直接收敛） |

### 返回结果

```json
{
  "items": [
    {
      "id": "session_1725700000000_ab12cd34x",
      "title": "帮我分析本月消费",
      "preview": "你: 帮我分析本月消费",
      "messageCount": 2,
      "createdAt": 1725700000000,
      "updatedAt": 1725701000000
    }
  ],
  "total": 1
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| items | array | 当前页会话，**结构为 `{items,total}`，不是业务 `PageResult`** |
| total | int | 符合条件的会话总数 |
| items[].preview | string | 会话**最后一条消息**（按 `timestamp` 升序取末条）：`role=="user"` → 前缀 `"你: "`，否则 `"AI: "`；content 截断 50 字 |
| items[].messageCount | int | 该会话消息条数 |

筛选语义（`db.ts listSessions`）：仅统计 `deleted_at = 0 AND user_id = :uid`；排序 `sortCol DESC, id DESC`。

### 错误场景

| 场景 | HTTP | 响应体 |
|------|------|--------|
| `sort` 非法 | 200 | `{"error": "sort 参数非法"}` |
| `order` 非法 | 200 | `{"error": "order 参数非法"}` |
| 未登录 / Token 无效 | 401 | Result 结构（由依赖抛出） |

### 实现依赖

- 数据表：`sessions`、`messages`（preview 子查询与 keyword 命中）；
- 模块：`schemas/ai.py`（`SessionListItem` / `SessionListOut`）、`crud/ai.py`（`list_sessions`）。

### 具体实现

```python
@ai.get("/sessions", summary="会话列表")
async def list_sessions(user: int = Depends(get_current_user),
                        db: AsyncSession = Depends(get_db),
                        keyword: str = Query(""),
                        sort: str = Query("updated"),
                        order: str = Query("desc"),
                        page: int = Query(1, ge=1),
                        size: int = Query(20)) -> Any:
    # 1) sort 不在 {"updated","created"} -> return ai_error("sort 参数非法")   # HTTP 200
    # 2) order 不在 {"asc","desc"}     -> return ai_error("order 参数非法")
    # 3) size 夹取 1..100；page = max(page, 1)
    # 4) WHERE deleted_at=0 AND user_id=:uid
    #    [AND (s.title LIKE %kw% OR EXISTS(SELECT 1 FROM messages m
    #         WHERE m.session_id=s.id AND m.content LIKE %kw%))]
    # 5) 子查询/窗口取每个会话的末条消息作 preview；COUNT 总数
    # 6) ORDER BY :sort :order, id DESC；LIMIT/OFFSET
    # 7) return {"items": [...], "total": n}      # 勿套 Result
    return {"items": [], "total": 0}
```

---

## 6.3 重命名会话

**接口**：`PATCH /api/ai/sessions/{id}`　**登录**：是　**标签**：`ai`　**成功状态码**：`200`

**功能描述**：用户手动改名后**锁定标题**，AI 不再自动覆盖（`auto_title` 置 0）。

**依赖注入**：`body: SessionRenameIn`、`user: int = Depends(get_current_user)`、`db: AsyncSession = Depends(get_db)`；`response_model: None`（裸返回）。

### 路径参数

| 参数 | 类型 | 必填 | 含义与约束 |
|------|------|------|------------|
| id | string | 是 | 会话 ID（如 `session_1725700000000_ab12cd34x`） |

### 请求体 `SessionRenameIn`

| 字段 | JSON 键 | 类型 | 必填 | 默认值 | 含义与约束 |
|------|---------|------|------|--------|------------|
| title | title | str | 是 | — | 新标题。**trim 后长度须为 1–50**，否则 `{"error":"标题需 1-50 字"}` |

```json
{ "title": "本月消费分析" }
```

### 返回结果

```json
{
  "success": true,
  "session": {
    "id": "session_1725700000000_ab12cd34x",
    "userId": 1,
    "title": "本月消费分析",
    "autoTitle": 0,
    "createdAt": 1725700000000,
    "updatedAt": 1725701000000,
    "deletedAt": 0
  }
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| success | bool | 成功 `true` / 失败 `false`（**不是 `{"error":...}`，与 6.1/6.2 形态不同**） |
| session | object | 更新后的完整 Session 对象；`success=false` 时该字段可能缺省 |

### 错误场景

| 场景 | HTTP | 响应体 |
|------|------|--------|
| 标题为空 / > 50 字 | 200 | `{"error": "标题需 1-50 字"}` |
| 会话不存在 / 非本人 / 已删除 | 200 | `{"success": false}` |
| 未登录 / Token 无效 | 401 | Result 结构（由依赖抛出） |

### 实现依赖

- 数据表：`sessions`；
- 模块：`schemas/ai.py`（`SessionRenameIn` / `SessionOut`）、`crud/ai.py`（`get_session` / `rename_session`）。

### 具体实现

```python
@ai.patch("/sessions/{session_id}", summary="重命名会话")
async def rename_session(session_id: str, body: SessionRenameIn, user: int = Depends(get_current_user),
                         db: AsyncSession = Depends(get_db)) -> Any:
    # 1) title = body.title.strip()；长度不在 1..50 -> return ai_error("标题需 1-50 字")
    # 2) SELECT * FROM sessions WHERE id=:session_id AND user_id=:uid AND deleted_at=0
    #    无行 -> return {"success": False}
    # 3) UPDATE sessions SET title=:title, auto_title=0, updated_at=now_ms WHERE id=:session_id
    # 4) return {"success": True, "session": {...}}
    return {"success": False}
```

---

## 6.4 删除会话

**接口**：`DELETE /api/ai/sessions/{id}`　**登录**：是　**标签**：`ai`　**成功状态码**：`200`

**功能描述**：用户删除单个会话。**软删除**：`deleted_at` 写入当前毫秒，数据保留，由定时任务在 7 天后物理清除（07 §1）。

**依赖注入**：`user: int = Depends(get_current_user)`、`db: AsyncSession = Depends(get_db)`；`response_model: None`（裸返回）。

### 路径参数

| 参数 | 类型 | 必填 | 含义与约束 |
|------|------|------|------------|
| id | string | 是 | 会话 ID |

### 返回结果

```json
{ "success": true }
```

### 错误场景

| 场景 | HTTP | 响应体 |
|------|------|--------|
| 会话不存在 / 非本人 / 已删除 | 200 | `{"success": false}` |
| 未登录 / Token 无效 | 401 | Result 结构（由依赖抛出） |

### 实现依赖

- 数据表：`sessions`；
- 模块：`crud/ai.py`（`soft_delete_session`）。

### 具体实现

```python
@ai.delete("/sessions/{session_id}", summary="删除会话")
async def delete_session(session_id: str, user: int = Depends(get_current_user),
                         db: AsyncSession = Depends(get_db)) -> Any:
    # 1) UPDATE sessions SET deleted_at=now_ms
    #     WHERE id=:session_id AND user_id=:uid AND deleted_at=0
    # 2) rowcount == 0 -> return {"success": False}；否则 {"success": True}
    return {"success": False}
```

---

## 6.5 批量删除会话

**接口**：`POST /api/ai/sessions/batch-delete`　**登录**：是　**标签**：`ai`　**成功状态码**：`200`

**功能描述**：会话列表多选后批量清理。

**依赖注入**：`body: SessionIdsIn`、`user: int = Depends(get_current_user)`、`db: AsyncSession = Depends(get_db)`；`response_model: None`（裸返回）。

### 请求体 `SessionIdsIn`

| 字段 | JSON 键 | 类型 | 必填 | 默认值 | 含义与约束 |
|------|---------|------|------|--------|------------|
| ids | ids | array[string] | 是 | — | 会话 ID 数组。**为空或超过 50 条** → `{"error":"单次最多删除 50 条"}`；重复项自动去重 |

```json
{ "ids": ["session_1725700000000_ab12cd34x"] }
```

> ⚠️ 类型差异：这里元素是 **string**，而业务模块 §5.4 / §5.6 的 `IdsIn` 元素是 **int**，两类模型不可混用（见模块级约定）。

### 返回结果

```json
{ "success": true, "deleted": 1 }
```

| 字段 | 类型 | 说明 |
|------|------|------|
| deleted | int | 实际软删的条数（去重后、仅本人且未删的才计入） |

### 错误场景

| 场景 | HTTP | 响应体 |
|------|------|--------|
| ids 为空或 > 50 | 200 | `{"error": "单次最多删除 50 条"}` |
| 未登录 / Token 无效 | 401 | Result 结构（由依赖抛出） |

> ⚠️ 口径说明：旧 Java 网关对「ids 为空」**同样**返回「单次最多删除 50 条」，与 Express 层「ids 不能为空」不同。**对外以网关口径为准**（05 §1.5）。

### 实现依赖

- 数据表：`sessions`；
- 模块：`schemas/ai.py`（`SessionIdsIn`）、`crud/ai.py`（批量软删）。

### 具体实现

```python
@ai.post("/sessions/batch-delete", summary="批量删除会话")
async def batch_delete_sessions(body: SessionIdsIn, user: int = Depends(get_current_user),
                                db: AsyncSession = Depends(get_db)) -> Any:
    # 1) ids = list(dict.fromkeys(body.ids))        # 去重（保持顺序）
    # 2) if not ids or len(ids) > 50:
    #        return ai_error("单次最多删除 50 条")
    # 3) UPDATE sessions SET deleted_at=now_ms
    #     WHERE id IN :ids AND user_id=:uid AND deleted_at=0
    # 4) return {"success": True, "deleted": rowcount}
    return {"success": True, "deleted": 0}
```

---

## 6.6 会话消息

**接口**：`GET /api/ai/sessions/{id}/messages`　**登录**：是　**标签**：`ai`　**成功状态码**：`200`

**功能描述**：打开历史会话时回填对话气泡列表。

**依赖注入**：`user: int = Depends(get_current_user)`、`db: AsyncSession = Depends(get_db)`；`response_model: None`（裸返回）。

### 路径参数

| 参数 | 类型 | 必填 | 含义与约束 |
|------|------|------|------------|
| id | string | 是 | 会话 ID |

### 请求参数

无。

### 返回结果

**裸数组**（按 `timestamp` 升序）：

```json
[
  { "id": "msg_1725700000100_aa11bb22c", "sessionId": "session_1725700000000_ab12cd34x",
    "role": "user", "content": "帮我分析本月消费", "timestamp": 1725700000100 },
  { "id": "msg_1725700000456_q8w7e6", "sessionId": "session_1725700000000_ab12cd34x",
    "role": "assistant", "content": "本月支出较上月上升 12%...", "timestamp": 1725700000456 }
]
```

| 字段 | 类型 | 说明 |
|------|------|------|
| （根） | array | **响应体本身就是数组**，不是 `{data:[...]}` |
| [].role | string | `user` 或 `assistant` |
| [].timestamp | int | 毫秒时间戳 |

### 错误场景

| 场景 | HTTP | 响应体 |
|------|------|--------|
| 会话不存在 / 非本人 / 已删除 | 200 | `[]`（**空数组，非错误对象**，保持 Java 行为） |
| 未登录 / Token 无效 | 401 | Result 结构（由依赖抛出） |

### 实现依赖

- 数据表：`sessions`（归属校验）、`messages`；
- 模块：`schemas/ai.py`（`MessageOut`）、`crud/ai.py`（`list_messages`）。

### 具体实现

```python
@ai.get("/sessions/{session_id}/messages", summary="会话消息")
async def session_messages(session_id: str, user: int = Depends(get_current_user),
                           db: AsyncSession = Depends(get_db)) -> Any:
    # 1) 校验会话归属（id + user_id + deleted_at=0）；不合法 -> return []     # 空数组，非 error
    # 2) SELECT * FROM messages WHERE session_id=:session_id ORDER BY timestamp ASC
    # 3) return 裸数组（勿包 data）
    return []
```

---

## 6.7 非流式对话

**接口**：`POST /api/ai/chat`　**登录**：是　**标签**：`ai`　**成功状态码**：`200`

**功能描述**：兼容 UniApp 移动端的一次性问答（React 桌面端主用 §6.8 流式）。

**依赖注入**：`body: ChatIn`、`user: int = Depends(get_current_user)`、`db: AsyncSession = Depends(get_db)`；`response_model: None`（裸返回）。

### 请求体 `ChatIn`

| 字段 | JSON 键 | 类型 | 必填 | 默认值 | 含义与约束 |
|------|---------|------|------|--------|------------|
| session_id | sessionId | str | 是 | — | 会话 ID；必须归属当前用户且未删除 |
| message | message | str | 是 | — | 用户消息，非空 |

```json
{ "sessionId": "session_1725700000000_ab12cd34x", "message": "帮我分析本月消费" }
```

### 返回结果

```json
{ "content": "本月支出较上月上升 12%，主要增长在餐饮..." }
```

| 字段 | 类型 | 说明 |
|------|------|------|
| content | string | AI 完整回复。**字段名是 `content` 而非 `answer`**（Express 曾用 `answer`，Java 已转 `content`，本实现保持 `content`） |

实现流程（05 §2.1）：取用户上下文 → 会话归属校验 → `ChatChain.chat(...)`。Chain 内部会把本轮 **user 消息与 assistant 完整回复双双落库**到 `messages`（06 §3.2）。

### 错误场景

| 场景 | HTTP | 响应体 |
|------|------|--------|
| `sessionId` / `message` 缺一 | 200 | `{"error": "缺少参数"}` |
| 会话不存在 / 非本人 / 已删除 | 200 | `{"error": "会话不存在"}` |
| LLM 调用异常 | 200 | `{"error": "<异常信息>"}` |
| 未登录 / Token 无效 | 401 | Result 结构（由依赖抛出） |

### 实现依赖

- 数据表：`sessions`、`messages`（Chain 内部落库）、`records` / `categories` 等（`ai/context.py` 的 `build_user_context` 组包财务上下文）；
- 外部服务：LLM（`ChatOpenAI`，`ai/llm.py` 的 `get_chat_llm()` 单例）；
- 模块：`schemas/ai.py`（`ChatIn` / `ChatOut`）、`ai/chat_chain.py`（`chat_stream`）、`ai/context.py`（`build_user_context`）、`ai/memory.py`（`get_history_messages`）。

### 具体实现

```python
@ai.post("/chat", summary="非流式对话")
async def chat(body: ChatIn, user: int = Depends(get_current_user),
               db: AsyncSession = Depends(get_db)) -> Any:
    # 1) sessionId/message 缺一 -> return ai_error("缺少参数")
    # 2) 会话归属校验（不存在/非本人/已删）-> return ai_error("会话不存在")
    # 3) ctx = await build_user_context(db, user.id)              # 06 §2
    # 4) answer = await get_chat_chain().chat(body.session_id, body.message, ctx, db)
    # 5) return {"content": answer}                               # 勿套 Result
    return {"content": ""}
```

---

## 6.8 流式对话（SSE）

**接口**：`POST /api/ai/chat/stream`　**登录**：是　**标签**：`ai`　**成功状态码**：`200`（`Content-Type: text/event-stream`）　**缺参状态码**：`400`（**无 body**，Java 直写 400，属唯一例外）

**功能描述**：React 桌面端 AI 助手主页的打字机效果。前端用 `fetch` + `ReadableStream` 手动解析，**只认 `data: ` 前缀行**。

**依赖注入**：`body: ChatIn`、`user: int = Depends(get_current_user)`、`db: AsyncSession = Depends(get_db)`；`response_model: None`（返回 `StreamingResponse`，不能声明模型）。

### 请求体 `ChatIn`

同 §6.7。

```json
{ "sessionId": "session_1725700000000_ab12cd34x", "message": "帮我分析本月消费" }
```

### 返回结果

**响应头**：

```
Content-Type: text/event-stream; charset=utf-8
Cache-Control: no-cache
Connection: keep-alive
X-Accel-Buffering: no
```

**响应（SSE 事件流，字节级精确）**：

```
data: {"type":"content","content":"本月支出"}

data: {"type":"content","content":"较上月上升 12%"}

data: {"type":"done"}

```

| 事件 type | 载荷 | 说明 |
|-----------|------|------|
| `content` | `content: string` | 增量文本片段，前端追加渲染 |
| `done` | 无 | 结束标志，随后关闭连接；**不是 `[DONE]` 字符串** |
| `error` | `error: string` | 出错（含 LLM 异常、会话不存在），发送后关闭连接 |

> 红线：端点与生成器**必须全 async**；每条事件必须含 `type` 字段；必须按 UTF-8 写出（FastAPI 的 `StreamingResponse` 直接 yield `str` 即可，无 Java 的 Latin-1 坑）。

### 错误场景

| 场景 | HTTP / 事件 |
|------|-------------|
| `sessionId` / `message` 缺一 | HTTP `400`（无 body） |
| 会话不存在 / 非本人 / 已删除 | `data: {"type":"error","error":"会话不存在"}` 后关闭 |
| LLM 异常 | `data: {"type":"error","error":"<异常信息>"}` 后关闭 |
| 未登录 / Token 无效 | HTTP `401`（在流建立前由依赖抛出） |

### 实现依赖

- 数据表：同 §6.7（`sessions` / `messages`）；
- 外部服务：LLM 流式（`ChatOpenAI(streaming=True)`）；
- 模块：`ai/chat_chain.py`（`stream_chat`）、`fastapi.responses.StreamingResponse`、`ai/memory.py`（上下文拼接）。

### 具体实现

```python
@ai.post("/chat/stream", summary="流式对话（SSE）")
async def chat_stream(body: ChatIn, user: int = Depends(get_current_user),
                      db: AsyncSession = Depends(get_db)) -> Any:
    if not body.session_id or not body.message:
        return Response(status_code=400)                       # 缺参：裸 400，无 body

    async def gen():
        try:
            # 1) 会话归属校验（不合法 -> raise，走 error 事件）
            # 2) ctx = await build_user_context(db, user.id)
            # 3) async for chunk in get_chat_chain().stream_chat(...):
            #        yield f"data: {json.dumps({'type':'content','content': chunk}, ensure_ascii=False)}\n\n"
            # 4) 结束后若 auto_title == 1，异步生成标题（不阻塞 SSE 结束，06 §3.4）
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream", headers={
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    })
```

---

## 6.9 消费分析

**接口**：`POST /api/ai/analyze/expenses`　**登录**：是　**标签**：`ai`　**成功状态码**：`200`

**功能描述**：用户点击「分析我的消费」时，服务端**自行查库组包**（本月汇总 + 支出 Top5 + 上月汇总），交给 LLM 产出结构化分析报告，前端渲染成卡片（总结 / 洞察 / 建议 / 健康度）。

**依赖注入**：`body: ExpenseAnalyzeIn`、`user: int = Depends(get_current_user)`、`db: AsyncSession = Depends(get_db)`；`response_model: None`（裸返回）。

### 请求体 `ExpenseAnalyzeIn`

| 字段 | JSON 键 | 类型 | 必填 | 默认值 | 含义与约束 |
|------|---------|------|------|--------|------------|
| query | query | str | 否 | `"请分析我的消费情况"` | 用户的自然语言诉求，作为提示词的 human 片段 |

```json
{ "query": "分析下这个月消费" }
```

> 财务数据（金额、分类、上月对比）**由服务端现查 MySQL 组包**，前端**不传**任何金额/分类参数（Java 行为；迁移后全部进程内完成，06 §2）。

### 返回结果

```json
{
  "success": true,
  "data": {
    "summary": "本月支出较上月上升 12%，主要增长集中在餐饮与娱乐...",
    "total_expense": 3500.00,
    "top_categories": [
      { "name": "餐饮", "amount": 1200.00, "percentage": 34.2, "trend": "上升" }
    ],
    "insights": ["餐饮支出占比连续两月上升", "周末消费明显高于工作日", "娱乐支出环比翻倍"],
    "suggestions": ["将餐饮预算控制在 1000 元以内", "设置娱乐类月限额", "本周可尝试自带午餐"],
    "savings_rate": 43.7,
    "risk_level": "一般"
  }
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| success | bool | 成功 `true` |
| data | object | `ExpenseAnalysis` 结构（06 §4.1）。**注意字段名为 snake_case**：`total_expense` / `top_categories` / `savings_rate` / `risk_level` |
| data.top_categories[].trend | string | 枚举：`上升` / `下降` / `持平` |
| data.insights / suggestions | array[string] | 元素为单句中文，长度分别 ≥ 3 条 |
| data.savings_rate | number | 储蓄率百分比，精确到 1 位小数 |
| data.risk_level | string | 枚举：`健康` / `一般` / `偏高` |

### 错误场景

| 场景 | HTTP | 响应体 |
|------|------|--------|
| LLM 调用失败 / 输出无法通过 Pydantic 校验 | 200 | `{"error": "分析失败: <原因>"}` |
| 未登录 / Token 无效 | 401 | Result 结构（由依赖抛出） |

### 实现依赖

- 数据表：`records` / `categories`（`build_minimal_context` 组包本月与上月数据）；
- 外部服务：LLM（`get_analyze_llm`，Agnes 兼容 JSON mode，`response_format={"type":"json_object"}`）；
- 模块：`ai/analyze_chain.py`（`analyze_expense`）、`ai/context.py`（财务上下文组包）、Pydantic 校验模型 `ExpenseAnalysis`（06 §4.1）。

### 具体实现

```python
@ai.post("/analyze/expenses", summary="消费分析")
async def analyze_expenses(body: ExpenseAnalyzeIn, user: int = Depends(get_current_user),
                           db: AsyncSession = Depends(get_db)) -> Any:
    try:
        # 1) query = body.query or "请分析我的消费情况"
        # 2) current  = await build_minimal_context(db, user.id, 今年, 本月)
        # 3) previous = 上月上下文（默认始终传，见 06 §2 差异说明）
        # 4) data = await get_analyze_chain().analyze_expenses(query, current, previous)
        # 5) return {"success": True, "data": data.model_dump()}
        return {"success": True, "data": None}
    except Exception as e:
        return ai_error(f"分析失败: {e}")            # HTTP 200
```

---

## 6.10 预算规划

**接口**：`POST /api/ai/analyze/budget`　**登录**：是　**标签**：`ai`　**成功状态码**：`200`

**功能描述**：用户输入月收入（可选储蓄目标），生成下月分类预算方案。

**依赖注入**：`body: BudgetPlanIn`、`user: int = Depends(get_current_user)`、`db: AsyncSession = Depends(get_db)`；`response_model: None`（裸返回）。

### 请求体 `BudgetPlanIn`

| 字段 | JSON 键 | 类型 | 必填 | 默认值 | 含义与约束 |
|------|---------|------|------|--------|------------|
| monthly_income | monthlyIncome | number | 是 | — | 月收入。缺失 → `{"error":"缺少参数: monthlyIncome"}`；须 `> 0` |
| savings_goal | savingsGoal | number | 否 | `null` | 月储蓄目标；不传则按 50/30/20 法则推导 |

```json
{ "monthlyIncome": 15000, "savingsGoal": 3000 }
```

### 返回结果

```json
{
  "success": true,
  "data": {
    "monthly_budget": 12000.00,
    "category_limits": [
      { "category": "餐饮", "limit": 2500.00, "reason": "近三月均值上浮 10%" }
    ],
    "savings_target": 3000.00,
    "alerts": ["娱乐类目近两月超支风险较高"]
  }
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| data | object | `BudgetPlan` 结构（06 §4.1）。字段名 snake_case：`monthly_budget` / `category_limits` / `savings_target` / `alerts` |
| data.category_limits | array | 建议 5–8 个分类限额 |
| data.monthly_budget | number | 月预算总额 = 总收入 − 储蓄目标 |

### 错误场景

| 场景 | HTTP | 响应体 |
|------|------|--------|
| 缺 `monthlyIncome` | 200 | `{"error": "缺少参数: monthlyIncome"}` |
| LLM 失败 / 校验失败 | 200 | `{"error": "预算规划失败: <原因>"}` |
| 未登录 / Token 无效 | 401 | Result 结构（由依赖抛出） |

### 实现依赖

- 数据表：`records` / `categories`（`build_minimal_context` 组包）；
- 外部服务：LLM（同 6.9）；
- 模块：`ai/analyze_chain.py`（含 `plan_budget` 逻辑）、Pydantic 校验模型 `BudgetPlan`（06 §4.1）。

### 具体实现

```python
@ai.post("/analyze/budget", summary="预算规划")
async def analyze_budget(body: BudgetPlanIn, user: int = Depends(get_current_user),
                         db: AsyncSession = Depends(get_db)) -> Any:
    try:
        # 1) monthlyIncome 必填校验 -> return ai_error("缺少参数: monthlyIncome")
        # 2) ctx = await build_minimal_context(db, user.id, 今年, 本月)
        # 3) data = await get_analyze_chain().plan_budget(monthly_income, savings_goal, ctx)
        # 4) return {"success": True, "data": data.model_dump()}
        return {"success": True, "data": None}
    except Exception as e:
        return ai_error(f"预算规划失败: {e}")
```

---

## 6.11 FAQ 检索

**接口**：`GET /api/ai/faq/search`　**登录**：是　**标签**：`ai`　**成功状态码**：`200`

**功能描述**：AI 助手 FAQ 面板的语义检索；也是 ChatChain 的检索增强来源（阈值 0.5、topK 3）。

**依赖注入**：`user: int = Depends(get_current_user)`、`db: AsyncSession = Depends(get_db)`；`response_model: None`（裸返回）。

### 请求参数（query）

| 参数 | 类型 | 必填 | 默认值 | 含义与约束 |
|------|------|------|--------|------------|
| query | str | 是 | — | 检索词（**必填 query 参数**，非请求体） |

### 返回结果

```json
{
  "results": [
    { "id": 1, "question": "如何添加一笔消费记录？",
      "answer": "您可以直接对我说：「帮我记录一笔餐饮消费50元」...",
      "category": "记账操作", "score": 0.87 }
  ]
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| results | array | 命中结果，按 `score` 降序，最多 `faq_top_k`（默认 3）条 |
| results[].score | number | 余弦相似度，取值 `0~1`；**Embedding 不可用时自动降级为关键词检索，score 仍为 0~1 的数字**，响应**不含 `fallback` 标记** |

### 错误场景

| 场景 | HTTP | 响应体 |
|------|------|--------|
| **任何异常**（Embedding 不可用、DB 报错等） | 200 | `{"results": [], "fallback": true}` |
| 未登录 / Token 无效 | 401 | Result 结构（由依赖抛出） |

> ⚠️ 两种失败形态要区分：**正常检索无命中** → `{"results": []}`（无 `fallback` 键）；**检索过程抛异常** → `{"results": [], "fallback": true}`（含 `fallback`）。

### 实现依赖

- 数据表：`faq`；
- 外部服务：Embedding（不可用时自动降级为关键词检索）；
- 模块：`ai/faq_retriever.py`（`search_faq()`，余弦相似度 + 关键词降级）、`config/settings.py`（`FAQ_TOP_K`，默认 3）。
- 注：原骨架规划的向量索引文件 `data/faq_vectors.json` 为设计稿口径，实际实现见 `ai/faq_retriever.py`。

### 具体实现

```python
@ai.get("/faq/search", summary="FAQ 语义检索")
async def faq_search(query: str, user: int = Depends(get_current_user),
                     db: AsyncSession = Depends(get_db)) -> Any:
    try:
        # 1) results = await get_faq_retriever().search(query, get_settings().faq_top_k)
        # 2) return {"results": results}                  # 无 fallback 键
        return {"results": []}
    except Exception:
        return {"results": [], "fallback": True}          # 异常兜底
```

---

## 6.12 重建 FAQ 索引

**接口**：`POST /api/ai/faq/rebuild`　**登录**：是　**标签**：`ai`　**成功状态码**：`200`

**功能描述**：FAQ 知识库内容变更后，手动触发向量索引全量重建。

**依赖注入**：`user: int = Depends(get_current_user)`、`db: AsyncSession = Depends(get_db)`；`response_model: None`（裸返回）。

### 请求参数

无（无请求体、无 query）。

### 返回结果

```json
{ "success": true, "count": 8 }
```

| 字段 | 类型 | 说明 |
|------|------|------|
| count | int | 重建后的 FAQ 条目数（种子数据 8 条，02 §3.4） |

### 错误场景

| 场景 | HTTP | 响应体 |
|------|------|--------|
| 重建失败（Embedding 服务不可用等） | 200 | `{"error": "重建失败", "detail": "<原因>"}` |
| 未登录 / Token 无效 | 401 | Result 结构（由依赖抛出） |

### 实现依赖

- 数据表：`faq`；
- 外部服务：Embedding；
- 模块：`ai/faq_retriever.py`（向量重建：清空 → 重载 → 算向量 → 持久化）。

### 具体实现

```python
@ai.post("/faq/rebuild", summary="重建 FAQ 向量索引")
async def faq_rebuild(user: int = Depends(get_current_user),
                      db: AsyncSession = Depends(get_db)) -> Any:
    try:
        # 1) n = await get_faq_retriever().rebuild(db)   # 清空 -> 重载 -> 算向量 -> 持久化
        # 2) return {"success": True, "count": n}
        return {"success": True, "count": 0}
    except Exception as e:
        return {"error": "重建失败", "detail": str(e)}
```

---

## 6.13 保存反馈

**接口**：`POST /api/ai/feedback`　**登录**：是　**标签**：`ai`　**成功状态码**：`200`

**功能描述**：用户对某条 AI 回复点赞/点踩并留言，用于满意度统计（§6.14）。

**依赖注入**：`body: FeedbackIn`、`user: int = Depends(get_current_user)`、`db: AsyncSession = Depends(get_db)`；`response_model: None`（裸返回）。

### 请求体 `FeedbackIn`

| 字段 | JSON 键 | 类型 | 必填 | 默认值 | 含义与约束 |
|------|---------|------|------|--------|------------|
| message_id | messageId | str | 是 | — | 被评价的消息 ID（`msg_...`） |
| rating | rating | int | 是 | — | 评分，`TINYINT` 范围 `1–5` |
| comment | comment | str \| null | 否 | `null` | 文字反馈 |

```json
{ "messageId": "msg_1725700000456_q8w7e6", "rating": 5, "comment": "很好" }
```

### 返回结果

```json
{ "success": true }
```

### 错误场景

| 场景 | HTTP | 响应体 |
|------|------|--------|
| 写入失败 | 200 | `{"error": "保存失败"}` |
| 未登录 / Token 无效 | 401 | Result 结构（由依赖抛出） |

### 实现依赖

- 数据表：`feedback`；
- 模块：`schemas/ai.py`（`FeedbackIn`）。

### 具体实现

```python
@ai.post("/feedback", summary="保存反馈")
async def save_feedback(body: FeedbackIn, user: int = Depends(get_current_user),
                        db: AsyncSession = Depends(get_db)) -> Any:
    try:
        # 1) now_ms = int(time.time() * 1000)
        # 2) INSERT feedback(id=f"feedback_{now_ms}_{rand9}", message_id=body.message_id,
        #                    rating=body.rating, comment=body.comment, timestamp=now_ms)
        # 3) return {"success": True}
        return {"success": True}
    except Exception:
        return {"error": "保存失败"}
```

> TODO（需补充）：`feedback` 表（02 §3.3）**没有 `user_id` 列**，因此本接口无法按用户隔离反馈；如果后续要在管理端做「按用户看反馈」，需要给表加列并同步 02/08。

---

## 6.14 AI 会话统计

**接口**：`GET /api/ai/admin/stats`　**登录**：是（**注意：仅要求登录，非管理员**，差异表 #9；如需收紧改 `AdminDep`）　**标签**：`ai`　**成功状态码**：`200`

**功能描述**：管理侧展示 AI 模块使用情况的汇总数字。

**依赖注入**：`user: int = Depends(get_current_user)`、`db: AsyncSession = Depends(get_db)`；`response_model: None`（裸返回）。

### 请求参数

无。

### 返回结果

```json
{ "totalSessions": 12, "totalMessages": 340, "totalFeedback": 27, "averageRating": 4.3 }
```

| 字段 | 类型 | 说明 |
|------|------|------|
| totalSessions | int | 会话总数（**全量 COUNT，不含 `deleted_at` 过滤**，与列表接口口径不同） |
| totalMessages | int | 消息总数 |
| totalFeedback | int | 反馈总数 |
| averageRating | number | `AVG(rating)`，**无数据时返回 `0`**（不是 null） |

> TODO（需补充）：本接口是否应排除软删会话（`deleted_at > 0`），源码未明确。当前按「全量统计」实现，与 05 §4.4 一致；若产品要求排除，需同步改 05 与本表。

### 错误场景

| 场景 | HTTP | 响应体 |
|------|------|--------|
| 未登录 / Token 无效 | 401 | Result 结构（由依赖抛出） |

### 实现依赖

- 数据表：`sessions` / `messages` / `feedback`（三个 COUNT + 一个 AVG）。

### 具体实现

```python
@ai.get("/admin/stats", summary="AI 会话统计")
async def ai_admin_stats(user: int = Depends(get_current_user),
                         db: AsyncSession = Depends(get_db)) -> Any:
    # 1) SELECT COUNT(*) FROM sessions / messages / feedback
    # 2) SELECT AVG(rating) FROM feedback；NULL -> 0
    # 3) return {"totalSessions":.., "totalMessages":.., "totalFeedback":.., "averageRating":..}
    return {"totalSessions": 0, "totalMessages": 0, "totalFeedback": 0, "averageRating": 0}
```

---

## 6.15 自然语言记账

**接口**：`POST /api/ai/bookkeeping`　**登录**：是　**标签**：`ai`　**成功状态码**：`200`

**功能描述**：用户直接用一句口语化中文记账（如「我今天花79块吃了一顿烤肉」）。服务端做语义解析 → 字段归一化与校验 → 写入 `record` 表 → 回显确认卡。**这是本系统区别于普通记账应用的核心能力。**

**依赖注入**：`body: BookkeepingIn`、`user: int = Depends(get_current_user)`、`db: AsyncSession = Depends(get_db)`；`response_model: None`（裸返回；且存在四种 `action` 形态 + `{"error"}`，无法声明单一模型）。

> 契约详见 05 §6.0–§6.6；解析链 `BookkeepingChain` 见 06 §11；幂等日志表 `ai_bookkeeping_logs` 见 02 §3.5。

### 请求体 `BookkeepingIn`

| 字段 | JSON 键 | 类型 | 必填 | 默认值 | 含义与约束 |
|------|---------|------|------|--------|------------|
| message | message | str | 是 | — | 原始口语化文本。trim 后长度 1–500；空 →「缺少参数: message」 |
| session_id | sessionId | str \| null | 否 | `null` | AI 会话 ID。传入时把消息写入 `messages`，并维护「最近一笔」上下文（05 §6.4） |
| client_msg_id | clientMsgId | str \| null | 否 | `null` | 客户端 UUID，**强幂等键**；重发同一条消息必须带同一个值 |
| draft_id | draftId | int \| null | 否 | `null` | 追问续写：把本次内容补进指定草稿（`ai_bookkeeping_logs.id`） |
| dry_run | dryRun | bool | 否 | `false` | `true` = 只解析不入账，返回 `preview` |
| force | force | bool | 否 | `false` | `true` = 跳过 5 分钟弱幂等窗口，强制再记一笔 |
| now | now | str \| null | 否 | `null` | ISO datetime，覆盖服务端「今天」，仅联调/测试用 |

```json
{
  "sessionId": "session_1725969000000_ab12cd34x",
  "message": "我今天花79块吃了一顿烤肉",
  "clientMsgId": "8f2c1a10-4c7e-4a52-9f3b-2d6e0c9a7b41"
}
```

### 返回结果（四种 `action` 形态）

**① `action=created`（已入账，可能多笔）**

```json
{
  "action": "created",
  "requestId": "bk_1725969000123_x1y2z3",
  "records": [
    { "id": 128, "amount": 79.00, "type": 1, "categoryId": 3,
      "categoryName": "餐饮", "recordDate": "2026-09-10", "remark": "烤肉" }
  ],
  "totalAmount": 79.00,
  "echo": "已记下：餐饮 ¥79.00 · 今天(2026-09-10) · 备注「烤肉」· 记录 #128\n回复「改成45块」可修改，回复「删掉」可撤销。",
  "warnings": [],
  "errors": [],
  "sessionId": "session_1725969000000_ab12cd34x",
  "messageId": "msg_1725969000456_q8w7e6"
}
```

**② `action=clarify`（缺金额，追问而非猜测）**

```json
{
  "action": "clarify",
  "requestId": "bk_1725969000789_a1b2c3",
  "draftId": 1291,
  "question": "这笔消费的金额是多少？比如「35元」。",
  "missing": ["amount"],
  "preview": { "items": [ { "amount": null, "amountRaw": null, "type": 1,
      "categoryName": "餐饮", "categoryId": 3, "date": "2026-09-10",
      "dateExpr": "今天", "remark": "吃了顿烤肉", "confidence": 0.58 } ] },
  "records": []
}
```

**③ `action=ignored`（非消费类消息，不处理）**

```json
{
  "action": "ignored",
  "requestId": "bk_1725969000999_m4n5p6",
  "reason": "not_expense",
  "echo": "这不像一笔消费记录，我没有记账。想记账可以说「今天打车花了18块」。",
  "records": []
}
```

**④ `action=duplicate`（命中幂等，未重复入账）**

```json
{
  "action": "duplicate",
  "requestId": "bk_1725969000123_x1y2z3",
  "originRequestId": "bk_1725968999000_p0o9i8",
  "records": [ { "id": 128, "amount": 79.00, "categoryName": "餐饮",
                 "recordDate": "2026-09-10", "remark": "烤肉" } ],
  "echo": "这条我已经记过啦（#128 · 餐饮 ¥79.00），没有重复记账。",
  "hint": "如果确实要再记一笔，请重新发送并带上 force=true。"
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| action | string | `created` / `clarify` / `ignored` / `duplicate` —— 前端据此分支渲染 |
| requestId | string | 本次请求 ID，格式 `bk_{毫秒}_{随机}` |
| records | array | 入账明细。`records[].type` 为 **0=支出 / 1=收入**（`records.type` 语义，与 `category` 共用同一套 0/1） |
| totalAmount | number | 本次入账金额合计（多笔时） |
| echo | string | 服务端格式化好的回显文案，前端可直接渲染（模板见 05 §6.5） |
| warnings | array[string] | 兜底提示，如「未识别到明确分类，已归入「其他」」 |
| errors | array | 本次未入账的条目及原因；部分成功时非空 |
| draftId | int | 仅 `clarify` 返回，供下一次续写携带 |
| missing | array[string] | 仅 `clarify` 返回，缺失字段名，如 `["amount"]` |
| reason | string | 仅 `ignored` 返回：`not_expense` / `query` / `income_unsupported` / `too_ambiguous` / `no_recent_record` |

### 语义解析规则（摘要）

- **金额**：支持中文数字（`七十九块`→79.00）、小数、`块/元/块钱/¥/RMB`、千分位、`1万2`→12000.00；必须 `0 < amount ≤ 99999999.99`；**无法识别一律追问，不猜测**。
- **日期**：`今天/昨天/前天/大前天/本周三/上周三/上个月/3月5号/N天前` → 具体 `yyyy-MM-dd`；未指定年份且结果晚于今天则**年份 −1**；无时间词回落「今天」。
- **分类**：自定义分类优先于系统预设 → 别名词典（吃饭/外卖→餐饮；打车/地铁→交通…）→ 模糊包含 → 历史行为 → 兜底「其他」（**必带 warning**）。
- **多笔**：一条消息含多笔消费时**分别入账**，各返回独立 `id`；单条消息上限 **10 笔**。
- **幂等**：`clientMsgId` 强幂等（不过期）+ `SHA256(user_id|归一化文本)` 5 分钟窗口弱幂等；靠唯一键冲突兜底，**禁止"先 SELECT 再 INSERT"**。

### 错误场景

| 场景 | HTTP | 响应体 |
|------|------|--------|
| 缺 `message` 或 trim 后为空 | 200 | `{"error": "缺少参数: message"}` |
| `message` 超 500 字 | 200 | `{"error": "消息过长，最多 500 字"}` |
| `sessionId` 不存在 / 非本人 / 已删除 | 200 | `{"error": "会话不存在"}` |
| `draftId` 过期或不存在（> 30 分钟） | 200 | `{"error": "草稿已过期，请重新描述这笔消费"}` |
| 识别出的条目超过 10 笔 | 200 | `{"error": "一次最多识别 10 笔消费，请分开发送"}` |
| LLM 失败 / 输出无法校验 | 200 | `{"error": "记账解析失败，请换个说法再试"}` |
| 未登录 / Token 无效 | 401 | Result 结构（由依赖抛出） |

### 实现依赖

- 数据表：`record`（入账）、`ai_bookkeeping_logs`（幂等/草稿/审计，`models/bookkeeping.py` **已实现**）、`sessions` / `messages`（可选写会话）、`categories`（分类解析）；
- 外部服务：LLM（JSON mode，`ai/llm.py` 的 `get_analyze_llm()`）；
- 模块：解析链与归一化工具（`ai/bookkeeping_chain.py` / `ai/normalizers.py` / `ai/category_alias.py` 为 06 §11.7 规划文件，**尚未创建**）、`crud/ai.py`（幂等查询与日志读写）。

### 具体实现

```python
@ai.post("/bookkeeping", summary="自然语言记账")
async def bookkeeping(body: BookkeepingIn, user: int = Depends(get_current_user),
                      db: AsyncSession = Depends(get_db)) -> Any:
    # 1) message = (body.message or "").strip()；为空 -> ai_error("缺少参数: message")
    #    长度 > 500 -> ai_error("消息过长，最多 500 字")
    # 2) sessionId 非空时校验归属（user_id 匹配且 deleted_at=0）-> 否则 ai_error("会话不存在")
    # 3) 幂等：clientMsgId -> find_by_client_msg()；否则 dedup_hash + 300s 窗口 find_recent_by_dedup()
    #    命中 -> 反查首次 record_ids -> return {"action": "duplicate", ...}
    # 4) INSERT ai_bookkeeping_logs(request_id=f"bk_{ms}_{rand}") 拿 id；
    #    捕获 IntegrityError -> 回查首次 -> duplicate          # 禁止先 SELECT 再 INSERT
    # 5) parsed = await get_bookkeeping_chain().parse(message, today, category_names)
    #    LLM 失败 -> ai_error("记账解析失败，请换个说法再试")
    # 6) intent ∈ {query, chitchat} 或 not is_expense_related -> action="ignored"，日志 action='ignored'
    # 7) len(items) > 10 -> ai_error("一次最多识别 10 笔消费，请分开发送")
    #    逐条 normalize_amount / normalize_date / resolve_category（06 §11.3-11.5）
    # 8) dryRun -> 返回 preview（不写 record、不参与去重）
    #    全部 ok=False -> action="clarify" + draftId（日志 status=0）
    #    否则同一事务逐条 INSERT record -> action="created"
    # 9) 回写日志 record_ids / parse_json / action；格式化 echo（05 §6.5 模板）
    return {"action": "ignored", "records": []}
```

> ✅ 依赖已定稿：本接口依赖的 `records.status`（软删）与 `records.type`（**0=支出 / 1=收入**）均已包含在定稿表结构中，`sql/init_mysql.sql` 已建好。`ai_bookkeeping_logs` 的 ORM 模型 `models/bookkeeping.py` 已实现；⚠️ 解析链 `ai/bookkeeping_chain.py` 与归一化工具 `ai/normalizers.py` / `ai/category_alias.py` 仍为规划文件，实现本接口前需按 06 §11.7 补齐。

---

## 6.16 修改 AI 记账记录

**接口**：`PATCH /api/ai/bookkeeping/{id}`　**登录**：是　**标签**：`ai`　**成功状态码**：`200`

**功能描述**：用户对刚记下的那笔做修正——「改成45块」「备注改成AA」「分类换交通」。

**依赖注入**：`body: BookkeepingAmendIn`、`user: int = Depends(get_current_user)`、`db: AsyncSession = Depends(get_db)`；`response_model: None`（裸返回）。

### 路径参数

| 参数 | 类型 | 必填 | 含义与约束 |
|------|------|------|------------|
| id | int | 是 | 记录 ID（`record.id`），必须归属当前用户且未删除 |

### 请求体 `BookkeepingAmendIn`

**至少一项非空**；显式字段与 `message` 都给时，**以显式字段为准**。

| 字段 | JSON 键 | 类型 | 必填 | 默认值 | 含义与约束 |
|------|---------|------|------|--------|------------|
| amount | amount | number | 否 | `null` | 新金额，`> 0` 且 `≤ 99999999.99` |
| category_id | categoryId | int | 否 | `null` | 新分类，必须归属当前用户且 `type` 与原记录一致 |
| date | recordDate | str | 否 | `null` | 新日期，`yyyy-MM-dd` |
| remark | remark | str | 否 | `null` | 新备注，≤ 200 字，超出截断 |
| message | message | str | 否 | `null` | 自然语言修正指令，如「改成45块5，备注AA」 |

```json
{ "message": "改成45块5" }
```

### 返回结果

```json
{
  "success": true,
  "record": {
    "id": 128, "amount": 45.50, "type": 1, "categoryId": 3,
    "categoryName": "餐饮", "recordDate": "2026-09-10", "remark": "烤肉"
  },
  "changes": { "amount": { "from": 79.00, "to": 45.50 } },
  "echo": "已更新 #128：餐饮 ¥45.50（原 ¥79.00）· 2026-09-10 · 备注「烤肉」"
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| changes | object | **只列实际发生变动的字段**，值为 `{from, to}`；无变动时为 `{}` |

### 错误场景

| 场景 | HTTP | 响应体 |
|------|------|--------|
| 记录不存在 / 非本人 / 已删除 | 200 | `{"error": "记录不存在"}` |
| 金额非正或超上限 | 200 | `{"error": "金额必须大于0且不超过99999999.99"}` |
| 新分类不存在或归属不符 | 200 | `{"error": "分类不存在"}` |
| 请求体全空（无任何可改字段） | 200 | `{"error": "缺少修改内容"}` |
| 未登录 / Token 无效 | 401 | Result 结构（由依赖抛出） |

### 实现依赖

- 数据表：`record`（更新）、`ai_bookkeeping_logs`（追加 `action='amend'` 日志，`parent_id` 指向原记账日志）、`categories`（分类归属校验）；
- 外部服务：LLM（仅当 `message` 传入时，走 `BookkeepingChain.parse`）；
- 模块：`ai/bookkeeping_chain.py`、`ai/normalizers.py`。

### 具体实现

```python
@ai.patch("/bookkeeping/{record_id}", summary="修改 AI 记账记录")
async def amend_bookkeeping(record_id: int, body: BookkeepingAmendIn, user: int = Depends(get_current_user),
                            db: AsyncSession = Depends(get_db)) -> Any:
    # 1) SELECT * FROM records WHERE id=:record_id AND user_id=:uid [AND status=1]
    #    无行 -> ai_error("记录不存在")
    # 2) body.message 存在时走 BookkeepingChain.parse 取增量字段（显式字段优先覆盖）
    # 3) 校验 amount / categoryId 归属与 type 一致 / remark 截断 200
    # 4) UPDATE records ... ；追加日志 action='amend', parent_id=原记账日志
    # 5) changes 只列实际变动字段；拼 echo（05 §6.2）-> return {"success": True, ...}
    return {"success": False}
```

---

## 6.17 删除 AI 记账记录

**接口**：`DELETE /api/ai/bookkeeping/{id}`　**登录**：是　**标签**：`ai`　**成功状态码**：`200`

**功能描述**：用户对刚记下的那笔说「删掉刚才那笔」，撤销误记。

**依赖注入**：`user: int = Depends(get_current_user)`、`db: AsyncSession = Depends(get_db)`；`response_model: None`（裸返回）。

### 路径参数

| 参数 | 类型 | 必填 | 含义与约束 |
|------|------|------|------------|
| id | int | 是 | 记录 ID，必须归属当前用户且未删除 |

### 返回结果

```json
{ "success": true, "echo": "已删除 #128（餐饮 ¥79.00 · 2026-09-10）" }
```

### 错误场景

| 场景 | HTTP | 响应体 |
|------|------|--------|
| 记录不存在 / 非本人 / 已删除 | 200 | `{"error": "记录不存在"}` |
| 未登录 / Token 无效 | 401 | Result 结构（由依赖抛出） |

> 删除语义：**软删**（`record.status = 0`），与业务模块 `DELETE /api/records/{id}` 的物理删除不同。同时在 `ai_bookkeeping_logs` 追加 `action='delete'` 日志，并把原记账日志 `status` 置为 `2`（已回滚）。

### 实现依赖

- 数据表：`record`（软删，`status=0`）、`ai_bookkeeping_logs`（追加 `action='delete'`，原日志 `status=2`）。

### 具体实现

```python
@ai.delete("/bookkeeping/{record_id}", summary="删除 AI 记账记录")
async def delete_bookkeeping(record_id: int, user: int = Depends(get_current_user),
                             db: AsyncSession = Depends(get_db)) -> Any:
    # 1) 归属校验（user_id & status=1）-> 否则 ai_error("记录不存在")
    # 2) UPDATE records SET status=0 WHERE id=:record_id          # 软删
    # 3) 追加日志 action='delete'；原日志 status=2（已回滚）
    # 4) return {"success": True, "echo": "已删除 #128（餐饮 ¥79.00 · 2026-09-10）"}
    return {"success": False}
```

---
