-- ============================================================
-- 验证查询
-- ============================================================

.mode column
.headers on
.width 30 10

SELECT '========================================' AS separator;
SELECT '📊 SQLite数据库结构验证' AS title;
SELECT '========================================' AS separator;

-- 统计表数量
SELECT
    COUNT(*) AS total_tables,
    'Main Tables' AS category
FROM sqlite_master
WHERE type = 'table' AND name NOT LIKE 'sqlite_%';

-- 统计视图数量
SELECT
    COUNT(*) AS total_views,
    'Views' AS category
FROM sqlite_master
WHERE type = 'view';

-- 统计索引数量
SELECT
    COUNT(*) AS total_indexes,
    'Indexes' AS category
FROM sqlite_master
WHERE type = 'index' AND name NOT LIKE 'sqlite_%';

SELECT '========================================' AS separator;
SELECT '📋 所有表' AS section;
SELECT '========================================' AS separator;

-- 列出所有表
SELECT
    name AS table_name,
    type AS object_type
FROM sqlite_master
WHERE type IN ('table', 'view')
    AND name NOT LIKE 'sqlite_%'
ORDER BY
    CASE type
        WHEN 'table' THEN 1
        WHEN 'view' THEN 2
    END,
    name;

SELECT '========================================' AS separator;
SELECT '✅ 验证完成' AS status;
SELECT '========================================' AS separator;
