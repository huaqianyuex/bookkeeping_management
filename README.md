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

### 管理员后台（Web 端）
- 用户管理：列表、详情、启用 / 禁用、删除、批量删除
- 账单管理：全量账单列表、批量删除
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

使用 MySQL 8 执行初始化脚本（建库 `bookkeeping_fastapi`、9 张业务表、默认管理员与预设分类，脚本可重复执行）：

```bash
mysql -u root -p < sql/init_mysql.sql
```

### 3. 启动后端（端口 8000）

```bash
cd fast_backend
pip install -r requirements.txt
uvicorn main:app --reload
```

- 服务地址：<http://localhost:8000>
- 接口文档（Swagger）：<http://localhost:8000/docs>
- 健康检查：`GET /api/health`

首次运行前请在 `fast_backend/` 下创建 `.env` 配置文件（该文件不入库），可参考：

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
cd fast_backend
pip install -r requirements-dev.txt
pytest
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
├── fast_backend/                  # FastAPI 后端服务
│   ├── main.py                    # 应用入口：CORS、静态资源、路由挂载
│   ├── config/                    # settings.py（读取 .env）、db_config.py（异步引擎与会话）
│   ├── models/                    # SQLAlchemy ORM 模型
│   ├── schemas/                   # Pydantic 请求 / 响应模型
│   ├── crud/                      # 数据访问层
│   ├── routers/                   # 路由：user / category / record / statistics / admin / ai
│   ├── ai/                        # AI 模块：对话链、消费分析、FAQ 检索、会话记忆
│   ├── tasks/                     # 定时任务（如过期待清理）
│   ├── utils/                     # JWT 鉴权、统一响应、异常处理、文件上传
│   ├── uploads/                   # 运行时头像存储（不入库，自动创建）
│   └── requirements.txt
├── personal-ledger-frontend/      # Web 端（React 18 + Vite + Ant Design 5）
│   └── src/
│       ├── api/                   # 按模块封装的接口调用
│       ├── components/            # MainLayout、AdminRoute（管理员路由守卫）等
│       ├── context/               # 登录态管理
│       └── pages/                 # Dashboard / Records / AiChat / AdminUsers / AdminRecords 等
├── personal-ledger-uniapp/        # 移动端（uni-app + Vue 3）
│   ├── PRODUCT.md                 # 产品定位与约束（impeccable 设计流程用）
│   ├── DESIGN.md                  # 设计系统规范（配色 / 字体 / 组件）
│   └── src/
│       ├── api/                   # 请求封装与后端地址配置（config.js）
│       ├── components/            # RecordCard、TabBar、AppIcon（自绘 SVG 图标）等
│       ├── pages/                 # 首页 / 账单 / 记账编辑 / 分类 / 我的 / AI 对话 / AI 历史
│       ├── static/fonts/          # Saira 数字字体（App / H5 端加载）
│       ├── utils/                 # 金额格式化、分类功能色板、状态缓存
│       └── styles/                # 主题令牌与动画样式
├── sql/
│   ├── init_mysql.sql             # 建库建表 + 种子数据（可重复执行）
│   └── create_tables_from_models.sql
├── docs/                          # 设计文档与效果预览截图（screenshots/）
├── 记账App设计稿/                  # UI 设计稿
├── docker-compose.yml             # 一键部署：MySQL + 后端 + Web 端
├── .env.example                   # 环境变量模板（复制为 .env 使用）
└── 开题报告/                       # 毕业设计开题报告
```

## 使用说明

1. **启动顺序**：MySQL → 后端（`uvicorn main:app --reload`）→ Web 前端 / 移动端。
2. **默认管理员**：初始化脚本内置管理员账号 `admin` / `123456`（BCrypt 加密存储），登录 Web 端后可见管理后台入口；**上线前务必修改密码**。
3. **普通用户流程**：注册账号 → 登录 → 在「记账」页新增收支记录（手动填写或使用 AI 自然语言记账）→ 在「分类」页管理自定义分类 → 在「首页 / 统计」查看月度收支与分类统计。
4. **AI 记账**：在 AI 对话页直接输入「早餐花了 15 元」「把刚才那笔改成 20 元」「删掉刚才那笔」即可完成记账操作；也可发起自由对话、请求「分析一下我本月的消费」或「帮我做一份预算规划」。
5. **管理员操作**：使用 `admin` 账号登录 Web 端，左侧导航会出现「用户管理 / 账单管理 / 系统概览」等入口，可对全平台用户与账单进行管理。
6. **接口调试**：启动后端后访问 Swagger 页面（<http://localhost:8000/docs>）；AI 模块的链路与数据流说明见 `fast_backend/docs/AI模块讲解.md`。

## 注意事项

- **端口一致性**：后端实际监听端口由 uvicorn 启动参数决定（默认 `8000`）。若修改端口，需同步修改 `personal-ledger-frontend/vite.config.js` 与 `personal-ledger-uniapp/vite.config.js` 中的代理目标地址，以及移动端 `src/api/config.js` 中的 `BASE_URL`。
- **敏感信息**：`.env` 文件（含数据库密码、JWT 密钥、AI API Key）已加入 `.gitignore`，不会随仓库提交；克隆后需按上文模板自行创建。提交前建议启用 gitleaks 敏感信息扫描钩子（见 [CONTRIBUTING](CONTRIBUTING.md)）。
- **默认凭据**：数据库连接示例中的 `root/change-me` 与默认管理员密码 `123456` 仅为本地开发演示，部署前请全部修改；`JWT_SECRET` 上线前务必更换。
- **角色字段约束**：`users.role` 为 `TINYINT`（0 = 普通用户，1 = 管理员），前端 `AdminRoute.jsx`、`MainLayout.jsx` 依赖该数值判断权限，请勿改为字符串类型。
- **金额精度**：金额字段统一使用 `DECIMAL(10,2)`，请勿改为 FLOAT / DOUBLE。
- **移动端真机调试**：手机与电脑需在同一局域网；若请求失败，可参考 `personal-ledger-uniapp/安卓运行排查指南.md` 排查（如安卓明文 HTTP 限制）。
- **AI 功能可选**：未配置 `AGNES_API_KEY` 时，仅 AI 相关接口不可用，记账、统计、管理等其余功能均可正常使用。
- **数据库脚本幂等**：`sql/init_mysql.sql` 使用 `CREATE IF NOT EXISTS` + `ON DUPLICATE KEY UPDATE`，可重复执行；请勿调整其中建表的依赖顺序。
- **已知限制**：移动端依赖 `@dcloudio/*` 的 alpha 通道版本（已锁定精确版本号，升级请整组评估）；微信小程序端仅有空壳配置，尚未实际接入。
