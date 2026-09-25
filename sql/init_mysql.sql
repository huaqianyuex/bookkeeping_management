-- ============================================================================
--  智能个人记账管理系统 · MySQL 8 数据库初始化脚本
--  文件：sql/init_mysql.sql
--  生成日期：2026-09-10
-- ============================================================================
--
--  【一】目标数据库
--    MySQL 8.0+ / 存储引擎 InnoDB / 字符集 utf8mb4 / 排序规则 utf8mb4_general_ci
--    金额统一 DECIMAL(10,2)（禁止 FLOAT/DOUBLE 存钱）
--    业务表时间用 DATETIME（无小数秒）；AI 会话相关时间用 BIGINT 毫秒时间戳
--    标识符命名：全部小写 snake_case，脚本内一律使用反引号包裹
--
--  【二】执行方式
--    mysql -u root -p < sql/init_mysql.sql
--    或在客户端中直接整段执行。脚本可重复执行（CREATE IF NOT EXISTS + 幂等 INSERT）。
--
--  【三】依赖顺序（先主表后从表，勿调整）
--    1. users                 用户主表
--    2. user_token            依赖 users
--    3. categories            依赖 users
--    4. records               依赖 users, categories
--    5. sessions              依赖 users
--    6. messages              依赖 sessions
--    7. feedback              依赖 messages
--    8. faq                   独立字典表
--    9. ai_bookkeeping_logs   依赖 users, sessions, messages, 自身
--
--  【四】表间关系说明
--    users          1 : N  categories            （一个用户多个分类）
--    users          1 : N  records               （一个用户多条账单）
--    categories     1 : N  records               （一个分类下多条账单）
--    users          1 : N  user_token            （一个用户可有多枚有效令牌/多端登录）
--    users          1 : N  sessions              （一个用户多个 AI 会话）
--    sessions       1 : N  messages              （一个会话多条消息）
--    messages       1 : N  feedback              （一条消息可被反馈多次）
--    users          1 : N  ai_bookkeeping_logs   （一个用户多次 AI 记账请求）
--    sessions       1 : N  ai_bookkeeping_logs   （一次记账请求可挂在某会话下）
--    ai_bookkeeping_logs 1 : N ai_bookkeeping_logs （parent_id 自关联：追问续写 / 纠错链路）
--    faq            —      独立字典表，无外键
--    * 一对一：本系统无 1:1 关系
--    * 多对多：本系统无 N:M 关系，因此不需要中间表
--
--  【五】设计决策与已知偏差（务必阅读）
--    本项目存在两套并行的口径（`fast_backend/models/` 代码版 与
--    `docs/fastapi-backend/02-数据库设计.md` 文档版），二者在表名、字段、类型上不一致。
--    本脚本按以下约定折中，逐条如下：
--
--    (1) 表名口径【混用，有意为之】
--        业务表  → 复数（代码版）：users / user_token / categories / records
--        AI 表   → 单数（文档版）：sessions / messages / feedback / faq
--        ⚠️ 代码里 AI 表名是 chat_sessions / chat_messages / feedbacks / faqs，
--           与前端/接口文档约定不符，采用本脚本后需同步改 `fast_backend/models/chat.py`。
--
--    (2) `users.role` 用 **TINYINT 0/1**（0=普通用户，1=管理员）。
--        ⚠️ 前端硬约束：`components/AdminRoute.jsx` 用 `if (user.role !== 1)` 拦截管理后台、
--           `components/MainLayout.jsx` 用 `user?.role === 1` 决定是否显示管理入口、
--           `pages/AdminUsers.jsx` 用 `record.role === 1` 渲染「管理员」标签并禁用删除按钮。
--           若改成字符串 'user'/'admin'，管理后台会**整个进不去**、用户列表标签全错。
--        仓库中 `fast_backend/models/user.py` 曾写作 `VARCHAR(20)`，已一并改回 TINYINT。
--
--    (3) categories.user_id 允许 NULL，NULL 表示「系统预设分类」，随文档版语义。
--        ⚠️ 代码版写法是 `NOT NULL DEFAULT 0`，但 0 不是 users 表里存在的 id，
--           一旦建了真实外键就无法插入。改为 NULL 是同时满足「系统预设」与
--           「真实外键约束」的唯一做法，业务层判断需从 `user_id == 0` 改为 `user_id IS NULL`。
--
--    (4) records.category_id 外键为 ON DELETE RESTRICT。
--        ⚠️ 这会改变既有行为 B7：原 Java 允许「删除分类后账单保留悬空 category_id」，
--           建立外键后删除仍有账单的分类会被拒绝（errno 1451）。
--           若产品必须保留原行为，就不能建这条外键（见文件末尾「变体 B」）。
--
--    (5) `type` 语义统一为 **0=支出 / 1=收入**（`categories.type` 与 `records.type` 同一套）。
--        ⚠️ 这是**前端硬约束**，不是可选项：Web 端 `Records.jsx` 用
--           `categories.filter(c => c.type === 0)` 取支出分类、`categoryType === 0 ? '-' : '+'`
--           判正负号，`MainLayout.jsx` / `AdminRecords.jsx` / `Dashboard.jsx` 与 uni-app
--           的 `records/index`、`records/add-edit` 同理；`Dashboard` 还传 `type=0|1` 查统计。
--           若改成 1/2，支出分类会全被过滤掉、收支颜色与正负号全部反向。
--        仓库里 `fast_backend/` 的模型与 `fast_backend/docs/API文档_FastAPI.md` 曾写作
--        「1 支出 / 2 收入」，属未传导的错误，已一并改回 0/1。
--
--    (6) 业务表的创建/更新时间列统一为 created_at / updated_at（随 TimestampMixin）。
--        ⚠️ 文档版与旧 Java 库用的是 create_time / update_time。迁移存量数据时需做列名映射。
--
--    (7) ai_bookkeeping_logs 是本脚本新增的表（自然语言记账功能依赖），
--        其时间列沿用 created_at / updated_at（02 §3.5 原文写作 create_time / update_time，
--        此处统一，需同步修订该文档）。
--
--    (8) faq.embedding 默认不建（随文档版 02 §3.4，向量在启动时内存构建）。
--        若希望向量持久化以加快启动，启用该列的注释行即可（代码版有此列）。
--
-- ============================================================================


-- ---------------------------------------------------------------------------
-- 0. 库与全局设置
-- ---------------------------------------------------------------------------

CREATE DATABASE IF NOT EXISTS `bookkeeping_fastapi`
    DEFAULT CHARACTER SET utf8mb4
    DEFAULT COLLATE utf8mb4_general_ci;

USE `bookkeeping_fastapi`;

SET NAMES utf8mb4;
SET SESSION time_zone = '+08:00';

-- 【可选】需要清空重建时，取消下面整段的注释后再执行。
-- 注意：DROP 会永久删除数据，且 MySQL 的 DDL 会隐式提交，无法回滚。
--
-- SET FOREIGN_KEY_CHECKS = 0;
-- DROP TABLE IF EXISTS `ai_bookkeeping_logs`;
-- DROP TABLE IF EXISTS `feedback`;
-- DROP TABLE IF EXISTS `messages`;
-- DROP TABLE IF EXISTS `faq`;
-- DROP TABLE IF EXISTS `sessions`;
-- DROP TABLE IF EXISTS `records`;
-- DROP TABLE IF EXISTS `categories`;
-- DROP TABLE IF EXISTS `user_token`;
-- DROP TABLE IF EXISTS `users`;
-- SET FOREIGN_KEY_CHECKS = 1;


-- ============================================================================
--  一、业务表
-- ============================================================================

-- ---------------------------------------------------------------------------
-- 1. users —— 用户账号表
--    用途：存放系统登录账号，是全部业务数据的归属主体。
--          几乎所有业务查询都会带 `user_id = 当前用户`，实现多用户数据隔离。
--    来源：fast_backend/models/user.py
--    关系：被 user_token / categories / records / sessions / ai_bookkeeping_logs 引用（1:N）
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `users` (
    `id`            BIGINT       NOT NULL AUTO_INCREMENT           COMMENT '用户 ID，主键',
    `username`      VARCHAR(50)  NOT NULL                          COMMENT '用户名，登录账号，全局唯一',
    `password`      VARCHAR(100) NOT NULL                          COMMENT '密码哈希（BCrypt，$2b$10$ 开头共 60 字符）',
    `nickname`      VARCHAR(50)  NULL     DEFAULT NULL             COMMENT '昵称，可为空',
    `avatar`        VARCHAR(200) NULL     DEFAULT NULL             COMMENT '头像相对路径，如 /uploads/avatars/xxx.png',
    `email`         VARCHAR(100) NULL     DEFAULT NULL             COMMENT '邮箱，可为空',
    `phone`         VARCHAR(20)  NULL     DEFAULT NULL             COMMENT '手机号，唯一，可为空',
    `role`          TINYINT      NOT NULL DEFAULT 0                COMMENT '角色：0=普通用户，1=管理员',
    `status`        TINYINT      NOT NULL DEFAULT 1                COMMENT '状态：0=禁用，1=启用',
    `last_login_at` DATETIME     NULL     DEFAULT NULL             COMMENT '最后登录时间',
    `created_at`    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at`    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_users_username` (`username`),
    UNIQUE KEY `uk_users_phone` (`phone`),
    KEY `idx_users_status` (`status`)
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4
  COLLATE = utf8mb4_general_ci
  COMMENT = '用户账号表';


-- ---------------------------------------------------------------------------
-- 2. user_token —— 用户登录令牌表
--    用途：记录已签发的登录令牌，支持令牌吊销与多端登录管理。
--          （服务端同时支持无状态 JWT；本表用于需要主动失效令牌的场景）
--    来源：fast_backend/models/user.py → UserToken
--    关系：user_token.user_id → users.id（N:1）
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `user_token` (
    `id`         BIGINT       NOT NULL AUTO_INCREMENT           COMMENT '令牌 ID，主键',
    `user_id`    BIGINT       NOT NULL                          COMMENT '所属用户 ID',
    `token`      VARCHAR(255) NOT NULL                          COMMENT '令牌值（JWT 或随机串），唯一',
    `expires_at` DATETIME     NOT NULL                          COMMENT '过期时间',
    `created_at` DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_user_token_token` (`token`),
    KEY `idx_user_token_user` (`user_id`),
    CONSTRAINT `fk_user_token_user` FOREIGN KEY (`user_id`)
        REFERENCES `users` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4
  COLLATE = utf8mb4_general_ci
  COMMENT = '用户登录令牌表';


-- ---------------------------------------------------------------------------
-- 3. categories —— 收支分类表
--    用途：账单的分类字典。既存放系统预设分类（user_id 为 NULL），
--          也存放用户自建分类（user_id 指向本人）。
--          系统预设中的「其他」是 AI 自然语言记账识别不出分类时的兜底归属。
--    来源：fast_backend/models/category.py
--    关系：categories.user_id → users.id（N:1）；被 records.category_id 引用（1:N）
--    注意：type 取值 0=支出 / 1=收入（与 records.type 同一套语义，前端按此判断）
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `categories` (
    `id`         BIGINT      NOT NULL AUTO_INCREMENT           COMMENT '分类 ID，主键',
    `user_id`    BIGINT      NULL     DEFAULT NULL             COMMENT '归属用户 ID；NULL 表示系统预设分类',
    `name`       VARCHAR(50) NOT NULL                          COMMENT '分类名称，如 餐饮/交通/工资',
    `type`       TINYINT     NOT NULL                          COMMENT '收支类型：0=支出，1=收入',
    `icon`       VARCHAR(50) NULL     DEFAULT NULL             COMMENT '图标标识，可为空',
    `sort_order` INT         NOT NULL DEFAULT 0                COMMENT '排序值，越小越靠前',
    `status`     TINYINT     NOT NULL DEFAULT 1                COMMENT '状态：0=禁用，1=启用',
    `created_at` DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (`id`),
    KEY `idx_categories_user_type` (`user_id`, `type`),
    CONSTRAINT `fk_categories_user` FOREIGN KEY (`user_id`)
        REFERENCES `users` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
    -- 【可选】若要求「同一用户、同一类型下分类名唯一」，取消下一行注释：
    -- , UNIQUE KEY `uk_categories_user_name_type` (`user_id`, `name`, `type`)
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4
  COLLATE = utf8mb4_general_ci
  COMMENT = '收支分类表（user_id 为 NULL 表示系统预设）';


-- ---------------------------------------------------------------------------
-- 4. records —— 记账流水表（核心业务表）
--    用途：存放每一笔收入/支出。手工记账（POST /api/records）与
--          AI 自然语言记账（POST /api/ai/bookkeeping）最终都写入本表。
--    来源：fast_backend/models/record.py
--    关系：records.user_id → users.id（N:1）；records.category_id → categories.id（N:1）
--    注意：type 取值 0=支出 / 1=收入；status=0 表示已软删除（AI 记账的「撤销」走软删）
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `records` (
    `id`          BIGINT        NOT NULL AUTO_INCREMENT           COMMENT '账单 ID，主键',
    `user_id`     BIGINT        NOT NULL                          COMMENT '所属用户 ID',
    `category_id` BIGINT        NOT NULL                          COMMENT '分类 ID',
    `type`        TINYINT       NOT NULL                          COMMENT '收支类型：0=支出，1=收入',
    `amount`      DECIMAL(10,2) NOT NULL                          COMMENT '金额，必须大于 0，最大 99999999.99',
    `date`        DATE          NOT NULL                          COMMENT '记账日期',
    `remark`      VARCHAR(200)  NULL     DEFAULT NULL             COMMENT '备注，可为空',
    `status`      TINYINT       NOT NULL DEFAULT 1                COMMENT '状态：0=已删除（软删），1=正常',
    `created_at`  DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at`  DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (`id`),
    KEY `idx_records_user_date` (`user_id`, `date`),
    KEY `idx_records_category` (`category_id`),
    KEY `idx_records_user_status_date` (`user_id`, `status`, `date`),
    CONSTRAINT `fk_records_user` FOREIGN KEY (`user_id`)
        REFERENCES `users` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT `fk_records_category` FOREIGN KEY (`category_id`)
        REFERENCES `categories` (`id`) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4
  COLLATE = utf8mb4_general_ci
  COMMENT = '记账流水表';


-- ============================================================================
--  二、AI 助手表
--  时间列说明：sessions / messages / feedback 的时间列均为 **BIGINT 毫秒时间戳**，
--             前端用 Date.now() 直接比对并做相对时间格式化，切勿改成 DATETIME。
-- ============================================================================

-- ---------------------------------------------------------------------------
-- 5. sessions —— AI 对话会话表（软删除）
--    用途：AI 助手的会话列表。deleted_at 为 0 表示未删除，
--          大于 0 时存放删除那一刻的毫秒时间戳（软删，由定时任务在 7 天后物理清除）。
--    来源：docs/fastapi-backend/02-数据库设计.md §3.1
--    关系：sessions.user_id → users.id（N:1）；被 messages、ai_bookkeeping_logs 引用（1:N）
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `sessions` (
    `id`         VARCHAR(64) NOT NULL                          COMMENT '主键，格式 session_{毫秒}_{随机≤9位}',
    `user_id`    BIGINT      NULL     DEFAULT NULL             COMMENT '归属用户 ID；NULL 表示历史遗留无主数据',
    `title`      VARCHAR(50) NOT NULL                          COMMENT '会话标题，默认「新对话」',
    `auto_title` TINYINT     NOT NULL DEFAULT 1                COMMENT '标题是否可被 AI 覆盖：1=可覆盖，0=用户已重命名锁定',
    `created_at` BIGINT      NOT NULL                          COMMENT '创建时间（毫秒时间戳）',
    `updated_at` BIGINT      NOT NULL                          COMMENT '更新时间（毫秒时间戳）',
    `deleted_at` BIGINT      NOT NULL DEFAULT 0                COMMENT '软删标记：0=未删除，>0=删除时的毫秒时间戳',
    PRIMARY KEY (`id`),
    KEY `idx_sessions_user` (`user_id`, `deleted_at`, `updated_at`),
    CONSTRAINT `fk_sessions_user` FOREIGN KEY (`user_id`)
        REFERENCES `users` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4
  COLLATE = utf8mb4_general_ci
  COMMENT = 'AI 对话会话表（时间列为毫秒时间戳）';


-- ---------------------------------------------------------------------------
-- 6. messages —— AI 对话消息表
--    用途：存放会话内的每一轮消息（role=user / assistant）。
--    来源：docs/fastapi-backend/02-数据库设计.md §3.2
--    关系：messages.session_id → sessions.id（N:1）；被 feedback.message_id 引用（1:N）
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `messages` (
    `id`         VARCHAR(64) NOT NULL                          COMMENT '主键，格式 msg_{毫秒}_{随机≤9位}',
    `session_id` VARCHAR(64) NOT NULL                          COMMENT '所属会话 ID',
    `role`       VARCHAR(16) NOT NULL                          COMMENT '角色：user=用户，assistant=AI',
    `content`    TEXT        NOT NULL                          COMMENT '消息正文',
    `timestamp`  BIGINT      NOT NULL                          COMMENT '发送时间（毫秒时间戳）',
    PRIMARY KEY (`id`),
    KEY `idx_messages_session_ts` (`session_id`, `timestamp`),
    CONSTRAINT `fk_messages_session` FOREIGN KEY (`session_id`)
        REFERENCES `sessions` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4
  COLLATE = utf8mb4_general_ci
  COMMENT = 'AI 对话消息表（时间列为毫秒时间戳）';


-- ---------------------------------------------------------------------------
-- 7. feedback —— AI 回复反馈表
--    用途：用户对某条 AI 回复的评分与留言，用于满意度统计
--          （GET /api/ai/admin/stats 的 averageRating 取自本表）。
--    来源：docs/fastapi-backend/02-数据库设计.md §3.3
--    关系：feedback.message_id → messages.id（N:1）
--    注意：本表按文档版未设 user_id，因此无法按用户维度隔离反馈。
--          如需「谁反馈的」分析，需新增 user_id 列并同步 02/08 文档。
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `feedback` (
    `id`         VARCHAR(64) NOT NULL                          COMMENT '主键，格式 feedback_{毫秒}_{随机≤9位}',
    `user_id`    BIGINT      NOT NULL                          COMMENT '反馈人 ID，关联 users.id',
    `message_id` VARCHAR(64) NOT NULL                          COMMENT '被评价的消息 ID',
    `rating`     TINYINT     NOT NULL                          COMMENT '评分，1~5',
    `comment`    TEXT        NULL                              COMMENT '文字反馈内容，可为空',
    `timestamp`  BIGINT      NOT NULL                          COMMENT '反馈时间（毫秒时间戳）',
    PRIMARY KEY (`id`),
    KEY `idx_feedback_message` (`message_id`),
    KEY `idx_feedback_user` (`user_id`),
    CONSTRAINT `fk_feedback_message` FOREIGN KEY (`message_id`)
        REFERENCES `messages` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT `fk_feedback_user` FOREIGN KEY (`user_id`)
        REFERENCES `users` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4
  COLLATE = utf8mb4_general_ci
  COMMENT = 'AI 回复反馈表（时间列为毫秒时间戳）';


-- ---------------------------------------------------------------------------
-- 8. faq —— FAQ 知识库表（基础配置数据字典表）
--    用途：AI 助手的常见问题知识库，供语义检索（GET /api/ai/faq/search）使用；
--          启动时预加载并构建向量索引，POST /api/ai/faq/rebuild 可全量重建。
--    来源：docs/fastapi-backend/02-数据库设计.md §3.4
--    关系：独立字典表，无外键
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `faq` (
    `id`       INT         NOT NULL AUTO_INCREMENT           COMMENT '主键',
    `question` TEXT        NOT NULL                          COMMENT '问题',
    `answer`   TEXT        NOT NULL                          COMMENT '回答',
    `category` VARCHAR(50) NOT NULL                          COMMENT '分类标签，如 记账操作/账单查询',
    -- `embedding` TEXT     NULL                              COMMENT '向量（JSON 数组）；启用后可持久化向量',
    PRIMARY KEY (`id`),
    KEY `idx_faq_category` (`category`)
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4
  COLLATE = utf8mb4_general_ci
  COMMENT = 'FAQ 知识库表';


-- ============================================================================
--  三、AI 自然语言记账表
-- ============================================================================

-- ---------------------------------------------------------------------------
-- 9. ai_bookkeeping_logs —— AI 自然语言记账日志表
--    用途：一表三用 ——
--          ① 幂等去重：client_msg_id 强幂等 + dedup_hash 5 分钟窗口弱幂等，
--             保证同一条消息不会重复入账；
--          ② 追问草稿：信息不全（如缺金额）时暂存半成品，status=0，
--             用户补充后携带 draft_id 续写，30 分钟过期；
--          ③ 审计与纠错样本：记录「AI 记账 → 用户修改/撤销」的完整链路。
--    来源：docs/fastapi-backend/02-数据库设计.md §3.5
--    关系：user_id → users.id；session_id → sessions.id；message_id → messages.id；
--          parent_id → 自身 id（自关联，指向被续写/被修改的原日志）
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `ai_bookkeeping_logs` (
    `id`            BIGINT       NOT NULL AUTO_INCREMENT           COMMENT '主键',
    `request_id`    VARCHAR(64)  NOT NULL                          COMMENT '对外请求 ID，格式 bk_{毫秒}_{随机}',
    `user_id`       BIGINT       NOT NULL                          COMMENT '发起用户 ID',
    `session_id`    VARCHAR(64)  NULL     DEFAULT NULL             COMMENT '关联的 AI 会话 ID，可为空',
    `message_id`    VARCHAR(64)  NULL     DEFAULT NULL             COMMENT '关联的消息 ID，可为空',
    `client_msg_id` VARCHAR(64)  NULL     DEFAULT NULL             COMMENT '客户端幂等键（UUID）；NULL 表示不启用强幂等',
    `dedup_hash`    CHAR(64)     NOT NULL                          COMMENT 'SHA256(user_id|归一化文本)，用于弱幂等窗口去重',
    `raw_text`      VARCHAR(500) NOT NULL                          COMMENT '用户原始消息文本',
    `intent`        VARCHAR(20)  NOT NULL                          COMMENT '意图：bookkeeping/amend/delete/query/chitchat',
    `action`        VARCHAR(20)  NOT NULL                          COMMENT '处理结果：created/clarify/ignored/duplicate/preview/amend/delete/error',
    `parse_json`    JSON         NULL                              COMMENT 'LLM 抽取出的原始解析结果',
    `record_ids`    JSON         NULL                              COMMENT '本次入账的 records.id 数组，如 [128,129]',
    `error_msg`     VARCHAR(200) NULL     DEFAULT NULL             COMMENT '失败原因（仅内部记录，不回显给前端）',
    `status`        TINYINT      NOT NULL DEFAULT 1                COMMENT '状态：0=草稿待追问，1=已处理，2=已回滚',
    `parent_id`     BIGINT       NULL     DEFAULT NULL             COMMENT '指向原日志 ID（追问续写 / 修改 / 撤销）',
    `created_at`    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at`    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_abk_request_id` (`request_id`),
    UNIQUE KEY `uk_abk_client_msg` (`user_id`, `client_msg_id`),
    KEY `idx_abk_dedup` (`user_id`, `dedup_hash`, `created_at`),
    KEY `idx_abk_user_recent` (`user_id`, `created_at`),
    KEY `idx_abk_session` (`session_id`, `id`),
    KEY `idx_abk_parent` (`parent_id`),
    CONSTRAINT `fk_abk_user` FOREIGN KEY (`user_id`)
        REFERENCES `users` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT `fk_abk_session` FOREIGN KEY (`session_id`)
        REFERENCES `sessions` (`id`) ON DELETE SET NULL ON UPDATE CASCADE,
    CONSTRAINT `fk_abk_message` FOREIGN KEY (`message_id`)
        REFERENCES `messages` (`id`) ON DELETE SET NULL ON UPDATE CASCADE,
    CONSTRAINT `fk_abk_parent` FOREIGN KEY (`parent_id`)
        REFERENCES `ai_bookkeeping_logs` (`id`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4
  COLLATE = utf8mb4_general_ci
  COMMENT = 'AI 自然语言记账日志表（幂等 / 追问草稿 / 审计）';

-- ⚠️ `client_msg_id` 允许为 NULL：MySQL 唯一索引对多行 NULL 不冲突，
--    这正是「未传幂等键时不触发强幂等」的预期行为，切勿改为 NOT NULL。


-- ============================================================================
--  四、初始化数据（基础字典与默认账号）
-- ============================================================================

-- ---------------------------------------------------------------------------
-- 4.1 默认管理员账号
--     用户名：admin    密码：123456
--     密码为 BCrypt 哈希（strength=10），可由 bcrypt.checkpw("123456", hash) 验证通过。
--     上线前请务必修改密码。
-- ---------------------------------------------------------------------------
INSERT INTO `users` (`username`, `password`, `nickname`, `role`, `status`)
VALUES ('admin',
        '$2b$10$rBiLbDPdRudrgpFVVcz7UekHykTr1ULhDJo24UPWYeiUPvD.pVJK6',
        '系统管理员',
        1,
        1)
ON DUPLICATE KEY UPDATE `id` = `id`;


-- ---------------------------------------------------------------------------
-- 4.2 系统预设分类（user_id 为 NULL，任何用户可见，不可被用户删除）
--     type：0=支出，1=收入
--     其中支出类的「其他」（id=10）是 AI 自然语言记账识别不出分类时的兜底归属。
--     使用显式 id（1~16）+ ON DUPLICATE KEY UPDATE，保证脚本可重复执行；
--     用户后续自建分类的 id 从 17 开始自增，不会冲突。
-- ---------------------------------------------------------------------------
INSERT INTO `categories` (`id`, `user_id`, `name`, `type`, `icon`, `sort_order`, `status`)
VALUES (1,  NULL, '餐饮',   0, 'food',      1,  1),
       (2,  NULL, '交通',   0, 'transport', 2,  1),
       (3,  NULL, '购物',   0, 'shopping',  3,  1),
       (4,  NULL, '娱乐',   0, 'entertain', 4,  1),
       (5,  NULL, '住房',   0, 'house',     5,  1),
       (6,  NULL, '医疗',   0, 'medical',   6,  1),
       (7,  NULL, '教育',   0, 'education', 7,  1),
       (8,  NULL, '通讯',   0, 'telecom',   8,  1),
       (9,  NULL, '人情',   0, 'social',    9,  1),
       (10, NULL, '其他',   0, 'other',     99, 1),
       (11, NULL, '工资',   1, 'salary',    1,  1),
       (12, NULL, '奖金',   1, 'bonus',     2,  1),
       (13, NULL, '兼职',   1, 'parttime',  3,  1),
       (14, NULL, '理财',   1, 'invest',    4,  1),
       (15, NULL, '红包',   1, 'redpack',   5,  1),
       (16, NULL, '其他',   1, 'other',     99, 1)
ON DUPLICATE KEY UPDATE
    `user_id`    = VALUES(`user_id`),
    `name`       = VALUES(`name`),
    `type`       = VALUES(`type`),
    `icon`       = VALUES(`icon`),
    `sort_order` = VALUES(`sort_order`),
    `status`     = VALUES(`status`);


-- ---------------------------------------------------------------------------
-- 4.3 FAQ 种子数据（8 条，供 AI 助手语义检索）
--     使用显式 id + ON DUPLICATE KEY UPDATE，保证脚本可重复执行。
-- ---------------------------------------------------------------------------
INSERT INTO `faq` (`id`, `question`, `answer`, `category`) VALUES
    (1, '如何添加一笔消费记录？',
        '您可以直接对我说：「帮我记录一笔餐饮消费50元」，我会自动帮您记录。也可以说「添加支出：交通，30元」等。',
        '记账操作'),
    (2, '如何查看我的账单？',
        '您可以说：「查看本月的账单」、「显示我的消费记录」、「这个月花了多少钱」等，我会为您展示相应的账单信息。',
        '账单查询'),
    (3, '系统支持哪些消费类型？',
        '我们支持多种消费类型：餐饮、交通、购物、娱乐、住房、医疗、教育、其他等。您也可以自定义消费类型。',
        '功能介绍'),
    (4, '如何设置预算？',
        '您可以说：「设置本月预算为5000元」、「帮我制定消费预算」等，我会帮您设置并跟踪预算执行情况。',
        '预算管理'),
    (5, '数据会保存多久？',
        '您的记账数据会永久保存在系统中，除非您主动删除。我们重视您的数据安全。',
        '技术支持'),
    (6, '如何导出账单？',
        '目前支持导出为 CSV 格式。您可以说：「导出本月账单为 CSV」、「下载我的消费记录」等。',
        '数据管理'),
    (7, '什么是储蓄率？',
        '储蓄率 = (收入 - 支出) / 收入 × 100%。健康的储蓄率建议在 20% 以上，表示您有较强的财务安全垫。',
        '财务知识'),
    (8, '如何分析消费趋势？',
        '您可以说：「分析我的消费趋势」、「这个月花钱多了吗」，我会对比历史数据帮助您了解消费变化。',
        '财务分析')
ON DUPLICATE KEY UPDATE
    `question` = VALUES(`question`),
    `answer`   = VALUES(`answer`),
    `category` = VALUES(`category`);


-- ============================================================================
--  五、执行结果校验
-- ============================================================================
-- 执行完成后，预期看到 9 张业务/支撑表：
--
--   SELECT TABLE_NAME, TABLE_COMMENT FROM information_schema.TABLES
--    WHERE TABLE_SCHEMA = 'bookkeeping_fastapi' ORDER BY TABLE_NAME;
--
-- 预期数据量：
--   SELECT COUNT(*) FROM `users`;                -- ≥ 1（admin）
--   SELECT COUNT(*) FROM `categories`;           -- 16（系统预设）
--   SELECT COUNT(*) FROM `faq`;                  -- 8
--
-- 外键是否建立成功：
--   SELECT TABLE_NAME, CONSTRAINT_NAME, REFERENCED_TABLE_NAME
--     FROM information_schema.KEY_COLUMN_USAGE
--    WHERE TABLE_SCHEMA = 'bookkeeping_fastapi' AND REFERENCED_TABLE_NAME IS NOT NULL;
--   预期 11 条外键约束（fk_user_token_user / fk_categories_user /
--   fk_records_user / fk_records_category / fk_sessions_user / fk_messages_session /
--   fk_feedback_message / fk_abk_user / fk_abk_session / fk_abk_message / fk_abk_parent）。


-- ============================================================================
--  六、可选变体（按需启用，与上方主脚本二选一）
-- ============================================================================
--
-- 【变体 B】移除 records.category_id 外键，保留「删分类不级联、账单留悬空引用」的既有行为
--   适用：必须与旧 Java 行为 B7 完全一致时。
--   做法：删掉 records 表的 `fk_records_category` 约束声明，仅保留 `idx_records_category` 索引。
--
-- 【变体 C】启用 faq.embedding，将 FAQ 向量持久化
--   适用：希望避免每次启动重新计算向量。
--   做法：取消 faq 表定义中 embedding 列那一行的注释。
