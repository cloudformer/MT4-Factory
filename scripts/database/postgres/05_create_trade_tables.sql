-- ============================================================
-- 05. 真实交易层（Trade Layer）
-- 用途: 真实交易记录（20年分区）+ 兼容视图
-- ============================================================

\set ON_ERROR_STOP on

\echo '▶ 05. 创建真实交易层...'

BEGIN;

-- 真实交易表（分区）
CREATE TABLE IF NOT EXISTS real_online_trades (
    id VARCHAR(32),
    ticket BIGINT NOT NULL CHECK (ticket > 0),
    account_id VARCHAR(32),
    signal_id VARCHAR(32),
    strategy_id VARCHAR(32),
    symbol VARCHAR(10) NOT NULL,
    direction VARCHAR(4) NOT NULL CHECK (direction IN ('buy', 'sell')),
    volume DECIMAL(10, 2) NOT NULL CHECK (volume > 0),
    open_price DECIMAL(10, 5) CHECK (open_price > 0),
    close_price DECIMAL(10, 5) CHECK (close_price > 0),
    sl DECIMAL(10, 5),
    tp DECIMAL(10, 5),
    profit DECIMAL(10, 2),
    commission DECIMAL(10, 2) DEFAULT 0,
    swap DECIMAL(10, 2) DEFAULT 0,
    open_time TIMESTAMP,
    close_time TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    PRIMARY KEY (id, created_at),

    CONSTRAINT fk_real_trades_account FOREIGN KEY (account_id)
        REFERENCES accounts(id) ON DELETE SET NULL,
    CONSTRAINT fk_real_trades_strategy FOREIGN KEY (strategy_id)
        REFERENCES strategies(id) ON DELETE SET NULL,
    CHECK (close_time IS NULL OR close_time >= open_time)
) PARTITION BY RANGE (created_at);

-- 创建2020-2040年分区（21年）
DO $$
DECLARE
    yr INT;
BEGIN
    FOR yr IN 2020..2040 LOOP
        EXECUTE format(
            'CREATE TABLE IF NOT EXISTS real_online_trades_%s
             PARTITION OF real_online_trades
             FOR VALUES FROM (%L) TO (%L)',
            yr, yr || '-01-01', (yr + 1) || '-01-01'
        );
    END LOOP;
END $$;

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_real_trades_account ON real_online_trades(account_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_real_trades_strategy ON real_online_trades(strategy_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_real_trades_symbol ON real_online_trades(symbol, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_real_trades_ticket ON real_online_trades(ticket);

COMMENT ON TABLE real_online_trades IS '真实线上交易记录（必须有ticket，关联account_type=REAL，20年分区）';

-- 兼容性视图（Dashboard使用）
CREATE OR REPLACE VIEW trades AS
SELECT
    id, account_id, signal_id, strategy_id, ticket,
    symbol, direction, volume,
    open_price, close_price, sl, tp,
    profit, commission, swap,
    open_time, close_time, created_at
FROM real_online_trades;

COMMENT ON VIEW trades IS '兼容性视图：Dashboard UI使用，指向真实交易表';

COMMIT;

\echo '✅ 05. 真实交易层创建完成 (real_online_trades: 2020-2040, 21个分区 + trades视图)'
\echo ''
