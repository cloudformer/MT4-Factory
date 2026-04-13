-- ============================================================
-- MT4-Factory PostgreSQL 主初始化脚本
-- 版本: V1.0.0
-- 用途: 自动执行所有初始化脚本
-- ============================================================
--
-- 执行方式:
--   psql -U mt4factory -d mt4factory -f 00_run_all.sql
--
-- 或 Docker:
--   docker exec -i mt4-factory-postgres psql -U mt4factory -d mt4factory < 00_run_all.sql
--
-- ============================================================

\set ON_ERROR_STOP on
\timing on

\echo '========================================'
\echo '  MT4-Factory 数据库初始化'
\echo '========================================'
\echo ''

\ir 01_init.sql
\ir 02_create_config_tables.sql
\ir 03_create_account_tables.sql
\ir 04_create_historical_tables.sql
\ir 05_create_trade_tables.sql
\ir 06_create_validation_tables.sql
\ir 07_create_triggers.sql
\ir 08_verify.sql

\echo ''
\echo '========================================'
\echo '  ✅ 所有初始化脚本执行完成！'
\echo '========================================'
\echo ''
