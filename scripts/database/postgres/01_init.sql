-- ============================================================
-- 01. 环境初始化
-- 用途: 创建扩展、设置时区、数据库配置
-- ============================================================

\set ON_ERROR_STOP on

\echo '▶ 01. 环境初始化...'

BEGIN;

-- 启用必要的扩展
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";

-- 设置时区
SET timezone = 'UTC';

-- 数据库注释
DO $$
BEGIN
    EXECUTE 'COMMENT ON DATABASE ' || current_database() ||
            ' IS ''MT4-Factory Trading System Database - v1.0.0''';
END $$;

COMMIT;

\echo '✅ 01. 环境初始化完成'
\echo ''
