# MT4-Factory 数据库设计方案

## 核心原则

**单Schema设计 + 表前缀分组 + Table分区**

- 单一Schema（`public`）- 简化查询和维护
- 表前缀分组（`trading_*`, `validation_*`）- 逻辑清晰
- 大表分区（按年）- 性能优化

---

## 架构总览

```
PostgreSQL Database: mt4factory
Schema: public
│
├─ 全局配置层
│   ├─ mt5_hosts                    # MT5连接配置
│   ├─ strategies                   # 策略实例（含registration状态）
│   ├─ signals                      # 交易信号
│   └─ registrations                # 策略注册（激活策略与账户绑定）
│
├─ 统一账户层
│   └─ accounts                     # 统一账户表（account_type区分REAL/DEMO）
│
├─ 历史数据层（分区）
│   └─ historical_bars              # 历史K线（2000-2040，40年分区）
│
├─ 真实交易层（分区）
│   └─ real_online_trades           # 真实线上交易（2020-2040，20年分区）
│
└─ 验证交易层（分区）
    ├─ validation_backtest_runs     # 回测批次元数据
    └─ validation_trades            # 验证交易（2020-2040，20年分区）
```

---

## 设计决策

### 为什么选择单Schema？

| 维度 | 单Schema | 多Schema | 结论 |
|------|---------|----------|------|
| 查询语法 | `SELECT * FROM trading_trades` | `SELECT * FROM trading.trades` | ✅ 单Schema更简洁 |
| Join | 简单 | 需要完整路径 | ✅ 单Schema胜 |
| 外键 | 同schema简单 | 跨schema复杂 | ✅ 单Schema胜 |
| 代码维护 | 简单 | 复杂 | ✅ 单Schema胜 |
| 权限管理 | Table级别 | Schema级别 | 项目规模不需要 |

**结论**：对于中小规模项目，单Schema + 表前缀 = 最优方案

---

## 表结构设计

### 1. 全局配置层

#### mt5_hosts - MT5连接配置

```sql
CREATE TABLE mt5_hosts (
    id VARCHAR(32) PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,        -- demo_1, real_icm_1
    host_type VARCHAR(20) NOT NULL,          -- demo/real
    host VARCHAR(100) NOT NULL,
    port INT NOT NULL DEFAULT 9090,
    api_key VARCHAR(255),
    timeout INT DEFAULT 10,
    
    login INTEGER,
    password VARCHAR(255),
    server VARCHAR(255),
    use_investor BOOLEAN DEFAULT TRUE,
    
    enabled BOOLEAN DEFAULT TRUE,
    tags TEXT,
    notes VARCHAR(500),
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**用途**：
- Trading和Validation共享的MT5连接配置
- 支持多个MT5 API Bridge（Demo/Real）
- 策略可绑定到指定MT5主机

#### strategy_library - 策略代码库

```sql
CREATE TABLE strategy_library (
    id VARCHAR(32) PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    
    code TEXT NOT NULL,                      -- Python策略代码
    code_hash VARCHAR(64) NOT NULL,          -- SHA256去重
    
    params_schema JSONB,                     -- 参数定义
    strategy_type VARCHAR(50),               -- TREND/REVERSAL/SCALPING
    applicable_symbols JSONB,                -- ["EURUSD", "GBPUSD"]
    applicable_timeframes JSONB,             -- ["H1", "H4"]
    
    generated_by VARCHAR(50),                -- LLM/MANUAL
    llm_model VARCHAR(50),
    
    validation_status VARCHAR(20) DEFAULT 'PENDING',
    -- PENDING → BACKTEST_PASSED → LIVE_TESTING → APPROVED
    
    version INT DEFAULT 1,
    parent_id VARCHAR(32) REFERENCES strategy_library(id),
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### strategies - 策略实例

```sql
CREATE TABLE strategies (
    id VARCHAR(32) PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    
    strategy_library_id VARCHAR(32) REFERENCES strategy_library(id),
    mt5_host_id VARCHAR(32) REFERENCES mt5_hosts(id),
    
    code TEXT NOT NULL,
    params JSONB,
    
    -- Registration状态管理
    status VARCHAR(20) DEFAULT 'CANDIDATE',
    -- CANDIDATE: 候选策略（未激活）
    -- ACTIVE: 激活策略（正在交易）
    -- ARCHIVED: 归档策略
    
    -- 验证指标
    last_validation_time TIMESTAMP,
    validation_win_rate FLOAT,
    validation_total_return FLOAT,
    validation_total_trades INTEGER,
    validation_sharpe_ratio FLOAT,
    validation_max_drawdown FLOAT,
    validation_profit_factor FLOAT,
    
    performance JSONB,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_strategies_status ON strategies(status);
CREATE INDEX idx_strategies_mt5_host ON strategies(mt5_host_id);
CREATE INDEX idx_strategies_library ON strategies(strategy_library_id);
```

---

### 2. 历史数据层（40年分区）

#### historical_bars - 历史K线

```sql
CREATE TABLE historical_bars (
    symbol VARCHAR(20) NOT NULL,
    timeframe VARCHAR(10) NOT NULL,          -- M5/M15/M30/H1/H4/D1/W1
    time TIMESTAMP NOT NULL,
    open DECIMAL(10, 5) NOT NULL,
    high DECIMAL(10, 5) NOT NULL,
    low DECIMAL(10, 5) NOT NULL,
    close DECIMAL(10, 5) NOT NULL,
    volume BIGINT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    PRIMARY KEY (time, symbol, timeframe)
) PARTITION BY RANGE (time);

-- 创建2000-2040年分区（40年）
DO $$
DECLARE
    yr INT;
BEGIN
    FOR yr IN 2000..2040 LOOP
        EXECUTE format(
            'CREATE TABLE historical_bars_%s PARTITION OF historical_bars
             FOR VALUES FROM (%L) TO (%L)',
            yr, yr || '-01-01', (yr + 1) || '-01-01'
        );
    END LOOP;
END $$;

CREATE INDEX idx_historical_bars_lookup 
    ON historical_bars(symbol, timeframe, time DESC);

COMMENT ON TABLE historical_bars IS '历史K线数据（40年分区），用于回测和策略验证';
```

**查询示例**：
```sql
-- 查询EURUSD最近1000根H1 K线
SELECT * FROM historical_bars
WHERE symbol = 'EURUSD' AND timeframe = 'H1'
ORDER BY time DESC LIMIT 1000;
```

---

### 3. 统一账户层

#### accounts - 统一账户表

```sql
CREATE TABLE accounts (
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
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_accounts_type ON accounts(account_type);
CREATE INDEX idx_accounts_login ON accounts(login);
CREATE INDEX idx_accounts_active ON accounts(is_active);

COMMENT ON TABLE accounts IS '统一账户表（account_type区分REAL/DEMO）';
```

**查询示例**：
```sql
-- 查询真实账户
SELECT * FROM accounts WHERE account_type = 'REAL';

-- 查询验证账户
SELECT * FROM accounts WHERE account_type = 'DEMO';
```

#### registrations - 策略注册表

```sql
CREATE TABLE registrations (
    id VARCHAR(32) PRIMARY KEY,
    
    -- 激活策略与真实账户的绑定
    strategy_id VARCHAR(32) NOT NULL REFERENCES strategies(id),
    account_id VARCHAR(32) NOT NULL REFERENCES accounts(id),
    
    -- 资金分配比例（可选）
    allocation_percentage FLOAT,
    
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT uix_strategy_account UNIQUE (strategy_id, account_id)
);

CREATE INDEX idx_registrations_strategy ON registrations(strategy_id);
CREATE INDEX idx_registrations_account ON registrations(account_id);

COMMENT ON TABLE registrations IS 'Registration服务：激活策略与真实账户的绑定关系';
```

**业务逻辑**：
```sql
-- 1. 激活策略
UPDATE strategies SET status = 'ACTIVE' WHERE id = 'str_001';

-- 2. 注册到真实账户
INSERT INTO registrations (strategy_id, account_id, allocation_percentage)
VALUES ('str_001', 'acc_real_001', 30.0);

-- 3. 查询账户上运行的策略
SELECT s.*, r.allocation_percentage
FROM strategies s
JOIN registrations r ON s.id = r.strategy_id
WHERE r.account_id = 'acc_real_001' AND r.is_active = TRUE;
```

---

### 4. 真实交易层（20年分区）

#### real_online_trades - 真实线上交易（分区）

```sql
CREATE TABLE real_online_trades (
    id VARCHAR(32) PRIMARY KEY,
    ticket BIGINT NOT NULL,                  -- 必须有MT5 ticket
    
    account_id VARCHAR(32) REFERENCES accounts(id),
    strategy_id VARCHAR(32) REFERENCES strategies(id),
    signal_id VARCHAR(32),
    
    symbol VARCHAR(10) NOT NULL,
    direction VARCHAR(4) NOT NULL,           -- BUY/SELL
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
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    PRIMARY KEY (id, created_at)
) PARTITION BY RANGE (created_at);

-- 创建2020-2040年分区（20年）
DO $$
DECLARE
    yr INT;
BEGIN
    FOR yr IN 2020..2040 LOOP
        EXECUTE format(
            'CREATE TABLE real_online_trades_%s PARTITION OF real_online_trades
             FOR VALUES FROM (%L) TO (%L)',
            yr, yr || '-01-01', (yr + 1) || '-01-01'
        );
    END LOOP;
END $$;

CREATE INDEX idx_real_online_trades_strategy 
    ON real_online_trades(strategy_id, created_at DESC);
CREATE INDEX idx_real_online_trades_account 
    ON real_online_trades(account_id, created_at DESC);
CREATE INDEX idx_real_online_trades_symbol 
    ON real_online_trades(symbol, created_at DESC);

COMMENT ON TABLE real_online_trades IS '真实线上交易记录（必须有ticket，关联account_type=REAL，20年分区）';
```

---

### 5. 验证交易层（20年分区）

#### validation_backtest_runs - 回测批次

```sql
CREATE TABLE validation_backtest_runs (
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
```

#### validation_trades - 验证交易（分区）

```sql
CREATE TABLE validation_trades (
    id VARCHAR(32) PRIMARY KEY,
    
    -- 区分两类验证
    execution_type VARCHAR(20) NOT NULL,     -- LIVE/BACKTEST
    ticket BIGINT,                           -- LIVE有值，BACKTEST为NULL
    
    strategy_id VARCHAR(32) REFERENCES strategies(id),
    account_id VARCHAR(32) REFERENCES validation_accounts(id),
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
    
    -- 约束
    CONSTRAINT chk_live_has_ticket CHECK (
        execution_type != 'LIVE' OR (ticket IS NOT NULL AND account_id IS NOT NULL)
    ),
    CONSTRAINT chk_backtest_no_ticket CHECK (
        execution_type != 'BACKTEST' OR (ticket IS NULL AND backtest_run_id IS NOT NULL)
    ),
    
    PRIMARY KEY (id, created_at)
) PARTITION BY RANGE (created_at);

-- 创建2020-2040年分区（20年）
DO $$
DECLARE
    yr INT;
BEGIN
    FOR yr IN 2020..2040 LOOP
        EXECUTE format(
            'CREATE TABLE validation_trades_%s PARTITION OF validation_trades
             FOR VALUES FROM (%L) TO (%L)',
            yr, yr || '-01-01', (yr + 1) || '-01-01'
        );
    END LOOP;
END $$;

CREATE INDEX idx_validation_trades_type 
    ON validation_trades(execution_type, created_at DESC);
CREATE INDEX idx_validation_trades_strategy 
    ON validation_trades(strategy_id, created_at DESC);
CREATE INDEX idx_validation_trades_backtest 
    ON validation_trades(backtest_run_id);

COMMENT ON TABLE validation_trades IS '验证交易记录（LIVE有ticket，BACKTEST无ticket，20年分区）';
```

---

### 6. 其他表

#### signals - 交易信号

```sql
CREATE TABLE signals (
    id VARCHAR(32) PRIMARY KEY,
    strategy_id VARCHAR(32) REFERENCES strategies(id),
    
    symbol VARCHAR(10) NOT NULL,
    direction VARCHAR(4) NOT NULL,
    volume DECIMAL(10, 2) NOT NULL,
    sl DECIMAL(10, 5),
    tp DECIMAL(10, 5),
    
    status VARCHAR(9) NOT NULL DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_signals_strategy ON signals(strategy_id);
CREATE INDEX idx_signals_status ON signals(status);
```

---

## 分区策略总结

| 表名 | 是否分区 | 分区键 | 分区范围 | 原因 |
|------|---------|--------|---------|------|
| `historical_bars` | ✅ | time | 2000-2040（40年） | 数据量最大（多品种×多周期×40年） |
| `real_online_trades` | ✅ | created_at | 2020-2040（20年） | 真实交易记录，长期累积 |
| `validation_trades` | ✅ | created_at | 2020-2040（20年） | 验证交易记录，长期累积 |
| 其他表 | ❌ | - | - | 配置表/元数据，数据量小，无需分区 |

**分区优势**：
- 查询时自动跳过无关分区（partition pruning）
- 维护方便（可以直接删除老分区释放空间）
- 大表查询性能提升10倍+

---

## 查询示例

### 跨表Join（单Schema优势）

```sql
-- 查询策略的所有真实交易（简洁）
SELECT 
    s.name AS strategy_name,
    a.login AS account_login,
    t.symbol,
    t.profit,
    t.open_time
FROM real_online_trades t
JOIN strategies s ON t.strategy_id = s.id
JOIN accounts a ON t.account_id = a.id
WHERE t.created_at >= '2024-01-01'
  AND a.account_type = 'REAL'
ORDER BY t.created_at DESC;
```

### 分区自动剪枝

```sql
-- PostgreSQL自动只扫描2024分区
EXPLAIN SELECT * FROM real_online_trades
WHERE created_at BETWEEN '2024-01-01' AND '2024-12-31';

-- 执行计划：
-- Append
--   -> Seq Scan on real_online_trades_2024  ✅
--   (其他20个分区自动跳过)
```

### 验证交易区分查询

```sql
-- 只查询回测数据
SELECT * FROM validation_trades
WHERE execution_type = 'BACKTEST'
AND backtest_run_id = 'run_001';

-- 只查询线上验证
SELECT * FROM validation_trades
WHERE execution_type = 'LIVE'
AND account_id = 'demo_acc_1';
```

---

## 数据流向

```
1. 历史数据回测
   historical_bars → Validator → validation_trades (BACKTEST)
   ├─ 读取历史K线
   ├─ 运行策略逻辑
   └─ 生成模拟交易（无ticket，关联backtest_run_id）

2. 线上验证
   Validator → MT5 API (DEMO账户) → validation_trades (LIVE)
   ├─ 真实下单（有ticket）
   ├─ 关联 accounts (account_type='DEMO')
   └─ 小手数验证

3. 真实交易
   Strategy → Signal → Executor → MT5 API (REAL账户) → real_online_trades
   ├─ 真实下单（有ticket）
   ├─ 关联 accounts (account_type='REAL')
   ├─ 关联 registrations（策略注册）
   └─ 正常手数交易
```

---

## 维护建议

### 定期清理老分区

```sql
-- 删除2020年的验证数据（释放空间）
DROP TABLE validation_trades_2020;

-- 历史K线通常保留（用于回测）
-- 真实交易记录建议永久保留（监管合规）
```

### 监控分区大小

```sql
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE tablename LIKE 'real_online_trades_%'
   OR tablename LIKE 'validation_trades_%'
   OR tablename LIKE 'historical_bars_%'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

---

## 参考文档

- [PostgreSQL分区表文档](https://www.postgresql.org/docs/current/ddl-partitioning.html)
- [MT5主机管理文档](./mt5.md)
- [系统架构设计](./architecture.md)

---

## 表结构总结

### 完整表清单（10张主表）

| # | 表名 | 分类 | 分区 | 说明 |
|---|------|------|------|------|
| 1 | `mt5_hosts` | 配置层 | ❌ | MT5 API Bridge连接配置 |
| 2 | `strategies` | 配置层 | ❌ | 策略实例（含status状态） |
| 3 | `signals` | 配置层 | ❌ | 交易信号 |
| 4 | `registrations` | 配置层 | ❌ | 策略注册（激活策略与账户绑定） |
| 5 | `accounts` | 数据层 | ❌ | 统一账户表（account_type: REAL/DEMO） |
| 6 | `historical_bars` | 数据层 | ✅ 40年 | 历史K线数据（2000-2040） |
| 7 | `real_online_trades` | 数据层 | ✅ 20年 | 真实线上交易（2020-2040） |
| 8 | `validation_trades` | 数据层 | ✅ 20年 | 验证交易（LIVE/BACKTEST，2020-2040） |
| 9 | `validation_backtest_runs` | 数据层 | ❌ | 回测批次元数据 |

### 表间关系

```
mt5_hosts
    ↓ (1:N)
accounts (account_type)
    ├─ REAL → real_online_trades
    └─ DEMO → validation_trades (LIVE)

strategies (status)
    ├─ ACTIVE → registrations → accounts (REAL)
    └─ CANDIDATE/ARCHIVED

signals
    ↓ (1:1)
real_online_trades / validation_trades

validation_backtest_runs
    ↓ (1:N)
validation_trades (BACKTEST)
```

### 核心设计特点

✅ **单Schema设计** - 简化查询，避免跨schema复杂度  
✅ **账户统一管理** - accounts表用account_type区分REAL/DEMO  
✅ **表前缀清晰** - real_*, validation_* 业务逻辑明确  
✅ **大表分区优化** - 历史K线40年，交易记录20年，自动剪枝  
✅ **金融行业术语** - trades（交易）、bars（K线）、runs（批次）  
✅ **Registration服务** - registrations表管理策略与账户绑定

