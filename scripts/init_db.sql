-- ============================================================
-- MT4-Factory PostgreSQL 初始化脚本
-- 单Schema + 表前缀 + Table分区
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
    use_investor BOOLEAN DEFAULT TRUE,
    enabled BOOLEAN DEFAULT TRUE,
    weight FLOAT DEFAULT 1.0,
    tags TEXT,
    notes VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_mt5_hosts_enabled ON mt5_hosts(enabled);
CREATE INDEX idx_mt5_hosts_type ON mt5_hosts(host_type);

COMMENT ON TABLE mt5_hosts IS 'MT5 API Bridge连接配置';

-- 策略表
CREATE TABLE IF NOT EXISTS strategies (
    id VARCHAR(32) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    code TEXT NOT NULL,
    status VARCHAR(9) NOT NULL DEFAULT 'candidate',
    performance JSONB,
    params JSONB,
    mt5_host_id VARCHAR(32),
    last_validation_time TIMESTAMP,
    validation_win_rate FLOAT,
    validation_total_return FLOAT,
    validation_total_trades INTEGER,
    validation_sharpe_ratio FLOAT,
    validation_max_drawdown FLOAT,
    validation_profit_factor FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    FOREIGN KEY (mt5_host_id) REFERENCES mt5_hosts(id)
);

CREATE INDEX idx_strategies_status ON strategies(status);
CREATE INDEX idx_strategies_name ON strategies(name);
CREATE INDEX idx_strategies_mt5_host ON strategies(mt5_host_id);

COMMENT ON TABLE strategies IS '策略实例（含Registration状态）';

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

CREATE INDEX idx_signals_strategy_id ON signals(strategy_id);
CREATE INDEX idx_signals_status ON signals(status);

COMMENT ON TABLE signals IS '交易信号';

-- ============================================================
-- 2. 统一账户层（合并trading_accounts和validation_accounts）
-- ============================================================

CREATE TABLE IF NOT EXISTS accounts (
    id VARCHAR(32) PRIMARY KEY,
    login INTEGER NOT NULL UNIQUE,

    -- 账户类型（区分真实/验证）
    account_type VARCHAR(20) NOT NULL,
    -- 'REAL' - 真实交易账户（大资金）
    -- 'DEMO' - 验证账户（Demo或小资金）

    mt5_host_id VARCHAR(32) REFERENCES mt5_hosts(id),

    server VARCHAR(255) NOT NULL,
    company VARCHAR(255),
    name VARCHAR(255),
    currency VARCHAR(10) DEFAULT 'USD',
    leverage INTEGER DEFAULT 100,

    initial_balance FLOAT NOT NULL,
    current_balance FLOAT,
    current_equity FLOAT,

    is_active BOOLEAN DEFAULT TRUE,
    trade_allowed BOOLEAN DEFAULT TRUE,
    risk_config JSONB,
    notes VARCHAR(500),

    start_time TIMESTAMP,
    last_sync_time TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_accounts_type ON accounts(account_type);
CREATE INDEX idx_accounts_login ON accounts(login);
CREATE INDEX idx_accounts_active ON accounts(is_active);

COMMENT ON TABLE accounts IS '统一账户表（account_type区分REAL/DEMO）';

-- 策略注册表（Registration服务核心表）
CREATE TABLE IF NOT EXISTS registrations (
    id VARCHAR(32) PRIMARY KEY,

    -- 激活策略与真实账户的绑定
    strategy_id VARCHAR(32) NOT NULL,
    account_id VARCHAR(32) NOT NULL,

    -- 资金分配比例（可选）
    allocation_percentage FLOAT,

    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT uix_strategy_account UNIQUE (strategy_id, account_id),
    FOREIGN KEY (strategy_id) REFERENCES strategies(id),
    FOREIGN KEY (account_id) REFERENCES accounts(id)
);

CREATE INDEX idx_registrations_strategy ON registrations(strategy_id);
CREATE INDEX idx_registrations_account ON registrations(account_id);

COMMENT ON TABLE registrations IS 'Registration服务：激活策略与真实账户的绑定关系';

-- ============================================================
-- 3. 历史数据层（40年分区）
-- ============================================================

CREATE TABLE IF NOT EXISTS historical_bars (
    symbol VARCHAR(20) NOT NULL,
    timeframe VARCHAR(10) NOT NULL,
    time TIMESTAMP NOT NULL,
    open DECIMAL(10, 5) NOT NULL,
    high DECIMAL(10, 5) NOT NULL,
    low DECIMAL(10, 5) NOT NULL,
    close DECIMAL(10, 5) NOT NULL,
    volume BIGINT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    PRIMARY KEY (time, symbol, timeframe)
) PARTITION BY RANGE (time);

-- 创建2000-2040年分区
DO $$
DECLARE
    yr INT;
BEGIN
    FOR yr IN 2000..2040 LOOP
        EXECUTE format(
            'CREATE TABLE IF NOT EXISTS historical_bars_%s
             PARTITION OF historical_bars
             FOR VALUES FROM (%L) TO (%L)',
            yr, yr || '-01-01', (yr + 1) || '-01-01'
        );
    END LOOP;
END $$;

CREATE INDEX idx_historical_bars_symbol_timeframe_time
    ON historical_bars(symbol, timeframe, time DESC);

COMMENT ON TABLE historical_bars IS '历史K线数据（40年分区，用于回测和策略验证）';

-- ============================================================
-- 4. 真实交易层（20年分区）
-- ============================================================

CREATE TABLE IF NOT EXISTS real_online_trades (
    id VARCHAR(32),
    ticket BIGINT NOT NULL,
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
    PRIMARY KEY (id, created_at),
    FOREIGN KEY (account_id) REFERENCES accounts(id),
    FOREIGN KEY (strategy_id) REFERENCES strategies(id)
) PARTITION BY RANGE (created_at);

-- 创建2020-2040年分区
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

CREATE INDEX idx_real_online_trades_account ON real_online_trades(account_id, created_at DESC);
CREATE INDEX idx_real_online_trades_strategy ON real_online_trades(strategy_id, created_at DESC);
CREATE INDEX idx_real_online_trades_symbol ON real_online_trades(symbol, created_at DESC);
CREATE INDEX idx_real_online_trades_ticket ON real_online_trades(ticket);

COMMENT ON TABLE real_online_trades IS '真实线上交易记录（必须有ticket，关联account_type=REAL，20年分区）';

-- ============================================================
-- 5. 验证交易层（20年分区）
-- ============================================================

-- 回测批次表
CREATE TABLE IF NOT EXISTS validation_backtest_runs (
    id VARCHAR(32) PRIMARY KEY,
    strategy_id VARCHAR(32) REFERENCES strategies(id),
    symbol VARCHAR(20) NOT NULL,
    timeframe VARCHAR(10) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    bars_count INT,
    total_trades INT DEFAULT 0,
    total_profit DECIMAL(10, 2) DEFAULT 0,
    win_rate DECIMAL(5, 2) DEFAULT 0,
    max_drawdown DECIMAL(10, 2) DEFAULT 0,
    sharpe_ratio DECIMAL(5, 2),
    run_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    duration_seconds INT,
    status VARCHAR(20) DEFAULT 'RUNNING'
);

CREATE INDEX idx_validation_backtest_runs_strategy ON validation_backtest_runs(strategy_id);

COMMENT ON TABLE validation_backtest_runs IS '回测批次元数据（统计汇总）';

-- 验证交易表
CREATE TABLE IF NOT EXISTS validation_trades (
    id VARCHAR(32),

    -- 区分两类验证
    execution_type VARCHAR(20) NOT NULL,
    -- 'LIVE' - 线上验证（真实下单，有ticket）
    -- 'BACKTEST' - 历史回测（纯模拟，无ticket）

    ticket BIGINT,

    strategy_id VARCHAR(32) REFERENCES strategies(id),
    account_id VARCHAR(32) REFERENCES accounts(id),
    backtest_run_id VARCHAR(32) REFERENCES validation_backtest_runs(id),

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
    PRIMARY KEY (id, created_at),

    -- 约束
    CONSTRAINT chk_live_has_ticket CHECK (
        execution_type != 'LIVE' OR (ticket IS NOT NULL AND account_id IS NOT NULL)
    ),
    CONSTRAINT chk_backtest_no_ticket CHECK (
        execution_type != 'BACKTEST' OR (ticket IS NULL AND backtest_run_id IS NOT NULL)
    )
) PARTITION BY RANGE (created_at);

-- 创建2020-2040年分区
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

CREATE INDEX idx_validation_trades_type ON validation_trades(execution_type, created_at DESC);
CREATE INDEX idx_validation_trades_strategy ON validation_trades(strategy_id, created_at DESC);
CREATE INDEX idx_validation_trades_backtest ON validation_trades(backtest_run_id);
CREATE INDEX idx_validation_trades_account ON validation_trades(account_id, created_at DESC);

COMMENT ON TABLE validation_trades IS '验证交易记录（LIVE有ticket关联DEMO账户，BACKTEST无ticket纯模拟，20年分区）';

-- ============================================================
-- 6. 兼容性视图（Dashboard UI使用）
-- ============================================================

-- trades视图：用于Dashboard统计（指向real_online_trades）
CREATE OR REPLACE VIEW trades AS
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

COMMENT ON VIEW trades IS '兼容性视图：Dashboard UI使用，指向真实交易表';

-- ============================================================
-- 初始化完成
-- ============================================================

DO $$
BEGIN
    RAISE NOTICE '✅ MT4-Factory 数据库初始化完成';
    RAISE NOTICE '';
    RAISE NOTICE '📊 表结构:';
    RAISE NOTICE '   配置层:';
    RAISE NOTICE '     - mt5_hosts';
    RAISE NOTICE '     - strategies';
    RAISE NOTICE '     - signals';
    RAISE NOTICE '     - registrations';
    RAISE NOTICE '';
    RAISE NOTICE '   数据层:';
    RAISE NOTICE '     - accounts (account_type: REAL/DEMO)';
    RAISE NOTICE '     - historical_bars (2000-2040, 40年)';
    RAISE NOTICE '     - real_online_trades (2020-2040, 20年)';
    RAISE NOTICE '     - validation_trades (2020-2040, 20年)';
    RAISE NOTICE '     - validation_backtest_runs';
    RAISE NOTICE '';
    RAISE NOTICE '🔢 分区统计:';
    RAISE NOTICE '     - historical_bars: 41个分区';
    RAISE NOTICE '     - real_online_trades: 21个分区';
    RAISE NOTICE '     - validation_trades: 21个分区';
    RAISE NOTICE '';
END $$;
