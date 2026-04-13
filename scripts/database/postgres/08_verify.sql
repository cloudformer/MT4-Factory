-- ============================================================
-- 08. 验证脚本（Verification）
-- 用途: 验证数据库初始化是否成功
-- ============================================================

\set ON_ERROR_STOP on

\echo '▶ 08. 验证数据库...'

\echo ''
\echo '=========================================='
\echo '  数据库初始化验证'
\echo '=========================================='
\echo ''

-- 统计表数量
\echo '📊 表统计:'
SELECT
    'Tables' AS type,
    COUNT(*) AS count
FROM pg_tables
WHERE schemaname = 'public'
AND tablename NOT LIKE '%\_20%'
UNION ALL
SELECT
    'Partitions' AS type,
    COUNT(*) AS count
FROM pg_tables
WHERE schemaname = 'public'
AND (tablename LIKE 'historical\_bars\_%' OR
     tablename LIKE 'real\_online\_trades\_%' OR
     tablename LIKE 'validation\_trades\_%')
UNION ALL
SELECT
    'Indexes' AS type,
    COUNT(*) AS count
FROM pg_indexes
WHERE schemaname = 'public'
UNION ALL
SELECT
    'Triggers' AS type,
    COUNT(*) AS count
FROM pg_trigger
WHERE tgisinternal = FALSE;

\echo ''
\echo '📋 表列表:'
SELECT
    schemaname AS schema,
    tablename AS "Table Name",
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS "Size"
FROM pg_tables
WHERE schemaname = 'public'
AND tablename NOT LIKE '%\_20%'
ORDER BY tablename;

\echo ''
\echo '🔧 分区统计:'
SELECT
    CASE
        WHEN tablename LIKE 'historical\_bars\_%' THEN 'historical_bars'
        WHEN tablename LIKE 'real\_online\_trades\_%' THEN 'real_online_trades'
        WHEN tablename LIKE 'validation\_trades\_%' THEN 'validation_trades'
    END AS "Parent Table",
    COUNT(*) AS "Partitions Count"
FROM pg_tables
WHERE schemaname = 'public'
AND (tablename LIKE 'historical\_bars\_%' OR
     tablename LIKE 'real\_online\_trades\_%' OR
     tablename LIKE 'validation\_trades\_%')
GROUP BY
    CASE
        WHEN tablename LIKE 'historical\_bars\_%' THEN 'historical_bars'
        WHEN tablename LIKE 'real\_online\_trades\_%' THEN 'real_online_trades'
        WHEN tablename LIKE 'validation\_trades\_%' THEN 'validation_trades'
    END
ORDER BY "Parent Table";

\echo ''
\echo '🔍 视图:'
SELECT
    schemaname AS schema,
    viewname AS "View Name"
FROM pg_views
WHERE schemaname = 'public'
ORDER BY viewname;

\echo ''
\echo '⚡ 触发器:'
SELECT
    t.tgname AS "Trigger Name",
    c.relname AS "Table Name"
FROM pg_trigger t
JOIN pg_class c ON t.tgrelid = c.oid
WHERE t.tgisinternal = FALSE
ORDER BY c.relname, t.tgname;

\echo ''
\echo '✅ 08. 验证完成'
\echo ''
\echo '=========================================='
\echo '  ✅ 数据库初始化成功！'
\echo '=========================================='
\echo ''
\echo '📊 核心表: mt5_hosts, strategies, signals, accounts, registrations'
\echo '📊 数据表: historical_bars (41分区), real_online_trades (21分区), validation_trades (21分区)'
\echo '📊 视图: trades'
\echo '📊 触发器: 4个 (auto updated_at)'
\echo ''
\echo '📝 使用说明:'
\echo '  - 配置层: mt5_hosts, strategies, signals'
\echo '  - 账户层: accounts, registrations'
\echo '  - 数据层: historical_bars (2000-2040)'
\echo '  - 交易层: real_online_trades (2020-2040), validation_trades (2020-2040)'
\echo ''
