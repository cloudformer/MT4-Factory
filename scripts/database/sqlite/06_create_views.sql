-- ============================================================
-- 兼容性视图：1个视图
-- - trades: Dashboard统计视图（指向real_online_trades）
-- ============================================================

DROP VIEW IF EXISTS trades;

CREATE VIEW IF NOT EXISTS trades AS
SELECT
    id,
    account_id,
    signal_id,
    strategy_id,
    ticket,
    symbol,
    direction,
    volume,
    open_price,
    close_price,
    sl,
    tp,
    profit,
    commission,
    swap,
    open_time,
    close_time,
    created_at
FROM real_online_trades;

SELECT '✓ 视图创建完成：1个视图' AS progress;
