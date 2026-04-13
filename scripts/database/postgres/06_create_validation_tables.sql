-- ============================================================
-- 06. 验证交易层（Validation Layer）
-- 用途: 回测批次 + 验证交易记录（20年分区）
-- ============================================================

\set ON_ERROR_STOP on

\echo '▶ 06. 创建验证交易层...'

BEGIN;

-- 回测批次表
CREATE TABLE IF NOT EXISTS validation_backtest_runs (
    id VARCHAR(32) PRIMARY KEY,
    strategy_id VARCHAR(32),
    symbol VARCHAR(20) NOT NULL,
    timeframe VARCHAR(10) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    bars_count INT CHECK (bars_count >= 0),
    total_trades INT DEFAULT 0 CHECK (total_trades >= 0),
    total_profit DECIMAL(10, 2) DEFAULT 0,
    win_rate DECIMAL(5, 2) DEFAULT 0 CHECK (win_rate BETWEEN 0 AND 100),
    max_drawdown DECIMAL(10, 2) DEFAULT 0,
    sharpe_ratio DECIMAL(5, 2),
    run_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    duration_seconds INT CHECK (duration_seconds >= 0),
    status VARCHAR(20) DEFAULT 'RUNNING' CHECK (status IN ('RUNNING', 'COMPLETED', 'FAILED', 'CANCELLED')),

    CONSTRAINT fk_backtest_strategy FOREIGN KEY (strategy_id)
        REFERENCES strategies(id) ON DELETE CASCADE,
    CHECK (end_date >= start_date)
);

CREATE INDEX IF NOT EXISTS idx_backtest_runs_strategy ON validation_backtest_runs(strategy_id);
CREATE INDEX IF NOT EXISTS idx_backtest_runs_status ON validation_backtest_runs(status);
CREATE INDEX IF NOT EXISTS idx_backtest_runs_run_at ON validation_backtest_runs(run_at DESC);

COMMENT ON TABLE validation_backtest_runs IS '回测批次元数据（统计汇总）';

-- 验证交易表（分区）
CREATE TABLE IF NOT EXISTS validation_trades (
    id VARCHAR(32),
    execution_type VARCHAR(20) NOT NULL CHECK (execution_type IN ('LIVE', 'BACKTEST')),
    ticket BIGINT,
    strategy_id VARCHAR(32),
    account_id VARCHAR(32),
    backtest_run_id VARCHAR(32),
    symbol VARCHAR(20) NOT NULL,
    direction VARCHAR(10) NOT NULL CHECK (direction IN ('buy', 'sell')),
    volume DECIMAL(10, 2) NOT NULL CHECK (volume > 0),
    open_price DECIMAL(10, 5) NOT NULL CHECK (open_price > 0),
    close_price DECIMAL(10, 5) CHECK (close_price > 0),
    sl DECIMAL(10, 5),
    tp DECIMAL(10, 5),
    profit DECIMAL(10, 2) DEFAULT 0,
    commission DECIMAL(10, 2) DEFAULT 0,
    swap DECIMAL(10, 2) DEFAULT 0,
    open_time TIMESTAMP NOT NULL,
    close_time TIMESTAMP,
    status VARCHAR(20) DEFAULT 'OPEN' CHECK (status IN ('OPEN', 'CLOSED', 'CANCELLED')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id, created_at),

    CONSTRAINT fk_validation_trades_strategy FOREIGN KEY (strategy_id)
        REFERENCES strategies(id) ON DELETE SET NULL,
    CONSTRAINT fk_validation_trades_account FOREIGN KEY (account_id)
        REFERENCES accounts(id) ON DELETE SET NULL,
    CONSTRAINT fk_validation_trades_backtest FOREIGN KEY (backtest_run_id)
        REFERENCES validation_backtest_runs(id) ON DELETE CASCADE,
    CONSTRAINT chk_live_has_ticket CHECK (
        execution_type != 'LIVE' OR (ticket IS NOT NULL AND account_id IS NOT NULL)
    ),
    CONSTRAINT chk_backtest_no_ticket CHECK (
        execution_type != 'BACKTEST' OR (ticket IS NULL AND backtest_run_id IS NOT NULL)
    ),
    CHECK (close_time IS NULL OR close_time >= open_time)
) PARTITION BY RANGE (created_at);

-- 创建2020-2040年分区（21年）
DO $$
DECLARE
    yr INT;
BEGIN
    FOR yr IN 2020..2040 LOOP
        EXECUTE format(
            'CREATE TABLE IF NOT EXISTS validation_trades_%s
             PARTITION OF validation_trades
             FOR VALUES FROM (%L) TO (%L)',
            yr, yr || '-01-01', (yr + 1) || '-01-01'
        );
    END LOOP;
END $$;

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_validation_trades_type ON validation_trades(execution_type, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_validation_trades_strategy ON validation_trades(strategy_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_validation_trades_backtest ON validation_trades(backtest_run_id);
CREATE INDEX IF NOT EXISTS idx_validation_trades_account ON validation_trades(account_id, created_at DESC);

COMMENT ON TABLE validation_trades IS '验证交易记录（LIVE有ticket关联DEMO账户，BACKTEST无ticket纯模拟，20年分区）';

COMMIT;

\echo '✅ 06. 验证交易层创建完成 (validation_backtest_runs, validation_trades: 2020-2040, 21个分区)'
\echo ''
