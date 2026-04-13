-- ============================================================
-- 验证层：2张表（无分区）
-- - validation_backtest_runs: 回测批次元数据
-- - validation_trades: 验证/回测交易
-- ============================================================

-- 回测批次表
CREATE TABLE IF NOT EXISTS validation_backtest_runs (
    id VARCHAR(32) PRIMARY KEY,
    strategy_id VARCHAR(32),
    symbol VARCHAR(20) NOT NULL,
    timeframe VARCHAR(10) NOT NULL CHECK (timeframe IN ('M1', 'M5', 'M15', 'M30', 'H1', 'H4', 'D1', 'W1', 'MN')),
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    bars_count INTEGER CHECK (bars_count >= 0),
    total_trades INTEGER DEFAULT 0 CHECK (total_trades >= 0),
    total_profit DECIMAL(10, 2) DEFAULT 0,
    win_rate DECIMAL(5, 2) DEFAULT 0 CHECK (win_rate BETWEEN 0 AND 100),
    max_drawdown DECIMAL(10, 2) DEFAULT 0 CHECK (max_drawdown >= 0),
    sharpe_ratio DECIMAL(5, 2),
    run_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    duration_seconds INTEGER CHECK (duration_seconds >= 0),
    status VARCHAR(20) DEFAULT 'RUNNING' CHECK (status IN ('RUNNING', 'COMPLETED', 'FAILED', 'CANCELLED')),

    FOREIGN KEY (strategy_id) REFERENCES strategies(id) ON DELETE CASCADE,

    CHECK (end_date >= start_date)
);

CREATE INDEX IF NOT EXISTS idx_validation_backtest_runs_strategy
    ON validation_backtest_runs(strategy_id);
CREATE INDEX IF NOT EXISTS idx_validation_backtest_runs_status
    ON validation_backtest_runs(status);
CREATE INDEX IF NOT EXISTS idx_validation_backtest_runs_time
    ON validation_backtest_runs(run_at DESC);

-- 验证交易表
CREATE TABLE IF NOT EXISTS validation_trades (
    id VARCHAR(32) PRIMARY KEY,
    execution_type VARCHAR(20) NOT NULL CHECK (execution_type IN ('LIVE', 'BACKTEST')),
    ticket INTEGER,
    strategy_id VARCHAR(32),
    account_id VARCHAR(32),
    backtest_run_id VARCHAR(32),
    symbol VARCHAR(20) NOT NULL,
    direction VARCHAR(10) NOT NULL CHECK (direction IN ('buy', 'sell')),
    volume DECIMAL(10, 2) NOT NULL CHECK (volume > 0),
    open_price DECIMAL(10, 5) NOT NULL,
    close_price DECIMAL(10, 5),
    sl DECIMAL(10, 5),
    tp DECIMAL(10, 5),
    profit DECIMAL(10, 2) DEFAULT 0,
    commission DECIMAL(10, 2) DEFAULT 0,
    swap DECIMAL(10, 2) DEFAULT 0,
    open_time TIMESTAMP NOT NULL,
    close_time TIMESTAMP,
    status VARCHAR(20) DEFAULT 'OPEN' CHECK (status IN ('OPEN', 'CLOSED', 'CANCELLED')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (strategy_id) REFERENCES strategies(id) ON DELETE CASCADE,
    FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE SET NULL,
    FOREIGN KEY (backtest_run_id) REFERENCES validation_backtest_runs(id) ON DELETE CASCADE,

    CHECK (close_time IS NULL OR close_time >= open_time),

    -- LIVE必须有ticket和account_id
    CHECK (execution_type != 'LIVE' OR (ticket IS NOT NULL AND account_id IS NOT NULL)),

    -- BACKTEST必须有backtest_run_id，不能有ticket
    CHECK (execution_type != 'BACKTEST' OR (backtest_run_id IS NOT NULL AND ticket IS NULL))
);

CREATE INDEX IF NOT EXISTS idx_validation_trades_type
    ON validation_trades(execution_type, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_validation_trades_strategy
    ON validation_trades(strategy_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_validation_trades_backtest
    ON validation_trades(backtest_run_id);
CREATE INDEX IF NOT EXISTS idx_validation_trades_account
    ON validation_trades(account_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_validation_trades_status
    ON validation_trades(status);

SELECT '✓ 验证层创建完成：2张表（无分区）' AS progress;
