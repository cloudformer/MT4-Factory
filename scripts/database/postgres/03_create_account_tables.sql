-- ============================================================
-- 03. 账户层表（Account Layer）
-- 用途: 账户、策略注册绑定
-- ============================================================

\set ON_ERROR_STOP on

\echo '▶ 03. 创建账户层表...'

BEGIN;

-- 账户表
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
    initial_balance FLOAT NOT NULL CHECK (initial_balance >= 0),
    current_balance FLOAT,
    current_equity FLOAT,
    is_active BOOLEAN DEFAULT TRUE,
    trade_allowed BOOLEAN DEFAULT TRUE,
    risk_config JSONB,
    notes VARCHAR(500),
    start_time TIMESTAMP,
    last_sync_time TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_accounts_mt5_host FOREIGN KEY (mt5_host_id)
        REFERENCES mt5_hosts(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_accounts_type ON accounts(account_type);
CREATE INDEX IF NOT EXISTS idx_accounts_login ON accounts(login);
CREATE INDEX IF NOT EXISTS idx_accounts_active ON accounts(is_active) WHERE is_active = TRUE;
CREATE INDEX IF NOT EXISTS idx_accounts_mt5_host ON accounts(mt5_host_id);

COMMENT ON TABLE accounts IS '统一账户表（account_type区分REAL/DEMO）';
COMMENT ON COLUMN accounts.account_type IS 'REAL=真实交易 | DEMO=验证账户';

-- 策略注册表
CREATE TABLE IF NOT EXISTS registrations (
    id VARCHAR(32) PRIMARY KEY,
    strategy_id VARCHAR(32) NOT NULL,
    account_id VARCHAR(32) NOT NULL,
    allocation_percentage FLOAT CHECK (allocation_percentage BETWEEN 0 AND 100),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT uix_registrations_strategy_account UNIQUE (strategy_id, account_id),
    CONSTRAINT fk_registrations_strategy FOREIGN KEY (strategy_id)
        REFERENCES strategies(id) ON DELETE CASCADE,
    CONSTRAINT fk_registrations_account FOREIGN KEY (account_id)
        REFERENCES accounts(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_registrations_strategy ON registrations(strategy_id);
CREATE INDEX IF NOT EXISTS idx_registrations_account ON registrations(account_id);
CREATE INDEX IF NOT EXISTS idx_registrations_active ON registrations(is_active) WHERE is_active = TRUE;

COMMENT ON TABLE registrations IS 'Registration服务：激活策略与真实账户的绑定关系';

COMMIT;

\echo '✅ 03. 账户层表创建完成 (accounts, registrations)'
\echo ''
