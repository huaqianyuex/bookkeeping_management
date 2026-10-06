-- ============================================================================
-- 存量库升级：ai_bookkeeping_logs 增加 source 列（语音记账功能）
--   对应代码：fast_backend -fwature-expansion-version/models/bookkeeping.py
--   依据：docs/语音记账实施指南.md §3.1
--
-- 说明：
--   * server_default 'text' 让存量行自动回填为「手输/文本记账」，
--     NOT NULL 加列不会失败；
--   * AFTER user_id 仅为可读性，不影响现有索引
--     （idx_abk_user_recent / idx_abk_dedup 只用 user_id / dedup_hash / created_at）；
--   * 新库直接执行 init_mysql.sql / create_tables_from_models.sql 即可，
--     无需本脚本。
-- ============================================================================

USE `bookkeeping_fastapi`;

ALTER TABLE `ai_bookkeeping_logs`
  ADD COLUMN `source` VARCHAR(10) NOT NULL DEFAULT 'text'
    COMMENT '来源：text=手输/文本记账，voice=语音记账'
  AFTER `user_id`;
