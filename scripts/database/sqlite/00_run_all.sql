-- ============================================================
-- MT4-Factory SQLite 初始化主脚本
-- Mac开发环境专用（不支持分区表）
-- ============================================================

.echo on

-- 执行顺序
.read 01_create_config_tables.sql
.read 02_create_account_tables.sql
.read 03_create_historical_tables.sql
.read 04_create_trade_tables.sql
.read 05_create_validation_tables.sql
.read 06_create_views.sql
.read 07_verify.sql

SELECT '✅ SQLite数据库初始化完成' AS status;
