-- ============================================================
-- 真实交易层：1张表（无分区）
-- - real_online_trades: 真实订单
-- ============================================================

CREATE TABLE IF NOT EXISTS real_online_trades (
    id VARCHAR(32) PRIMARY KEY,
    ticket INTEGER NOT NULL CHECK (ticket > 0),
    account_id VARCHAR(32),
    signal_id VARCHAR(32),
    strategy_id VARCHAR(32),
    symbol VARCHAR(10) NOT NULL,
    direction VARCHAR(4) NOT NULL CHECK (direction IN ('buy', 'sell')),
    volume DECIMAL(10, 2) NOT NULL CHECK (volume > 0),
    open_price DECIMAL(10, 5),
    close_price DECIMAL(10, 5),
    sl DECIMAL(10, 5),
    tp DECIMAL(10, 5),
    profit DECIMAL(10, 2),
    commission DECIMAL(10, 2) DEFAULT 0,
    swap DECIMAL(10, 2) DEFAULT 0,
    open_time TIMESTAMP,
    close_time TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,

    FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE SET NULL,
    FOREIGN KEY (strategy_id) REFERENCES strategies(id) ON DELETE SET NULL,
    FOREIGN KEY (signal_id) REFERENCES signals(id) ON DELETE SET NULL,

    CHECK (close_time IS NULL OR close_time >= open_time)
);

CREATE INDEX IF NOT EXISTS idx_real_online_trades_account
    ON real_online_trades(account_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_real_online_trades_strategy
    ON real_online_trades(strategy_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_real_online_trades_symbol
    ON real_online_trades(symbol, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_real_online_trades_ticket
    ON real_online_trades(ticket);
CREATE INDEX IF NOT EXISTS idx_real_online_trades_signal
    ON real_online_trades(signal_id);

SELECT '✓ 真实交易层创建完成：1张表（无分区）' AS progress;
