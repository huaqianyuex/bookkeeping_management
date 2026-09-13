-- ============================================================================
-- 智能个人记账管理系统 · 按 fast_backend/models/* ORM 模型生成的建表 SQL
-- 数据库方言：MySQL 8.0+（项目 DATABASE_URL = mysql+aiomysql://.../bookkeeping_fastapi）
-- 引擎：InnoDB / 字符集：utf8mb4 / 排序规则：utf8mb4_general_ci
-- 生成依据：
--   fast_backend/models/base.py       IdMixin / TimestampMixin
--   fast_backend/models/user.py       User / UserToken
--   fast_backend/models/category.py   Category
--   fast_backend/models/record.py     Record
--   fast_backend/models/chat.py       ChatSession / ChatMessage / Feedback / Faq
--   fast_backend/models/bookkeeping.py AiBookkeepingLog
-- 说明：
--   * 金额一律 DECIMAL(10,2)，禁止 FLOAT/DOUBLE；
--   * 业务表（users/user_token/categories/records/ai_bookkeeping_logs）时间为 DATETIME；
--     AI 会话相关表（sessions/messages/feedback）时间为 BIGINT 毫秒时间戳（前端 Date.now() 直接比对）；
--   * ORM 的 Integer 枚举标志列（role/status/type/auto_title/rating）按项目口径（sql/init_mysql.sql
--     与 02-数据库设计.md）映射为 TINYINT；sort_order 按字面映射为 INT；
--   * 建表顺序 = 外键依赖顺序（被依赖的表先建）：
--     users → user_token / categories / sessions → records / messages → feedback → ai_bookkeeping_logs
--     （faq 为独立字典表，无外键，放任意位置）
-- ============================================================================

CREATE DATABASE IF NOT EXISTS `bookkeeping_fastapi`
    DEFAULT CHARACTER SET utf8mb4
    DEFAULT COLLATE utf8mb4_general_ci;

USE `bookkeeping_fastapi`;

SET NAMES utf8mb4;
SET SESSION time_zone = '+08:00';


-- ----------------------------------------------------------------------------
-- 1. users —— 用户账号表（Model: User, models/user.py）
--    全部业务数据的归属主体，多用户数据隔离的基础表。
--    被 user_token / categories / records / sessions / ai_bookkeeping_logs 引用（1:N）
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `users` (
    `id`            BIGINT       NOT NULL AUTO_INCREMENT              COMMENT '主键 ID',
    `username`      VARCHAR(50)  NOT NULL                             COMMENT '用户名，登录账号，全局唯一',
    `password`      VARCHAR(100) NOT NULL                             COMMENT '密码哈希（BCrypt，$2b$10$ 开头共 60 字符）',
    `nickname`      VARCHAR(50)  NULL     DEFAULT NULL               COMMENT '昵称，可为空',
    `avatar`        VARCHAR(200) NULL     DEFAULT NULL               COMMENT '头像相对路径，如 /uploads/avatars/xxx.png',
    `email`         VARCHAR(100) NULL     DEFAULT NULL               COMMENT '邮箱，可为空',
    `phone`         VARCHAR(20)  NULL     DEFAULT NULL               COMMENT '手机号，唯一，可为空',
    `role`          TINYINT      NOT NULL DEFAULT 0                  COMMENT '角色：0=普通用户，1=管理员（前端按 role===1 放行管理后台）',
    `status`        TINYINT      NOT NULL DEFAULT 1                  COMMENT '状态：0=禁用，1=启用',
    `last_login_at` DATETIME     NULL     DEFAULT NULL               COMMENT '最后登录时间',
    `created_at`    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP  COMMENT '创建时间',
    `updated_at`    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP
                                          ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_users_username` (`username`),
    UNIQUE KEY `uk_users_phone` (`phone`),
    KEY `idx_users_status` (`status`)
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4
  COLLATE = utf8mb4_general_ci
  COMMENT = '用户账号表';


-- ----------------------------------------------------------------------------
-- 2. user_token —— 用户登录令牌表（Model: UserToken, models/user.py）
--    记录已签发令牌，支持吊销与多端登录管理。
--    注：当前运行时鉴权为无状态 JWT（utils/auth.py），本表为预留的令牌持久化表。
--    关系：user_token.user_id → users.id（N:1，级联删除）
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `user_token` (
    `id`         BIGINT       NOT NULL AUTO_INCREMENT              COMMENT '主键 ID',
    `user_id`    BIGINT       NOT NULL                             COMMENT '所属用户 ID',
    `token`      VARCHAR(255) NOT NULL                             COMMENT '令牌值（JWT 或随机串），唯一',
    `expires_at` DATETIME     NOT NULL                             COMMENT '过期时间',
    `created_at` DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP   COMMENT '创建时间',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_user_token_token` (`token`),
    KEY `idx_user_token_user` (`user_id`),
    CONSTRAINT `fk_user_token_user` FOREIGN KEY (`user_id`)
        REFERENCES `users` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4
  COLLATE = utf8mb4_general_ci
  COMMENT = '用户登录令牌表（预留，当前鉴权走无状态 JWT）';


-- ----------------------------------------------------------------------------
-- 3. categories —— 收支分类表（Model: Category, models/category.py）
--    分类字典：user_id 为 NULL = 系统预设分类（全用户可见、不可删）；
--    type 语义 0=支出 / 1=收入（前端硬约束，勿改 1/2）。
--    关系：categories.user_id → users.id（N:1，级联删除）；被 records 引用（1:N，RESTRICT）
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `categories` (
    `id`         BIGINT      NOT NULL AUTO_INCREMENT              COMMENT '主键 ID',
    `user_id`    BIGINT      NULL     DEFAULT NULL               COMMENT '归属用户 ID；NULL 表示系统预设分类',
    `name`       VARCHAR(50) NOT NULL                             COMMENT '分类名称，如 餐饮/交通/工资',
    `type`       TINYINT     NOT NULL                             COMMENT '收支类型：0=支出，1=收入',
    `icon`       VARCHAR(50) NULL     DEFAULT NULL               COMMENT '图标标识，可为空',
    `sort_order` INT         NOT NULL DEFAULT 0                   COMMENT '排序值，越小越靠前',
    `status`     TINYINT     NOT NULL DEFAULT 1                   COMMENT '状态：0=禁用，1=启用',
    `created_at` DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP  COMMENT '创建时间',
    `updated_at` DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP
                                        ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (`id`),
    KEY `idx_categories_user_type` (`user_id`, `type`),
    CONSTRAINT `fk_categories_user` FOREIGN KEY (`user_id`)
        REFERENCES `users` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4
  COLLATE = utf8mb4_general_ci
  COMMENT = '收支分类表（user_id 为 NULL 表示系统预设）';


-- ----------------------------------------------------------------------------
-- 4. records —— 记账流水表（Model: Record, models/record.py）
--    核心业务表：手工记账（POST /api/records）与 AI 记账最终都写入本表。
--    日期列名为 date（对外 JSON 键 alias=recordDate）；status=0 为软删（AI 撤销走软删）。
--    关系：records.user_id → users.id（N:1，级联删除）；
--          records.category_id → categories.id（N:1，RESTRICT：仍有账单的分类不可删）
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `records` (
    `id`          BIGINT        NOT NULL AUTO_INCREMENT              COMMENT '主键 ID',
    `user_id`     BIGINT        NOT NULL                             COMMENT '所属用户 ID',
    `category_id` BIGINT        NOT NULL                             COMMENT '分类 ID',
    `type`        TINYINT       NOT NULL                             COMMENT '收支类型：0=支出，1=收入',
    `amount`      DECIMAL(10,2) NOT NULL                             COMMENT '金额（定点 2 位，>0，最大 99999999.99）',
    `date`        DATE          NOT NULL                             COMMENT '记账日期',
    `remark`      VARCHAR(200)  NULL     DEFAULT NULL               COMMENT '备注，可为空',
    `status`      TINYINT       NOT NULL DEFAULT 1                   COMMENT '状态：0=已删除（软删），1=正常',
    `created_at`  DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP  COMMENT '创建时间',
    `updated_at`  DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP
                                          ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
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


-- ----------------------------------------------------------------------------
-- 5. sessions —— AI 对话会话表（Model: ChatSession, models/chat.py）
--    软删：deleted_at=0 未删，>0 存删除时毫秒值（定时任务 7 天后物理清除）。
--    主键为业务字符串 session_{毫秒}_{随机}；时间列均为 BIGINT 毫秒（勿改 DATETIME）。
--    关系：sessions.user_id → users.id（N:1，级联删除；NULL=历史遗留无主数据）
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `sessions` (
    `id`         VARCHAR(64) NOT NULL                               COMMENT '主键，格式 session_{毫秒}_{随机}',
    `user_id`    BIGINT      NULL     DEFAULT NULL                  COMMENT '归属用户 ID；NULL 表示历史遗留无主数据',
    `title`      VARCHAR(50) NOT NULL                               COMMENT '会话标题（ORM 层默认“新对话”）',
    `auto_title` TINYINT     NOT NULL DEFAULT 1                     COMMENT '1=AI 可覆盖标题，0=用户已重命名锁定',
    `created_at` BIGINT      NOT NULL                               COMMENT '创建时间（毫秒时间戳）',
    `updated_at` BIGINT      NOT NULL                               COMMENT '更新时间（毫秒时间戳）',
    `deleted_at` BIGINT      NOT NULL DEFAULT 0                     COMMENT '软删标记：0=未删除，>0=删除时的毫秒时间戳',
    PRIMARY KEY (`id`),
    KEY `idx_sessions_user` (`user_id`, `deleted_at`, `updated_at`),
    CONSTRAINT `fk_sessions_user` FOREIGN KEY (`user_id`)
        REFERENCES `users` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4
  COLLATE = utf8mb4_general_ci
  COMMENT = 'AI 对话会话表（时间列为毫秒时间戳）';


-- ----------------------------------------------------------------------------
-- 6. messages —— AI 对话消息表（Model: ChatMessage, models/chat.py）
--    会话内每一轮消息（role=user/assistant）。
--    关系：messages.session_id → sessions.id（N:1，级联删除）；被 feedback 引用（1:N）
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `messages` (
    `id`         VARCHAR(64) NOT NULL                               COMMENT '主键，格式 msg_{毫秒}_{随机}',
    `session_id` VARCHAR(64) NOT NULL                               COMMENT '所属会话 ID',
    `role`       VARCHAR(16) NOT NULL                               COMMENT '角色：user=用户，assistant=AI',
    `content`    TEXT        NOT NULL                               COMMENT '消息正文',
    `timestamp`  BIGINT      NOT NULL                               COMMENT '发送时间（毫秒时间戳）',
    PRIMARY KEY (`id`),
    KEY `idx_messages_session_ts` (`session_id`, `timestamp`),
    CONSTRAINT `fk_messages_session` FOREIGN KEY (`session_id`)
        REFERENCES `sessions` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4
  COLLATE = utf8mb4_general_ci
  COMMENT = 'AI 对话消息表（时间列为毫秒时间戳）';


-- ----------------------------------------------------------------------------
-- 7. feedback —— AI 回复反馈表（Model: Feedback, models/chat.py）
--    用户对某条 AI 回复的评分（1~5）与留言。
--    注：按既有结构无 user_id 列，无法按用户维度隔离反馈。
--    关系：feedback.message_id → messages.id（N:1，级联删除）
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `feedback` (
    `id`         VARCHAR(64) NOT NULL                               COMMENT '主键，格式 feedback_{毫秒}_{随机}',
    `message_id` VARCHAR(64) NOT NULL                               COMMENT '被评价的消息 ID',
    `rating`     TINYINT     NOT NULL                               COMMENT '评分，1~5',
    `comment`    TEXT        NULL                                   COMMENT '文字反馈内容，可为空',
    `timestamp`  BIGINT      NOT NULL                               COMMENT '反馈时间（毫秒时间戳）',
    PRIMARY KEY (`id`),
    KEY `idx_feedback_message` (`message_id`),
    CONSTRAINT `fk_feedback_message` FOREIGN KEY (`message_id`)
        REFERENCES `messages` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4
  COLLATE = utf8mb4_general_ci
  COMMENT = 'AI 回复反馈表（时间列为毫秒时间戳）';


-- ----------------------------------------------------------------------------
-- 8. faq —— FAQ 知识库表（Model: Faq, models/chat.py）
--    独立字典表，无外键；AI 助手语义检索（GET /api/ai/faq/search）的数据源。
--    embedding 列按文档决策默认不建（向量在启动时内存构建）。
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `faq` (
    `id`       INT         NOT NULL AUTO_INCREMENT              COMMENT '主键 ID',
    `question` TEXT        NOT NULL                             COMMENT '问题',
    `answer`   TEXT        NOT NULL                             COMMENT '回答',
    `category` VARCHAR(50) NOT NULL                             COMMENT '分类标签，如 记账操作/账单查询',
    PRIMARY KEY (`id`),
    KEY `idx_faq_category` (`category`)
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4
  COLLATE = utf8mb4_general_ci
  COMMENT = 'FAQ 知识库表';


-- ----------------------------------------------------------------------------
-- 9. ai_bookkeeping_logs —— AI 自然语言记账日志表（Model: AiBookkeepingLog, models/bookkeeping.py）
--    一表三用：① 幂等去重（client_msg_id 强幂等 + dedup_hash 5 分钟弱幂等）；
--    ② 追问草稿（status=0 暂存半成品，30 分钟过期）；③ 审计与纠错样本（parent_id 自关联）。
--    注：client_msg_id 允许 NULL —— MySQL 唯一索引对多行 NULL 不冲突，切勿改 NOT NULL。
--    关系：user_id → users.id（级联删除）；session_id → sessions.id / message_id → messages.id
--          （ON DELETE SET NULL，会话被清理后日志保留）；parent_id → 自身 id（SET NULL 自关联）
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `ai_bookkeeping_logs` (
    `id`            BIGINT       NOT NULL AUTO_INCREMENT              COMMENT '主键 ID',
    `request_id`    VARCHAR(64)  NOT NULL                             COMMENT '对外请求 ID，格式 bk_{毫秒}_{随机}',
    `user_id`       BIGINT       NOT NULL                             COMMENT '发起用户 ID',
    `session_id`    VARCHAR(64)  NULL     DEFAULT NULL               COMMENT '关联的 AI 会话 ID，可为空',
    `message_id`    VARCHAR(64)  NULL     DEFAULT NULL               COMMENT '关联的消息 ID，可为空',
    `client_msg_id` VARCHAR(64)  NULL     DEFAULT NULL               COMMENT '客户端幂等键（UUID）；NULL 表示不启用强幂等',
    `dedup_hash`    CHAR(64)     NOT NULL                             COMMENT 'SHA256(user_id|归一化文本)，用于弱幂等窗口去重',
    `raw_text`      VARCHAR(500) NOT NULL                             COMMENT '用户原始消息文本',
    `intent`        VARCHAR(20)  NOT NULL                             COMMENT '意图：bookkeeping/amend/delete/query/chitchat',
    `action`        VARCHAR(20)  NOT NULL                             COMMENT '处理结果：created/clarify/ignored/duplicate/preview/amend/delete/error',
    `parse_json`    JSON         NULL                                 COMMENT 'LLM 抽取出的原始解析结果（JSON 列不能带默认值）',
    `record_ids`    JSON         NULL                                 COMMENT '本次入账的 records.id 数组，如 [128,129]',
    `error_msg`     VARCHAR(200) NULL     DEFAULT NULL               COMMENT '失败原因（仅内部记录，不回显给前端）',
    `status`        TINYINT      NOT NULL DEFAULT 1                   COMMENT '状态：0=草稿待追问，1=已处理，2=已回滚',
    `parent_id`     BIGINT       NULL     DEFAULT NULL               COMMENT '指向原日志 ID（追问续写 / 修改 / 撤销）',
    `created_at`    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP  COMMENT '创建时间',
    `updated_at`    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP
                                           ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
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


-- ============================================================================
-- 执行校验：预期 9 张表、11 条外键约束
--   SELECT TABLE_NAME, TABLE_COMMENT FROM information_schema.TABLES
--    WHERE TABLE_SCHEMA = 'bookkeeping_fastapi' ORDER BY TABLE_NAME;
--   SELECT CONSTRAINT_NAME, TABLE_NAME, REFERENCED_TABLE_NAME
--     FROM information_schema.KEY_COLUMN_USAGE
--    WHERE TABLE_SCHEMA = 'bookkeeping_fastapi' AND REFERENCED_TABLE_NAME IS NOT NULL;
--
-- 种子数据（默认管理员 admin/123456、16 条系统预设分类、8 条 FAQ）
-- 参见 sql/init_mysql.sql「四、初始化数据」节，本文件只含 DDL。
-- ============================================================================
