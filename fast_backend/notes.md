# Notes: 后端安全整改方案

## Sources
### `docs/后端安全分析报告.md`
- 18 项去重发现：H1-H2、M1-M7、L1-L9。
- 最高风险集中在 6 位 PIN 登录爆破、AI 成本滥用、JWT 无法撤销。
- M7、L8 仍标记为 unconfirmed，报告主要来自静态分析。

### `docs/后端安全修复计划.md`
- 已有 v1 计划，但固定假设“保留 6 位 PIN”和“单 worker 内存限流”，与真实部署约束尚未确认。
- 需要复核其中具体实现建议，尤其是账号枚举、限流键、并发计数、MySQL 锁与 JWT 迁移方案。
- 当前计划未逐项提供 1-3 个方案、量化验证指标和完整责任矩阵。

## Verified Findings
- H1 成立，但攻击条件依赖真实客户端 IP 解析；6 位 PIN 是前后端共同契约，不能只改后端正则。
- M1 仅“改密/登出后旧 token 有效”成立；禁用和删除已被每次鉴权回查用户状态/存在性阻断。
- M2 成立；固定可预测的“开发密钥”也不可作为生产逃生方案，生产必须 fail-closed。
- M3/M4 的代码事实成立，但实际弱连接串和日志落盘仍需部署侧确认。
- L2 成立；登录未知用户跳过 bcrypt 也产生时序枚举信号。假成功注册需要同步修改两个前端。
- L3 的无限流和预检查竞态成立；唯一键冲突已由全局异常处理器转为 400，并非未捕获 500。
- H2 成立，但 `/sessions` 不产生 LLM 成本；还漏了 `/faq/rebuild` 和携带 message 的 bookkeeping PATCH。
- M5 机制存在，但当前无工具/跨用户权限，建议降为低危模型鲁棒性；未来接工具时升级。
- M6 成立；普通 AsyncSession + 多次 commit 不能安全承载 MySQL advisory lock，锁名还会超长。
- M7 应拆为活跃会话无上限、列表大 OFFSET、消息接口无分页三部分。
- L8 实际成立；L6 不只是范围问题，还存在 Record.type 与 Category.type 不一致。
- FAQ 实际位于 `schemas/admin.py`；上传只验魔数也不完整，应实际解码、限制像素并重编码。
- `requirements.txt` 使用宽松 `>=`，且直接使用的 LangChain 依赖被注释；当前没有可复现安装链。

## Recommended Decisions
- H1：同步升级密码策略；规范化用户名后做账号维度和可信 IP 维度原子限流；失败触发验证码/退避。
- H2：按端点成本权重做用户日配额、分钟速率、用户/全局并发；SSE 在 `finally` 释放；供应商设置硬预算。
- M1：`users.token_version` 为推荐最小方案；强制旧 token 在维护窗口失效；`user_token` 用于未来按设备登出与审计。
- M6：非 dry-run 强制 `clientMsgId`；记录 pending/succeeded/failed 和请求哈希；内容唯一约束仅用于短 TTL 预留表，不直接约束 records。
- L9：若生产多 worker，限流/配额使用 Redis；单 worker 内存方案只作为明确标注的临时部署。
- 工程门禁：锁依赖、pytest、ruff/mypy 基线、bandit、pip-audit、数据库迁移和 mock LLM 测试。

## File-Level Implementation Notes
- 认证配置涉及 `config/settings.py`、`config/db_config.py`、`main.py`；生产必须 fail-closed，开发不能用公开固定密钥。
- 用户链路涉及 `schemas/users.py`、`routers/user.py`、`crud/user.py`、`utils/security.py`、`utils/auth.py`、`utils/throttle.py`、`utils/exception.py`、`models/user.py`。
- AI 路由不能独自承担配额和幂等；需把 LLM factory、history、FAQ、bookkeeping 状态机分别下沉到 `ai/` 和新增 service/guard。
- `routers/ai.py` 的 SSE 必须在生成器 `finally` 释放并发租约；bookkeeping 不使用普通 AsyncSession 跨 commit 持有 GET_LOCK。
- L6 的安全修复是“Record.type 从分类推导 + 分类 type 创建后不可变 + DB 值域 CHECK”，仅加 ge/le 不足。
- 上传安全需要实际解码、像素限制和重编码，magic bytes 仅作为快速预检。
- `tasks/purge.py` 当前为空桩；需要 scheduler + purge service + lifespan 接线，且不得物理删除软删财务记录。
- `models/bookkeeping.py` 已有 `(user_id, client_msg_id)` 唯一键，优先新增独立幂等状态表，不应把审计表继续扩成混合状态机。
- `_test_monthly_api.py` 和 `_verify_stats.py` 不是可靠门禁，测试内容应迁入标准 pytest；删除旧脚本需另行批准。
