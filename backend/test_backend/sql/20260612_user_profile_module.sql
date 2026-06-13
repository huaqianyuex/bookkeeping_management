-- 用户自定义模块数据库变更
-- 适用：MySQL 8+

ALTER TABLE user
    ADD COLUMN avatar_url VARCHAR(255) NULL COMMENT '头像访问地址' AFTER password;

-- 如现网缺少 role 字段，可取消注释执行
-- ALTER TABLE user
--     ADD COLUMN role TINYINT NOT NULL DEFAULT 0 COMMENT '角色：0=普通用户，1=管理员' AFTER avatar_url;

-- 可选：限制用户名长度（如已存在可忽略）
-- ALTER TABLE user
--     MODIFY COLUMN username VARCHAR(20) NOT NULL COMMENT '用户名';
