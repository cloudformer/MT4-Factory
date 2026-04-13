-- ============================================================
-- MT4-Factory SQLite 初始化脚本
-- Mac开发环境专用（不支持分区表）
-- ============================================================

-- ============================================================
-- 1. 全局配置层
-- ============================================================

-- MT5主机配置
CREATE TABLE IF NOT EXISTS mt5_hosts (
    id VARCHAR(32) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    host_type VARCHAR(20) NOT NULL,
    host VARCHAR(255) NOT NULL,
    port INTEGER NOT NULL DEFAULT 9090,
    api_key VARCHAR(255),
    timeout INTEGER DEFAULT 10,
    login INTEGER,
    password VARCHAR(255),
    server VARCHAR(255),
    use_investor BOOLEAN DEFAULT 1,
    enabled BOOLEAN DEFAULT 1,
    weight REAL DEFAULT 1.0,
    tags TEXT,
    notes VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_mt5_hosts_enabled ON mt5_hosts(enabled);
CREATE INDEX IF NOT EXISTS idx_mt5_hosts_type ON mt5_hosts(host_type);

-- 策略表
CREATE TABLE IF NOT EXISTS strategies (
    id VARCHAR(32) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    code TEXT NOT NULL,
    status VARCHAR(9) NOT NULL DEFAULT 'candidate',
    performance TEXT,
    params TEXT,
    mt5_host_id VARCHAR(32),
    last_validation_time TIMESTAMP,
    validation_win_rate REAL,
    validation_total_return REAL,
    validation_total_trades INTEGER,
    validation_sharpe_ratio REAL,
    validation_max_drawdown REAL,
    validation_profit_factor REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    FOREIGN KEY (mt5_host_id) REFERENCES mt5_hosts(id)
);

CREATE INDEX IF NOT EXISTS idx_strategies_status ON strategies(status);
CREATE INDEX IF NOT EXISTS idx_strategies_name ON strategies(name);
CREATE INDEX IF NOT EXISTS idx_strategies_mt5_host ON strategies(mt5_host_id);

-- 信号表
CREATE TABLE IF NOT EXISTS signals (
    id VARCHAR(32) PRIMARY KEY,
    strategy_id VARCHAR(32) NOT NULL,
    symbol VARCHAR(10) NOT NULL,
    direction VARCHAR(4) NOT NULL,
    volume DECIMAL(10, 2) NOT NULL,
    sl DECIMAL(10, 5),
    tp DECIMAL(10, 5),
    status VARCHAR(9) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    FOREIGN KEY (strategy_id) REFERENCES strategies(id)
);

CREATE INDEX IF NOT EXISTS idx_signals_strategy_id ON signals(strategy_id);
CREATE INDEX IF NOT EXISTS idx_signals_status ON signals(status);

-- ============================================================
-- 2. 统一账户层
-- ============================================================

CREATE TABLE IF NOT EXISTS accounts (
    id VARCHAR(32) PRIMARY KEY,
    login INTEGER NOT NULL UNIQUE,
    account_type VARCHAR(20) NOT NULL,
    mt5_host_id VARCHAR(32),
    server VARCHAR(255) NOT NULL,
    company VARCHAR(255),
    name VARCHAR(255),
    currency VARCHAR(10) DEFAULT 'USD',
    leverage INTEGER DEFAULT 100,
    initial_balance REAL NOT NULL,
    current_balance REAL,
    current_equity REAL,
    is_active BOOLEAN DEFAULT 1,
    trade_allowed BOOLEAN DEFAULT 1,
    risk_config TEXT,
    notes VARCHAR(500),
    start_time TIMESTAMP,
    last_sync_time TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (mt5_host_id) REFERENCES mt5_hosts(id)
);

CREATE INDEX IF NOT EXISTS idx_accounts_type ON accounts(account_type);
CREATE INDEX IF NOT EXISTS idx_accounts_login ON accounts(login);
CREATE INDEX IF NOT EXISTS idx_accounts_active ON accounts(is_active);

-- 策略注册表
CREATE TABLE IF NOT EXISTS registrations (
    id VARCHAR(32) PRIMARY KEY,
    strategy_id VARCHAR(32) NOT NULL,
    account_id VARCHAR(32) NOT NULL,
    allocation_percentage REAL,
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (strategy_id) REFERENCES strategies(id),
    FOREIGN KEY (account_id) REFERENCES accounts(id),
    UNIQUE (strategy_id, account_id)
);

CREATE INDEX IF NOT EXISTS idx_registrations_strategy ON registrations(strategy_id);
CREATE INDEX IF NOT EXISTS idx_registrations_account ON registrations(account_id);

-- ============================================================
-- 3. 历史数据层（无分区）
-- ============================================================

CREATE TABLE IF NOT EXISTS historical_bars (
    symbol VARCHAR(20) NOT NULL,
    timeframe VARCHAR(10) NOT NULL,
    time TIMESTAMP NOT NULL,
    open DECIMAL(10, 5) NOT NULL,
    high DECIMAL(10, 5) NOT NULL,
    low DECIMAL(10, 5) NOT NULL,
    close DECIMAL(10, 5) NOT NULL,
    volume INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    PRIMARY KEY (time, symbol, timeframe)
);

CREATE INDEX IF NOT EXISTS idx_historical_bars_lookup
    ON historical_bars(symbol, timeframe, time DESC);

-- ============================================================
-- 4. 真实交易层（无分区）
-- ============================================================

CREATE TABLE IF NOT EXISTS real_online_trades (
    id VARCHAR(32) PRIMARY KEY,
    ticket INTEGER NOT NULL,
    account_id VARCHAR(32),
    signal_id VARCHAR(32),
    strategy_id VARCHAR(32),
    symbol VARCHAR(10) NOT NULL,
    direction VARCHAR(4) NOT NULL,
    volume DECIMAL(10, 2) NOT NULL,
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
    FOREIGN KEY (account_id) REFERENCES accounts(id),
    FOREIGN KEY (strategy_id) REFERENCES strategies(id)
);

CREATE INDEX IF NOT EXISTS idx_real_online_trades_account
    ON real_online_trades(account_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_real_online_trades_strategy
    ON real_online_trades(strategy_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_real_online_trades_symbol
    ON real_online_trades(symbol, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_real_online_trades_ticket
    ON real_online_trades(ticket);

-- ============================================================
-- 5. 验证交易层（无分区）
-- ============================================================

-- 回测批次表
CREATE TABLE IF NOT EXISTS validation_backtest_runs (
    id VARCHAR(32) PRIMARY KEY,
    strategy_id VARCHAR(32),
    symbol VARCHAR(20) NOT NULL,
    timeframe VARCHAR(10) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    bars_count INTEGER,
    total_trades INTEGER DEFAULT 0,
    total_profit DECIMAL(10, 2) DEFAULT 0,
    win_rate DECIMAL(5, 2) DEFAULT 0,
    max_drawdown DECIMAL(10, 2) DEFAULT 0,
    sharpe_ratio DECIMAL(5, 2),
    run_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    duration_seconds INTEGER,
    status VARCHAR(20) DEFAULT 'RUNNING',
    FOREIGN KEY (strategy_id) REFERENCES strategies(id)
);

CREATE INDEX IF NOT EXISTS idx_validation_backtest_runs_strategy
    ON validation_backtest_runs(strategy_id);

-- 验证交易表
CREATE TABLE IF NOT EXISTS validation_trades (
    id VARCHAR(32) PRIMARY KEY,
    execution_type VARCHAR(20) NOT NULL,
    ticket INTEGER,
    strategy_id VARCHAR(32),
    account_id VARCHAR(32),
    backtest_run_id VARCHAR(32),
    symbol VARCHAR(20) NOT NULL,
    direction VARCHAR(10) NOT NULL,
    volume DECIMAL(10, 2) NOT NULL,
    open_price DECIMAL(10, 5) NOT NULL,
    close_price DECIMAL(10, 5),
    sl DECIMAL(10, 5),
    tp DECIMAL(10, 5),
    profit DECIMAL(10, 2) DEFAULT 0,
    commission DECIMAL(10, 2) DEFAULT 0,
    swap DECIMAL(10, 2) DEFAULT 0,
    open_time TIMESTAMP NOT NULL,
    close_time TIMESTAMP,
    status VARCHAR(20) DEFAULT 'OPEN',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (strategy_id) REFERENCES strategies(id),
    FOREIGN KEY (account_id) REFERENCES accounts(id),
    FOREIGN KEY (backtest_run_id) REFERENCES validation_backtest_runs(id)
);

CREATE INDEX IF NOT EXISTS idx_validation_trades_type
    ON validation_trades(execution_type, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_validation_trades_strategy
    ON validation_trades(strategy_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_validation_trades_backtest
    ON validation_trades(backtest_run_id);
CREATE INDEX IF NOT EXISTS idx_validation_trades_account
    ON validation_trades(account_id, created_at DESC);

-- ============================================================
-- 6. 兼容性视图（Dashboard UI使用）
-- ============================================================

-- trades视图：用于Dashboard统计（指向real_online_trades）
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
    NULL AS sl,
    NULL AS tp,
    profit,
    NULL AS commission,
    NULL AS swap,
    open_time,
    close_time,
    created_at
FROM real_online_trades;

-- ============================================================
-- 初始化完成
-- ============================================================

SELECT '✅ SQLite数据库初始化完成' AS status;
SELECT 'Mac开发环境（无分区）' AS environment;
