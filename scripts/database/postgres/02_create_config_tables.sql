-- ============================================================
-- 02. 配置层表（Config Layer）
-- 用途: MT5主机、策略、信号
-- ============================================================

\set ON_ERROR_STOP on

\echo '▶ 02. 创建配置层表...'

BEGIN;

-- MT5主机配置
CREATE TABLE IF NOT EXISTS mt5_hosts (
    id VARCHAR(32) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    host_type VARCHAR(20) NOT NULL CHECK (host_type IN ('demo', 'real')),
    host VARCHAR(255) NOT NULL,
    port INTEGER NOT NULL DEFAULT 9090 CHECK (port > 0 AND port < 65536),
    api_key VARCHAR(255),
    timeout INTEGER DEFAULT 10 CHECK (timeout > 0),
    login INTEGER,
    password VARCHAR(255),
    server VARCHAR(255),
    use_investor BOOLEAN DEFAULT TRUE,
    enabled BOOLEAN DEFAULT TRUE,
    weight FLOAT DEFAULT 1.0 CHECK (weight >= 0),
    tags TEXT,
    notes VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_mt5_hosts_enabled ON mt5_hosts(enabled);
CREATE INDEX IF NOT EXISTS idx_mt5_hosts_type ON mt5_hosts(host_type);
CREATE INDEX IF NOT EXISTS idx_mt5_hosts_weight ON mt5_hosts(weight DESC) WHERE enabled = TRUE;

COMMENT ON TABLE mt5_hosts IS 'MT5 API Bridge连接配置';
COMMENT ON COLUMN mt5_hosts.host_type IS 'demo=验证节点 | real=交易节点';
COMMENT ON COLUMN mt5_hosts.weight IS '负载均衡权重';

-- 策略表
CREATE TABLE IF NOT EXISTS strategies (
    id VARCHAR(32) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    code TEXT NOT NULL,
    status VARCHAR(9) NOT NULL DEFAULT 'candidate' CHECK (status IN ('candidate', 'active', 'archived')),
    performance JSONB,
    params JSONB,
    mt5_host_id VARCHAR(32),

    -- Validator验证结果
    last_validation_time TIMESTAMP,
    validation_win_rate FLOAT CHECK (validation_win_rate BETWEEN 0 AND 1),
    validation_total_return FLOAT,
    validation_total_trades INTEGER CHECK (validation_total_trades >= 0),
    validation_sharpe_ratio FLOAT,
    validation_max_drawdown FLOAT CHECK (validation_max_drawdown BETWEEN 0 AND 1),
    validation_profit_factor FLOAT CHECK (validation_profit_factor >= 0),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,

    CONSTRAINT fk_strategies_mt5_host FOREIGN KEY (mt5_host_id)
        REFERENCES mt5_hosts(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_strategies_status ON strategies(status);
CREATE INDEX IF NOT EXISTS idx_strategies_name ON strategies(name);
CREATE INDEX IF NOT EXISTS idx_strategies_mt5_host ON strategies(mt5_host_id);
CREATE INDEX IF NOT EXISTS idx_strategies_validation_time ON strategies(last_validation_time DESC);
CREATE INDEX IF NOT EXISTS idx_strategies_performance ON strategies USING GIN (performance);

COMMENT ON TABLE strategies IS '策略实例（含Registration状态）';
COMMENT ON COLUMN strategies.performance IS 'JSON: 包含 evaluation_params, total_return, sharpe_ratio 等';

-- 信号表
CREATE TABLE IF NOT EXISTS signals (
    id VARCHAR(32) PRIMARY KEY,
    strategy_id VARCHAR(32) NOT NULL,
    symbol VARCHAR(10) NOT NULL,
    direction VARCHAR(4) NOT NULL CHECK (direction IN ('buy', 'sell')),
    volume DECIMAL(10, 2) NOT NULL CHECK (volume > 0),
    sl DECIMAL(10, 5),
    tp DECIMAL(10, 5),
    status VARCHAR(9) NOT NULL CHECK (status IN ('pending', 'executed', 'cancelled', 'expired')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,

    CONSTRAINT fk_signals_strategy FOREIGN KEY (strategy_id)
        REFERENCES strategies(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_signals_strategy_id ON signals(strategy_id);
CREATE INDEX IF NOT EXISTS idx_signals_status ON signals(status);
CREATE INDEX IF NOT EXISTS idx_signals_created_at ON signals(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_signals_symbol ON signals(symbol);

COMMENT ON TABLE signals IS '交易信号';

COMMIT;

\echo '✅ 02. 配置层表创建完成 (mt5_hosts, strategies, signals)'
\echo ''
