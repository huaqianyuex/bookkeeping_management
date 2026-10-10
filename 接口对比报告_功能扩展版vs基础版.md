# FastAPI 后端接口差异对比报告：功能扩展版（项目 A） vs 基础版（项目 B）

## 1. 概述

| 项目 | 路径 | 说明 |
|---|---|---|
| 项目 A（功能扩展版） | `E:\一些毕设探索\Accounting Management System_fastapi\fast_backend -fwature-expansion-version` | 在 B 基础上扩展充值、语音识别、会员配额等能力 |
| 项目 B（基础版） | `E:\一些毕设探索\Accounting Management System_fastapi\fast_backend` | 基础记账系统 |

- 扫描时间：2026-10-08 23:22
- 扫描范围：`main.py` + `routers/` 目录全部路由定义（`@app.*` 与 `APIRouter`），已全项目 grep 交叉验证，无其他文件定义路由；静态资源挂载 `app.mount("/uploads", ...)` 非 API 路由，不计入
- 对比基准：**以项目 B 为基础**，按「HTTP 方法 + 完整路径」逐项匹配

### 接口总数对比

| 指标 | 数量 |
|---|---|
| 项目 A 总接口数 | **66** |
| 项目 B 总接口数 | **53** |
| 新增接口（仅 A 有） | **13** |
| 删除接口（仅 B 有） | **0** |
| 修改接口（方法/路径相同，实现或参数变化） | **17** |
| 保持不变接口 | **36** |
| 净增接口 | **+13** |

模块级数量对比：

| 模块（prefix） | B | A | 差异 |
|---|---|---|---|
| `/api/health`（main 直挂） | 1 | 1 | 相同 |
| `/api/user` | 6 | 6 | 2 修改 |
| `/api/categories` | 4 | 4 | 完全相同 |
| `/api/records` | 5 | 5 | 完全相同 |
| `/api/statistics` | 2 | 2 | 完全相同 |
| `/api/admin` | 12 | 12 | 1 修改 |
| `/api/ai` | 17 | 19 | 2 新增 + 8 修改 |
| `/api/membership` + `/api/admin/membership` | 6 | 6 | 6 修改 |
| `/api/recharge` + `/api/admin/recharges` | 0 | 11 | 11 新增（新模块） |
| **合计** | **53** | **66** | **+13** |

## 2. 新增接口明细表（仅项目 A 有，共 13 条）

| 方法 | 路径 | 函数名 | 文件 | 说明 |
|---|---|---|---|---|
| GET | `/api/recharge/plans` | `list_plans` | routers/recharge.py | 充值套餐目录 + 两档权益矩阵（服务端定价，前端禁止硬编码） |
| POST | `/api/recharge/orders` | `create_order` | routers/recharge.py | 创建充值订单：只收 planId，金额/天数服务端定价快照，频率与进行中订单幂等校验 |
| POST | `/api/recharge/orders/{order_no}/mock-pay` | `mock_pay` | routers/recharge.py | 模拟收银台支付：服务端生成签名事件，走与真实回调完全相同的验签/风控/审计路径 |
| POST | `/api/recharge/orders/{order_no}/cancel` | `cancel_order` | routers/recharge.py | 取消待支付订单（状态机校验） |
| GET | `/api/recharge/orders` | `list_my_orders` | routers/recharge.py | 我的充值订单分页（id 倒序，PageResult 结构） |
| GET | `/api/recharge/orders/{order_no}` | `get_order` | routers/recharge.py | 订单详情（归属校验在查询条件，跨用户一律 404） |
| POST | `/api/recharge/callback` | `payment_callback` | routers/recharge.py | 支付网关回调闸口（无鉴权，HMAC 验签→金额核对→行锁状态机→审计；签名无效 401） |
| GET | `/api/admin/recharges` | `admin_list_orders` | routers/recharge.py | 管理端订单分页 + 筛选（status/keyword；审批工作台按 status=1 过滤） |
| GET | `/api/admin/recharges/{order_id}/logs` | `admin_order_logs` | routers/recharge.py | 订单全链路审计轨迹时间线（append-only） |
| POST | `/api/admin/recharges/{order_id}/approve` | `admin_approve` | routers/recharge.py | 通过待审批订单：状态流转 + 审计 + 会员延期同一事务 |
| POST | `/api/admin/recharges/{order_id}/reject` | `admin_reject` | routers/recharge.py | 拒绝待审批订单：原因必填（schema 校验），写入 review_note + 审计留痕 |
| GET | `/api/ai/voice/config` | `voice_config` | routers/ai.py | 语音功能开关下发 `{enabled, maxSeconds}`，前端据此决定是否渲染话筒按钮 |
| POST | `/api/ai/voice/transcribe` | `voice_transcribe` | routers/ai.py | 语音转写：分档限流→扩展名白名单→分块读取限大小→魔数核对→ASR，返回 `{text, language, confidence}` |

## 3. 删除接口明细表（仅项目 B 有）

**无**。项目 B 的全部 53 条接口在项目 A 中均保留（36 条相同 + 17 条修改）。

## 4. 修改接口明细表（方法/路径相同，共 17 条）

| 方法 | 路径 | 函数名 | 文件 | 变化说明 |
|---|---|---|---|---|
| POST | `/api/user/login` | `login` | routers/user.py | 限流升级为**双桶**：原「IP+用户名」桶外新增纯 IP 全局兜底桶（防换用户名轮询爆破）；禁用账号登录失败也计入失败次数；`last_login_at` 改用 DB 时钟 `func.now()`（原为应用时钟） |
| GET | `/api/user/info` | `get_user_info` | routers/user.py | 返回体新增会员标识：`membership_tier` / `membership_expires_at`（查 user_membership 注入，过期惰性降级为免费） |
| GET | `/api/admin/users` | `list_users` | routers/admin.py | 返回体新增会员标识：行级 `member_map` 注入 `membership_tier` / `membership_expires_at` |
| POST | `/api/ai/chat` | `chat` | routers/ai.py | 新增**会员配额闸门**（`_quota_gate`，超额 429 + `QUOTA_EXCEEDED`）与**并发槽控制**（`ai_concurrency`，超限 429 + `CONCURRENCY_LIMIT`）；system prompt 重构为公共函数 `_build_system_prompt`（财务数据块 + 知识库块注入，FAQ 注入有开关）；按会员等级选择 premium 模型 |
| POST | `/api/ai/chat/stream` | `chat_stream` | routers/ai.py | 同上（配额 + 并发）；修复 SSE 流式期间复用已关闭 DB 会话的连接泄漏（生成器内单独建 `AsyncSessionLocal` 会话）；配额判定前移到 SSE 响应头发出之前 |
| POST | `/api/ai/analyze/expenses` | `analyze_expenses` | routers/ai.py | 新增配额闸门 + 并发控制；**修复 `body.query` 收而不传**的 bug（此前用户诉求被丢弃，现传入 analyze_chain） |
| POST | `/api/ai/analyze/budget` | `analyze_budget` | routers/ai.py | 新增配额闸门 + 并发控制 |
| GET | `/api/ai/faq/search` | `faq_search` | routers/ai.py | 改用 `search_faq_detailed`，返回体新增 **`mode`** 字段（`vector` 向量命中 / `keyword` 字符重合度降级 / `empty` 空查询）；top_k 不再硬编码 3，改读 `FAQ_TOP_K` 配置 |
| POST | `/api/ai/feedback` | `submit_feedback` | routers/ai.py | 仅实现微调：失败时补充异常日志（含 user_id / message_id） |
| POST | `/api/ai/bookkeeping` | `bookkeeping` | routers/ai.py | 大改：新增**会员配额闸门**（解析即计费）；请求体 `BookkeepingIn` 新增 `source`（text/voice）与 `overrides`（逐条确认覆盖）字段；分类解析过滤禁用分类（`status==1`）；收支类型由分类推导（不再默认收入）；override 归属/类型一致性校验；低置信条目（`BK_LOW_CONFIDENCE`）与归入「其他」的警告聚合去重；失败善后回写日志清理（`_bk_fail`）；缺「其他」分类时中止入账（防 NOT NULL 崩溃）；preview 返回体新增 `warnings` |
| PATCH | `/api/ai/bookkeeping/{record_id}` | `amend_bookkeeping` | routers/ai.py | 金额统一 `Decimal` 量化（修 float 写入 Numeric 的二进制精度垃圾）；分类解析过滤禁用分类；失败补充日志 |
| GET | `/api/membership/status` | `membership_status` | routers/membership.py | **由 TODO 骨架 → 完整实现**：返回会员等级、到期时间、今日用量、权益矩阵 |
| POST | `/api/membership/redeem` | `redeem` | routers/membership.py | **由 TODO 骨架 → 完整实现**：兑换码开通/续费，叠加语义（不覆盖已有会员期） |
| POST | `/api/admin/membership/codes` | `generate_codes` | routers/membership.py | **由 TODO 骨架 → 完整实现**：批量生成兑换码（1–500 张） |
| GET | `/api/admin/membership/codes` | `list_codes` | routers/membership.py | **由 TODO 骨架 → 完整实现**：兑换码分页列表 + status 筛选 |
| PUT | `/api/admin/membership/codes/{code_id}/void` | `void_code` | routers/membership.py | **由 TODO 骨架 → 完整实现**：作废兑换码（仅未使用可作废） |
| POST | `/api/admin/membership/grant` | `grant` | routers/membership.py | **由 TODO 骨架 → 完整实现**：管理员手动开通/延期会员（用户不存在返回 404） |

## 5. 完整接口对照表（按模块/前缀分组）

> 标注：🆕 新增（仅 A）| ✏️ 修改（实现/参数变化）| ＝ 保持不变

### 5.1 健康检查（main.py 直挂）

| 方法 | 路径 | 函数名 | A | B | 状态 |
|---|---|---|---|---|---|
| GET | `/api/health` | `health` | ✅ | ✅ | ＝ |

### 5.2 用户 `/api/user`（router，tags=["user"]）

| 方法 | 路径 | 函数名 | A | B | 状态 |
|---|---|---|---|---|---|
| POST | `/api/user/register` | `register` | ✅ | ✅ | ＝ |
| POST | `/api/user/login` | `login` | ✅ | ✅ | ✏️ 双桶限流、禁用账号计失败、DB 时钟 |
| GET | `/api/user/info` | `get_user_info` | ✅ | ✅ | ✏️ 注入会员标识 |
| PUT | `/api/user/info` | `update_user` | ✅ | ✅ | ＝ |
| PUT | `/api/user/password` | `change_password` | ✅ | ✅ | ＝ |
| POST | `/api/user/avatar` | `upload_avatar` | ✅ | ✅ | ＝ |

### 5.3 分类 `/api/categories`（router，tags=["category"]）

| 方法 | 路径 | 函数名 | A | B | 状态 |
|---|---|---|---|---|---|
| GET | `/api/categories` | `list_categories` | ✅ | ✅ | ＝ |
| POST | `/api/categories` | `create_category` | ✅ | ✅ | ＝ |
| PUT | `/api/categories/{category_id}` | `update_category` | ✅ | ✅ | ＝ |
| DELETE | `/api/categories/{category_id}` | `delete_category` | ✅ | ✅ | ＝ |

### 5.4 记账记录 `/api/records`（router，tags=["record"]）

| 方法 | 路径 | 函数名 | A | B | 状态 |
|---|---|---|---|---|---|
| GET | `/api/records` | `list_records` | ✅ | ✅ | ＝ |
| POST | `/api/records` | `create_record` | ✅ | ✅ | ＝ |
| GET | `/api/records/{record_id}` | `get_record` | ✅ | ✅ | ＝ |
| PUT | `/api/records/{record_id}` | `update_record` | ✅ | ✅ | ＝ |
| DELETE | `/api/records/{record_id}` | `delete_record` | ✅ | ✅ | ＝ |

### 5.5 统计 `/api/statistics`（router，tags=["statistics"]）

| 方法 | 路径 | 函数名 | A | B | 状态 |
|---|---|---|---|---|---|
| GET | `/api/statistics/monthly` | `get_summary` | ✅ | ✅ | ＝ |
| GET | `/api/statistics/category` | `get_category_stats` | ✅ | ✅ | ＝ |

### 5.6 管理端 `/api/admin`（router，tags=["admin"]）

| 方法 | 路径 | 函数名 | A | B | 状态 |
|---|---|---|---|---|---|
| GET | `/api/admin/users` | `list_users` | ✅ | ✅ | ✏️ 注入会员标识 |
| GET | `/api/admin/users/{user_id}` | `get_user_detail` | ✅ | ✅ | ＝ |
| PUT | `/api/admin/users/{user_id}/status` | `update_user_status` | ✅ | ✅ | ＝ |
| DELETE | `/api/admin/users/{user_id}` | `delete_user` | ✅ | ✅ | ＝ |
| POST | `/api/admin/users/batch-delete` | `batch_delete_users` | ✅ | ✅ | ＝ |
| GET | `/api/admin/records` | `list_records` | ✅ | ✅ | ＝ |
| POST | `/api/admin/records/batch-delete` | `batch_delete_records` | ✅ | ✅ | ＝ |
| GET | `/api/admin/statistics/overview` | `overview` | ✅ | ✅ | ＝ |
| GET | `/api/admin/faq` | `list_faq` | ✅ | ✅ | ＝ |
| POST | `/api/admin/faq` | `create_faq` | ✅ | ✅ | ＝ |
| PUT | `/api/admin/faq/{faq_id}` | `update_faq` | ✅ | ✅ | ＝ |
| DELETE | `/api/admin/faq/{faq_id}` | `delete_faq` | ✅ | ✅ | ＝ |

### 5.7 AI `/api/ai`（router，tags=["ai"]；裸 JSON 契约，非信封）

| 方法 | 路径 | 函数名 | A | B | 状态 |
|---|---|---|---|---|---|
| POST | `/api/ai/sessions` | `create_session` | ✅ | ✅ | ＝ |
| GET | `/api/ai/sessions` | `list_sessions` | ✅ | ✅ | ＝ |
| POST | `/api/ai/sessions/batch-delete` | `batch_delete_sessions` | ✅ | ✅ | ＝ |
| PATCH | `/api/ai/sessions/{session_id}` | `rename_session` | ✅ | ✅ | ＝ |
| DELETE | `/api/ai/sessions/{session_id}` | `delete_session` | ✅ | ✅ | ＝ |
| GET | `/api/ai/sessions/{session_id}/messages` | `session_messages` | ✅ | ✅ | ＝ |
| POST | `/api/ai/chat` | `chat` | ✅ | ✅ | ✏️ 配额 + 并发闸门、知识库注入、premium 模型 |
| POST | `/api/ai/chat/stream` | `chat_stream` | ✅ | ✅ | ✏️ 配额 + 并发闸门、独立流式 DB 会话 |
| POST | `/api/ai/analyze/expenses` | `analyze_expenses` | ✅ | ✅ | ✏️ 配额 + 并发闸门、修复 query 未传递 |
| POST | `/api/ai/analyze/budget` | `analyze_budget` | ✅ | ✅ | ✏️ 配额 + 并发闸门 |
| GET | `/api/ai/faq/search` | `faq_search` | ✅ | ✅ | ✏️ 返回 mode，top_k 读配置 |
| POST | `/api/ai/faq/rebuild` | `faq_rebuild` | ✅ | ✅ | ＝（函数体一致） |
| GET | `/api/ai/voice/config` | `voice_config` | ✅ | ❌ | 🆕 |
| POST | `/api/ai/voice/transcribe` | `voice_transcribe` | ✅ | ❌ | 🆕 |
| POST | `/api/ai/feedback` | `submit_feedback` | ✅ | ✅ | ✏️ 补充失败日志 |
| GET | `/api/ai/admin/stats` | `ai_admin_stats` | ✅ | ✅ | ＝ |
| POST | `/api/ai/bookkeeping` | `bookkeeping` | ✅ | ✅ | ✏️ 配额、source/overrides 参数、一致性校验、警告聚合 |
| PATCH | `/api/ai/bookkeeping/{record_id}` | `amend_bookkeeping` | ✅ | ✅ | ✏️ Decimal 精度、禁用分类过滤 |
| DELETE | `/api/ai/bookkeeping/{record_id}` | `delete_bookkeeping` | ✅ | ✅ | ＝ |

### 5.8 会员 `/api/membership` + `/api/admin/membership`（router + admin_router，tags=["membership"]）

| 方法 | 路径 | 函数名 | A | B | 状态 |
|---|---|---|---|---|---|
| GET | `/api/membership/status` | `membership_status` | ✅ | ✅ | ✏️ 骨架 → 完整实现 |
| POST | `/api/membership/redeem` | `redeem` | ✅ | ✅ | ✏️ 骨架 → 完整实现（叠加续费） |
| POST | `/api/admin/membership/codes` | `generate_codes` | ✅ | ✅ | ✏️ 骨架 → 完整实现（1–500 张） |
| GET | `/api/admin/membership/codes` | `list_codes` | ✅ | ✅ | ✏️ 骨架 → 完整实现（分页 + status 筛选） |
| PUT | `/api/admin/membership/codes/{code_id}/void` | `void_code` | ✅ | ✅ | ✏️ 骨架 → 完整实现（仅未使用可作废） |
| POST | `/api/admin/membership/grant` | `grant` | ✅ | ✅ | ✏️ 骨架 → 完整实现（用户不存在 404） |

### 5.9 充值 `/api/recharge` + `/api/admin/recharges`（router + admin_router，tags=["recharge"]；仅 A 有）

| 方法 | 路径 | 函数名 | A | B | 状态 |
|---|---|---|---|---|---|
| GET | `/api/recharge/plans` | `list_plans` | ✅ | ❌ | 🆕 |
| POST | `/api/recharge/orders` | `create_order` | ✅ | ❌ | 🆕 |
| POST | `/api/recharge/orders/{order_no}/mock-pay` | `mock_pay` | ✅ | ❌ | 🆕 |
| POST | `/api/recharge/orders/{order_no}/cancel` | `cancel_order` | ✅ | ❌ | 🆕 |
| GET | `/api/recharge/orders` | `list_my_orders` | ✅ | ❌ | 🆕 |
| GET | `/api/recharge/orders/{order_no}` | `get_order` | ✅ | ❌ | 🆕 |
| POST | `/api/recharge/callback` | `payment_callback` | ✅ | ❌ | 🆕 |
| GET | `/api/admin/recharges` | `admin_list_orders` | ✅ | ❌ | 🆕 |
| GET | `/api/admin/recharges/{order_id}/logs` | `admin_order_logs` | ✅ | ❌ | 🆕 |
| POST | `/api/admin/recharges/{order_id}/approve` | `admin_approve` | ✅ | ❌ | 🆕 |
| POST | `/api/admin/recharges/{order_id}/reject` | `admin_reject` | ✅ | ❌ | 🆕 |

## 6. 差异总结与结论

### 6.1 扩展方向

项目 A 相对项目 B 的全部差异集中在**三条主线**：

1. **商业化闭环（新增 recharge 模块，11 条接口）**：从「套餐目录 → 下单 → 模拟支付/回调 → 审批 → 审计」打通完整充值链路，含服务端定价、HMAC 验签闸口、状态机、风控、append-only 审计日志。会员体系（B 版仅为 TODO 骨架）同步落地为完整实现。
2. **AI 能力增强（ai 模块 2 新增 + 8 修改）**：新增语音输入（开关下发 + 语音转写，含魔数校验/限流等防滥用措施）；现有 AI 对话/分析/记账接口接入**会员配额闸门 + 并发控制**，实现付费墙与资源保护。
3. **会员标识贯通（user/admin 3 处修改）**：用户信息与用户列表接口注入 `membership_tier` / `membership_expires_at`，支撑前端会员态展示。

### 6.2 关键实现变化

- **配额计费语义**：chat 超额返回 HTTP 429（裸 JSON `QUOTA_EXCEEDED`），bookkeeping 超额返回 HTTP 200 + `error` 文案（前端契约不同，刻意区分）；配额在触达 LLM 前原子消耗（`consume_quota` 单语句校验+自增），失败不回滚（防刷量优先）。
- **并发保护**：新增 `ai_concurrency` 并发槽，超限 429 `CONCURRENCY_LIMIT`；先占槽后扣额度，避免并发满时白扣配额。
- **SSE 修复**：`chat/stream` 修复了 FastAPI 流式期间 DB 会话已关闭导致的连接泄漏，生成器内单独建会话。
- **记账健壮性**：`bookkeeping` 支持用户逐条确认（`overrides`）、类型由分类推导、警告聚合去重、失败善后清理脏日志、禁用分类不可被 AI 选中；`amend_bookkeeping` 修复金额浮点精度问题。
- **B 版存量缺陷修复**：`analyze/expenses` 的 `query` 参数此前收而不传（用户诉求被丢弃），A 版已修复。

### 6.3 兼容性结论

- **完全向后兼容**：B 版 53 条接口在 A 版全部保留（无删除），既有调用方无需改动路径与方法。
- **响应体有扩展**：5 处接口（user/login 行为、user/info、admin/users、ai/faq/search、ai/bookkeeping preview）返回体新增字段（会员标识、`mode`、`warnings`），为**追加式变更**，老前端兼容；`ai/faq/search` 的 `mode` 字段建议前端感知（区分向量分与重合度分的量纲）。
- **行为有收紧**：`user/login` 限流更严（新增 IP 兜底桶、禁用账号计失败）；`ai/chat` 等新增配额/并发上限——对免费用户是**新的限制**，前端需处理 429（`QUOTA_EXCEEDED` / `CONCURRENCY_LIMIT`）提示。
