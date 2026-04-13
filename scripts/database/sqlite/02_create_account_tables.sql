-- ============================================================
-- 账户层：2张表
-- - accounts: MT5账户
-- - registrations: 策略-账户绑定
-- ============================================================

-- MT5账户
CREATE TABLE IF NOT EXISTS accounts (
    id VARCHAR(32) PRIMARY KEY,
    login INTEGER NOT NULL UNIQUE CHECK (login > 0),
    account_type VARCHAR(20) NOT NULL CHECK (account_type IN ('REAL', 'DEMO')),
    mt5_host_id VARCHAR(32),
    server VARCHAR(255) NOT NULL,
    company VARCHAR(255),
    name VARCHAR(255),
    currency VARCHAR(10) DEFAULT 'USD',
    leverage INTEGER DEFAULT 100 CHECK (leverage > 0),
    initial_balance REAL NOT NULL CHECK (initial_balance >= 0),
    current_balance REAL CHECK (current_balance >= 0),
    current_equity REAL CHECK (current_equity >= 0),
    is_active INTEGER DEFAULT 1,      -- SQLite: BOOLEAN = INTEGER
    trade_allowed INTEGER DEFAULT 1,  -- SQLite: BOOLEAN = INTEGER
    risk_config TEXT,  -- SQLite: JSONB = TEXT
    notes VARCHAR(500),
    start_time TIMESTAMP,
    last_sync_time TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (mt5_host_id) REFERENCES mt5_hosts(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_accounts_type ON accounts(account_type);
CREATE INDEX IF NOT EXISTS idx_accounts_login ON accounts(login);
CREATE INDEX IF NOT EXISTS idx_accounts_active ON accounts(is_active);
CREATE INDEX IF NOT EXISTS idx_accounts_host ON accounts(mt5_host_id);

-- 策略注册表（策略-账户绑定）
CREATE TABLE IF NOT EXISTS registrations (
    id VARCHAR(32) PRIMARY KEY,
    strategy_id VARCHAR(32) NOT NULL,
    account_id VARCHAR(32) NOT NULL,
    allocation_percentage REAL CHECK (allocation_percentage BETWEEN 0 AND 100),
    is_active INTEGER DEFAULT 1,  -- SQLite: BOOLEAN = INTEGER
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (strategy_id) REFERENCES strategies(id) ON DELETE CASCADE,
    FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE,

    UNIQUE (strategy_id, account_id)
);

CREATE INDEX IF NOT EXISTS idx_registrations_strategy ON registrations(strategy_id);
CREATE INDEX IF NOT EXISTS idx_registrations_account ON registrations(account_id);
CREATE INDEX IF NOT EXISTS idx_registrations_active ON registrations(is_active);

SELECT '✓ 账户层创建完成：2张表' AS progress;
