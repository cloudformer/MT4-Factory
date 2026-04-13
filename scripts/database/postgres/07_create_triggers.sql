-- ============================================================
-- 07. 触发器（Triggers）
-- 用途: 自动更新 updated_at 字段
-- ============================================================

\set ON_ERROR_STOP on

\echo '▶ 07. 创建触发器...'

BEGIN;

-- 自动更新 updated_at 字段的函数
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION update_updated_at_column() IS '自动更新updated_at字段触发器函数';

-- 为需要的表添加触发器
DO $$
DECLARE
    tbl TEXT;
    tables_to_trigger TEXT[] := ARRAY['mt5_hosts', 'strategies', 'accounts', 'registrations'];
BEGIN
    FOREACH tbl IN ARRAY tables_to_trigger
    LOOP
        -- 检查表是否存在且有 updated_at 字段
        IF EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name = tbl
            AND column_name = 'updated_at'
            AND table_schema = 'public'
        ) THEN
            -- 删除旧触发器（如果存在）
            EXECUTE format(
                'DROP TRIGGER IF EXISTS trigger_update_%s_updated_at ON %I',
                tbl, tbl
            );

            -- 创建新触发器
            EXECUTE format(
                'CREATE TRIGGER trigger_update_%s_updated_at
                 BEFORE UPDATE ON %I
                 FOR EACH ROW
                 EXECUTE FUNCTION update_updated_at_column()',
                tbl, tbl
            );

            RAISE NOTICE '✅ 触发器已创建: trigger_update_%_updated_at', tbl;
        END IF;
    END LOOP;
END $$;

COMMIT;

\echo '✅ 07. 触发器创建完成 (mt5_hosts, strategies, accounts, registrations)'
\echo ''
