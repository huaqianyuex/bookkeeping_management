# 智能个人记账管理系统（FastAPI 版）

![License](https://img.shields.io/badge/license-MIT-green)
![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-async-009688?logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=black)
![uni-app](https://img.shields.io/badge/uni--app-Vue%203-2B9939)
![MySQL](https://img.shields.io/badge/MySQL-8.0-4479A1?logo=mysql&logoColor=white)

一个前后端分离的个人记账管理系统，提供 **Web 端**、**移动端（uni-app）** 与 **FastAPI 后端** 三端完整实现，并集成 AI 能力：自然语言记账、智能对话、消费分析与预算规划。

> 本项目后端已由 Spring Boot 版本重构迁移至 FastAPI，历史版本可在 Git 提交记录中查看。

## 项目定位

- **个人 / 家庭自部署记账**：数据完全自持（自有 MySQL），不依赖第三方 SaaS；AI 助手基于你自己的真实账单回答问题，而不是通用话术。
- **全栈与 AI 应用教学参考**：三端 + 分层后端 + LLM 应用链（结构化输出 / 流式 SSE / RAG 检索 / 幂等去重）的完整可运行样例。
- 与市面记账工具的差异：AI 自然语言记账支持澄清追问与幂等去重，对话直连数据库实时数据，且整套系统可以私有化部署与二次开发。

## 效果预览

| 概览 | 账单 |
| --- | --- |
| ![概览](docs/screenshots/dashboard.png) | ![账单](docs/screenshots/records.png) |
| **AI 助手** | **记账** |
| ![AI 助手](docs/screenshots/ai-chat.png) | ![记账](docs/screenshots/add-edit.png) |

## 项目简介

- **fast_backend**：基于 FastAPI 的异步后端服务，使用 SQLAlchemy 2.0（asyncio）+ MySQL 8，内置 JWT 鉴权、统一响应格式与全局异常处理，并通过 OpenAI 兼容接口接入大模型（对话 / 分析 / Embedding 检索）。
- **fast_backend -fwature-expansion-version**：功能演进版后端，在 fast_backend 之上补齐**会员体系（兑换码 / 管理员开通 / AI 配额闸门）、会员充值与安全审批（模拟支付网关 + 风险分层人工审批 + 审计留痕）、语音记账（STT）**等完整实现；体验全部功能请运行本版本（fast_backend 为保持简洁的对照骨架版，会员路由为 TODO 占位）。
- **personal-ledger-frontend**：基于 React 18 + Vite + Ant Design 5 的 Web 端，覆盖普通用户的记账流程与管理员后台。
- **personal-ledger-uniapp**：基于 uni-app（Vue 3 语法）的移动端，一套代码可运行于 H5、App 与微信小程序。

## 核心功能

### 用户与账户
- 用户注册、登录（JWT 令牌鉴权）
- 个人资料查看与修改、修改密码、头像上传

### 记账与分类
- 账单的新增、修改、删除、详情查看与分页查询
- 收支分类管理：系统预设 16 个常用分类，支持自定义增删改

### 统计报表
- 月度收支汇总统计
- 分类维度的收支统计

### AI 智能记账与助手（需配置 API Key）
- **自然语言记账**：如「早餐花了 15 元」即可完成记账，支持对刚记的记录继续「修改 / 删除」
- **AI 对话**：多会话管理、SSE 流式对话、会话历史记录；对话已实时接入账单数据（自动查询当月收支、环比与分类构成），可直接询问「本月花了多少」「分析我的消费」并得到基于真实数据的回答
- **消费分析 / 预算规划**：基于账单数据的智能分析
- **FAQ 语义检索**：基于 Embedding 的常见问题检索，支持消息点赞 / 点踩反馈
- **语音记账**（扩展版后端）：录音转文字（STT）后走语义记账链路

### 会员体系与充值
- **会员档位**：免费版 / 会员两档，AI 对话、账单分析、AI 记账按档位分配每日额度；额度用尽时明确提示并引导充值
- **充值购买**：套餐直购（月卡 / 季卡 / 年卡），服务端唯一定价、模拟支付网关（HMAC 验签回调，无商户资质要求）；大额或异常交易自动转入人工审批，管理员在 Web 端终审，订单状态机 + 全链路审计留痕
- **兑换码**：管理员按批次批量生成，用户在会员中心核销开通 / 续费，未到期续费天数自动叠加、不损失剩余天数
- **充值记录**：用户端充值记录页（状态 / 金额 / 拒绝原因）；运营方案见 [docs/membership-code-operation-plan.md](docs/membership-code-operation-plan.md)

### 管理员后台（Web 端）
- 用户管理：列表、详情、启用 / 禁用、删除、批量删除
- 账单管理：全量账单列表、批量删除
- 会员管理：兑换码批量生成与作废、手动开通 / 延期会员
- 充值审批：风控拦截订单的人工终审工作台（通过 / 拒绝、审计轨迹时间线）
- 系统概览统计与 AI 会话统计

## 技术栈

| 层次 | 技术 |
| --- | --- |
| 后端 | Python 3.10+、FastAPI、SQLAlchemy 2.0（asyncio）+ aiomysql、Pydantic v2、PyJWT + bcrypt |
| Web 前端 | React 18、Vite 5、Ant Design 5、React Router 6、Axios、dayjs |
| 移动端 | uni-app（Vue 3 语法）、Vite、Pinia、SCSS，支持 H5 / App / 微信小程序 |
| 数据库 | MySQL 8.0（InnoDB、utf8mb4、金额统一 DECIMAL(10,2)） |
| AI 能力 | OpenAI 兼容接口（默认 Agnes AI），对话模型 / 分析模型 / Embedding 模型 |

## 环境要求

- Python ≥ 3.10
- Node.js ≥ 16（推荐 18 LTS）
- MySQL ≥ 8.0
- （可选）OpenAI 兼容的大模型 API Key，用于 AI 功能
- （可选）HBuilderX / 微信开发者工具，用于移动端 App 与小程序调试

## 安装与运行方式

### 1. 克隆仓库

```bash
git clone https://gitee.com/hechao_2024/accounting-management-system.git
cd accounting-management-system
```

### 2. 初始化数据库

使用 MySQL 8 执行初始化脚本（建库 `bookkeeping_fastapi`、14 张业务表（业务 / AI / 会员 / 充值）、默认管理员与预设分类，脚本可重复执行）：

```bash
mysql -u root -p < sql/init_mysql.sql
```

### 3. 启动后端（端口 8000）

```bash
# 功能完整的扩展版后端（会员 / 充值 / 语音记账，前端两端默认联调此版本）：
cd "fast_backend -fwature-expansion-version"
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# 或运行对照骨架版（会员路由为 TODO 占位）：
cd fast_backend
uvicorn main:app --reload
```

- 服务地址：<http://localhost:8000>
- 接口文档（Swagger）：<http://localhost:8000/docs>
- 健康检查：`GET /api/health`

首次运行前请在对应后端目录下创建 `.env` 配置文件（该文件不入库），可参考：

```dotenv
# 数据库（改成你的 MySQL 账号密码）
DATABASE_URL=mysql+aiomysql://root:change-me@localhost:3306/bookkeeping_fastapi?charset=utf8mb4

# 服务
APP_HOST=0.0.0.0
CORS_ORIGINS=http://localhost:5173,http://localhost:5174

# SQL 回显（调试用，默认关闭；开启后 SQLAlchemy 会把 SQL 连同参数打进控制台）
SQL_ECHO=false

# JWT（上线前务必更换为随机字符串）
JWT_SECRET=please-generate-a-random-32-char-secret
JWT_EXPIRE_SECONDS=86400

# AI（可选；不配置则仅 AI 相关功能不可用，其余功能不受影响）
AGNES_API_KEY=
OPENAI_BASE_URL=https://apihub.agnes-ai.com/v1
CHAT_MODEL=agnes-2.5-flash
ANALYZE_MODEL=agnes-2.0-flash
EMBEDDING_MODEL=text-embedding-3-small

# 以下为扩展版后端可选配置（缺省即用代码默认值）
# 充值回调 HMAC 密钥（不配置则从 JWT_SECRET 派生；生产建议显式设置独立随机值）
# RECHARGE_CALLBACK_SECRET=
# 单笔/当日累计人工审批阈值（元）
# RECHARGE_MANUAL_REVIEW_AMOUNT=100
# RECHARGE_DAILY_REVIEW_AMOUNT=200
```

### 4. 启动 Web 前端（端口 5173）

```bash
cd personal-ledger-frontend
npm install
npm run dev
```

访问 <http://localhost:5173>，`/api` 与 `/uploads` 请求已由 Vite 代理转发至后端 `http://localhost:8000`。

### 5. 运行移动端（uni-app）

```bash
cd personal-ledger-uniapp
npm install
npm run dev:h5        # H5 版（端口 5174，/api 同样代理到 8000）
# npm run dev:app     # App 版
# npm run dev:mp-weixin   # 微信小程序版
```

**真机 / 模拟器调试**：需将 `personal-ledger-uniapp/src/api/config.js` 中非 H5 平台的 `BASE_URL` 改为电脑的局域网 IP（如 `http://192.168.x.x:8000/api`），并保证手机与电脑在同一 WiFi 下。

### 6. 运行测试（后端）

```bash
cd "fast_backend -fwature-expansion-version"
pip install -r requirements-dev.txt
pytest    # 扩展版：406 个用例（含会员、充值安全审批模块）

cd ../fast_backend && pytest    # 主后端骨架版
```

### 7. 一键部署（Docker Compose）

```bash
cp .env.example .env    # 至少设置 JWT_SECRET（≥32 位随机字符串）与 MYSQL_ROOT_PASSWORD
docker compose up -d --build
```

- 首次启动自动执行 `sql/init_mysql.sql` 完成建库建表与种子数据；Web 端访问 <http://localhost:5173>，后端 API 与 Swagger 在 <http://localhost:8000>。
- 传统部署建议：Nginx 反向代理 + systemd 托管 uvicorn + 每日 `mysqldump` 备份；生产环境务必更换默认密码与 JWT_SECRET，并启用 HTTPS。

**移动端设计体系**：移动端采用「纸面结算 × 行情看板」视觉体系（暖纸白底、墨黑正文、琥珀强调色、发丝线分区、Saira 等宽数字字体），完整设计规范见 [personal-ledger-uniapp/DESIGN.md](personal-ledger-uniapp/DESIGN.md)，产品定位与约束见 [PRODUCT.md](personal-ledger-uniapp/PRODUCT.md)。

## 目录结构

```
accounting-management-system/
├── fast_backend/                       # FastAPI 后端服务（对照骨架版）
│   ├── main.py                         # 应用入口：CORS、静态资源、路由挂载
│   ├── config/                         # settings.py（读取 .env）、db_config.py（异步引擎与会话）
│   ├── models/                         # SQLAlchemy ORM 模型
│   ├── schemas/                        # Pydantic 请求 / 响应模型
│   ├── crud/                           # 数据访问层
│   ├── routers/                        # 路由：user / category / record / statistics / admin / ai / membership
│   ├── ai/                             # AI 模块：对话链、消费分析、FAQ 检索、会话记忆
│   ├── tasks/                          # 定时任务（如过期待清理）
│   ├── utils/                          # JWT 鉴权、统一响应、异常处理、文件上传
│   ├── uploads/                        # 运行时头像存储（不入库，自动创建）
│   └── requirements.txt
├── fast_backend -fwature-expansion-version/  # 功能演进版后端（推荐运行）
│   └── ...                             # 在骨架版之上实现：会员体系、充值与安全审批、语音转写（STT）
│   ├── models/recharge.py              # 充值订单 / 审计日志表
│   ├── routers/recharge.py             # 用户侧 + 回调闸口 + 管理侧审批
│   └── utils/recharge_security.py      # 支付回调 HMAC 验签
├── personal-ledger-frontend/           # Web 端（React 18 + Vite + Ant Design 5）
│   └── src/
│       ├── api/                        # 按模块封装的接口调用
│       ├── components/                 # MainLayout、AdminRoute（管理员路由守卫）等
│       ├── context/                    # 登录态管理
│       └── pages/                      # Dashboard / Records / Membership / AiChat / admin/AdminUsers、AdminRecharges 等
├── personal-ledger-uniapp/             # 移动端（uni-app + Vue 3）
│   ├── PRODUCT.md                      # 产品定位与约束（impeccable 设计流程用）
│   ├── DESIGN.md                       # 设计系统规范（配色 / 字体 / 组件）
│   └── src/
│       ├── api/                        # 请求封装与后端地址配置（config.js）
│       ├── components/                 # RecordCard、TabBar、AppIcon（自绘 SVG 图标）等
│       ├── pages/                      # 概览 / 账单 / 记账 / 分类 / 我的 / AI 助手 / 会员中心 / 充值记录
│       ├── static/fonts/               # Saira 数字字体（App / H5 端加载）
│       ├── utils/                      # 金额格式化、分类色板、JWT 解析、状态缓存
│       └── styles/                     # 主题令牌与动画样式
├── sql/
│   ├── init_mysql.sql                  # 建库建表 + 种子数据（14 表，可重复执行）
│   ├── create_tables_from_models.sql   # 按 ORM 模型生成的建表脚本
│   └── upgrade_add_abk_source.sql      # 增量升级脚本示例
├── docs/                               # 设计文档与效果预览截图
│   ├── membership-plan.md              # 会员体系设计（兑换码 / 配额闸门）
│   ├── membership-code-operation-plan.md # 兑换码运营方案（分发 / 防刷 / 追踪 / 风控）
│   └── fastapi-backend/                # 编号后端文档（04 接口规范、11 充值与审批等）
├── 记账App设计稿/                       # UI 设计稿
├── docker-compose.yml                  # 一键部署：MySQL + 后端 + Web 端
├── .env.example                        # 环境变量模板（复制为 .env 使用）
└── 开题报告/                            # 毕业设计开题报告
```

## 使用说明

1. **启动顺序**：MySQL → 后端（`uvicorn main:app --reload`）→ Web 前端 / 移动端。
2. **默认管理员**：初始化脚本内置管理员账号 `admin` / `123456`（BCrypt 加密存储），登录 Web 端后可见管理后台入口；**上线前务必修改密码**。
3. **普通用户流程**：注册账号 → 登录 → 在「记账」页新增收支记录（手动填写或使用 AI 自然语言记账）→ 在「分类」页管理自定义分类 → 在「首页 / 统计」查看月度收支与分类统计。
4. **AI 记账**：在 AI 对话页直接输入「早餐花了 15 元」「把刚才那笔改成 20 元」「删掉刚才那笔」即可完成记账操作；也可发起自由对话、请求「分析一下我本月的消费」或「帮我做一份预算规划」。
5. **管理员操作**：使用 `admin` 账号登录 Web 端，左侧导航会出现「用户管理 / 账单管理 / 系统概览 / FAQ 管理 / 会员管理 / 充值审批」等入口，可对全平台用户、账单与会员进行管理。
6. **会员与充值**：在移动端或 Web 端「会员中心」查看当前档位与今日剩余额度；选择套餐经模拟支付开通 / 续费（演示环境无真实资金，大额订单需管理员在「充值审批」通过后到账）；也可使用管理员发放的兑换码核销。
7. **接口调试**：启动后端后访问 Swagger 页面（<http://localhost:8000/docs>）；AI 模块的链路与数据流说明见 `fast_backend -fwature-expansion-version/docs/AI模块讲解.md`，充值模块设计见 [docs/fastapi-backend/11-充值与审批模块.md](docs/fastapi-backend/11-充值与审批模块.md)。

## 注意事项

- **端口一致性**：后端实际监听端口由 uvicorn 启动参数决定（默认 `8000`）。若修改端口，需同步修改 `personal-ledger-frontend/vite.config.js` 与 `personal-ledger-uniapp/vite.config.js` 中的代理目标地址，以及移动端 `src/api/config.js` 中的 `BASE_URL`。
- **敏感信息**：`.env` 文件（含数据库密码、JWT 密钥、AI API Key）已加入 `.gitignore`，不会随仓库提交；克隆后需按上文模板自行创建。提交前建议启用 gitleaks 敏感信息扫描钩子（见 [CONTRIBUTING](CONTRIBUTING.md)）。
- **默认凭据**：数据库连接示例中的 `root/change-me` 与默认管理员密码 `123456` 仅为本地开发演示，部署前请全部修改；`JWT_SECRET` 上线前务必更换。
- **角色字段约束**：`users.role` 为 `TINYINT`（0 = 普通用户，1 = 管理员），前端 `AdminRoute.jsx`、`MainLayout.jsx` 依赖该数值判断权限，请勿改为字符串类型。
- **金额精度**：金额字段统一使用 `DECIMAL(10,2)`，请勿改为 FLOAT / DOUBLE。
- **移动端真机调试**：手机与电脑需在同一局域网；若请求失败，可参考 `personal-ledger-uniapp/安卓运行排查指南.md` 排查（如安卓明文 HTTP 限制）。
- **AI 功能可选**：未配置 `AGNES_API_KEY` 时，仅 AI 相关接口不可用，记账、统计、管理等其余功能均可正常使用。
- **支付为模拟实现**：充值使用内置模拟支付网关（HMAC 验签回调），无真实资金、无需商户资质；真实渠道（支付宝沙箱等）接入点见 [docs/fastapi-backend/11-充值与审批模块.md](docs/fastapi-backend/11-充值与审批模块.md)。
- **会员 / 充值为扩展版后端能力**：主后端 `fast_backend` 的会员路由为骨架占位，体验完整功能请运行 `fast_backend -fwature-expansion-version`（限流 / 并发控制为进程内实现，单 worker 部署前提）。
- **数据库脚本幂等**：`sql/init_mysql.sql` 使用 `CREATE IF NOT EXISTS` + `ON DUPLICATE KEY UPDATE`，可重复执行；请勿调整其中建表的依赖顺序。
- **已知限制**：移动端依赖 `@dcloudio/*` 的 alpha 通道版本（已锁定精确版本号，升级请整组评估）；微信小程序端仅有空壳配置，尚未实际接入。
