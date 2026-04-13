-- ============================================================
-- 配置层：3张表
-- - mt5_hosts: MT5主机配置
-- - strategies: 策略代码+性能（含evaluation_params）
-- - signals: 信号记录
-- ============================================================

-- MT5主机配置
CREATE TABLE IF NOT EXISTS mt5_hosts (
    id VARCHAR(32) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    host_type VARCHAR(20) NOT NULL CHECK (host_type IN ('demo', 'real', 'validator')),
    host VARCHAR(255) NOT NULL,
    port INTEGER NOT NULL DEFAULT 9090,
    api_key VARCHAR(255),
    timeout INTEGER DEFAULT 10,
    login INTEGER,
    password VARCHAR(255),
    server VARCHAR(255),
    use_investor INTEGER DEFAULT 1,  -- SQLite: BOOLEAN = INTEGER
    enabled INTEGER DEFAULT 1,       -- SQLite: BOOLEAN = INTEGER
    weight REAL DEFAULT 1.0 CHECK (weight >= 0),
    tags TEXT,  -- SQLite: JSONB = TEXT
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
    status VARCHAR(9) NOT NULL DEFAULT 'candidate' CHECK (status IN ('candidate', 'active', 'archived')),
    performance TEXT,  -- SQLite: JSONB = TEXT, 包含evaluation_params
    params TEXT,       -- SQLite: JSONB = TEXT
    mt5_host_id VARCHAR(32),

    -- Validator验证结果
    last_validation_time TIMESTAMP,
    validation_win_rate REAL CHECK (validation_win_rate BETWEEN 0 AND 1),
    validation_total_return REAL,
    validation_total_trades INTEGER CHECK (validation_total_trades >= 0),
    validation_sharpe_ratio REAL,
    validation_max_drawdown REAL CHECK (validation_max_drawdown >= 0),
    validation_profit_factor REAL CHECK (validation_profit_factor >= 0),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,

    FOREIGN KEY (mt5_host_id) REFERENCES mt5_hosts(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_strategies_status ON strategies(status);
CREATE INDEX IF NOT EXISTS idx_strategies_name ON strategies(name);
CREATE INDEX IF NOT EXISTS idx_strategies_mt5_host ON strategies(mt5_host_id);
CREATE INDEX IF NOT EXISTS idx_strategies_validation_time ON strategies(last_validation_time DESC);

-- 信号表
CREATE TABLE IF NOT EXISTS signals (
    id VARCHAR(32) PRIMARY KEY,
    strategy_id VARCHAR(32) NOT NULL,
    symbol VARCHAR(10) NOT NULL,
    direction VARCHAR(4) NOT NULL CHECK (direction IN ('buy', 'sell')),
    volume DECIMAL(10, 2) NOT NULL CHECK (volume > 0),
    sl DECIMAL(10, 5),
    tp DECIMAL(10, 5),
    status VARCHAR(9) NOT NULL CHECK (status IN ('pending', 'executed', 'failed', 'cancelled')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,

    FOREIGN KEY (strategy_id) REFERENCES strategies(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_signals_strategy_id ON signals(strategy_id);
CREATE INDEX IF NOT EXISTS idx_signals_status ON signals(status);
CREATE INDEX IF NOT EXISTS idx_signals_created ON signals(created_at DESC);

SELECT '✓ 配置层创建完成：3张表' AS progress;
