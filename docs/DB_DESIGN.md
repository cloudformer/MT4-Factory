# 数据库设计方案

## 核心原则

**Windows和Cloud都使用PostgreSQL，采用Schema逻辑分离：**
- `historical_data` - 历史K线数据
- `trading` - 真实交易数据（大资金生产账户）
- `validation` - 策略验证数据（Demo或小资金账户）

**时间和货币对都存放单表，加上必要的主键优化，使用年度分区（2000-2040）。**

---

## 架构总览

```
PostgreSQL RDS实例
├─ historical_data schema（历史K线数据）
│   └─ historical_bars（按年分区，2000-2040）
│
├─ trading schema（真实交易数据 + 元数据配置）
│   ├─ mt5_hosts（MT5 API Bridge连接配置）⭐ 新增
│   ├─ accounts（Real大资金账户，如$10万）→ 关联mt5_hosts
│   ├─ strategy_library（LLM生成的策略代码库）⭐ 新增
│   ├─ strategies（策略实例）→ 关联strategy_library
│   ├─ trades（MT5 Worker执行的真实交易）
│   └─ positions（VIEW - 当前持仓）
│
└─ validation schema（策略验证数据）
    ├─ accounts（Demo或Real小资金账户，如$10-$10,000）→ 关联trading.mt5_hosts
    ├─ backtest_runs（历史回测批次）
    ├─ trades（包含两类验证）
    │   ├─ execution_type='LIVE'（线上真实下单，有ticket）
    │   └─ execution_type='BACKTEST'（历史回测，无ticket）
    ├─ positions（VIEW - 线上验证持仓）
    └─ backtest_summary（VIEW - 回测结果汇总）
```

---

## Schema 1: historical_data（历史K线）

### 设计理念

- 存储所有品种、所有周期的历史K线
- 用于策略回测和验证
- 按年分区（2000-2040），支持40年数据

### 表结构

```sql
-- ============================================================
-- Historical Data Schema
-- ============================================================

CREATE SCHEMA IF NOT EXISTS historical_data;
COMMENT ON SCHEMA historical_data IS '历史K线数据，用于回测和策略验证';

SET search_path TO historical_data;

-- 历史K线表（按年分区）
CREATE TABLE historical_bars (
    symbol VARCHAR(20) NOT NULL,      -- 品种：EURUSD, GBPUSD, XAUUSD等
    timeframe VARCHAR(10) NOT NULL,   -- 周期：M5, M15, M30, H1, H4, D1, W1
    time TIMESTAMP NOT NULL,          -- 时间戳
    open DECIMAL(10, 5) NOT NULL,
    high DECIMAL(10, 5) NOT NULL,
    low DECIMAL(10, 5) NOT NULL,
    close DECIMAL(10, 5) NOT NULL,
    volume BIGINT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    PRIMARY KEY (time, symbol, timeframe)
) PARTITION BY RANGE (time);

COMMENT ON TABLE historical_bars IS '历史K线数据，所有品种和周期存储在单表';

-- 创建2000-2040年分区（40年）
DO $$
DECLARE
    start_year INT := 2000;
    end_year INT := 2040;
    current_year INT;
BEGIN
    FOR current_year IN start_year..end_year LOOP
        EXECUTE format(
            'CREATE TABLE IF NOT EXISTS historical_data.historical_bars_%s 
             PARTITION OF historical_data.historical_bars
             FOR VALUES FROM (%L) TO (%L)',
            current_year,
            current_year || '-01-01',
            (current_year + 1) || '-01-01'
        );
    END LOOP;
END $$;

-- 创建索引（性能关键）
CREATE INDEX idx_historical_bars_symbol_timeframe_time 
    ON historical_bars(symbol, timeframe, time DESC);

CREATE INDEX idx_historical_bars_symbol_time 
    ON historical_bars(symbol, time DESC);

-- 查看所有分区
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE tablename LIKE 'historical_bars_%'
ORDER BY tablename;
```

### 查询示例

```sql
-- 查询EURUSD的H1数据（最近1000根）
SELECT * FROM historical_data.historical_bars
WHERE symbol = 'EURUSD' 
  AND timeframe = 'H1'
ORDER BY time DESC 
LIMIT 1000;

-- 查询多个品种的D1数据
SELECT * FROM historical_data.historical_bars
WHERE symbol IN ('EURUSD', 'GBPUSD', 'XAUUSD')
  AND timeframe = 'D1'
  AND time >= '2024-01-01'
ORDER BY symbol, time DESC;
```

---

## Schema 2: trading（真实交易）

### 设计理念

- 主要生产交易，大资金账户
- MT5 Worker执行的真实订单
- 所有交易都有真实MT5 ticket
- 为了盈利

### 表结构

```sql
-- ============================================================
-- Trading Schema
-- ============================================================

CREATE SCHEMA IF NOT EXISTS trading;
COMMENT ON SCHEMA trading IS '真实交易数据（MT5 Worker执行）';

SET search_path TO trading;

-- 1. MT5连接配置表
CREATE TABLE mt5_hosts (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,  -- demo_1, real_1, real_2
    host VARCHAR(100) NOT NULL,
    port INT NOT NULL,
    api_key VARCHAR(255),
    
    -- 连接池配置
    max_connections INT DEFAULT 10,
    timeout INT DEFAULT 30,
    
    -- 状态
    status VARCHAR(20) DEFAULT 'ACTIVE',  -- ACTIVE/INACTIVE/MAINTENANCE
    description TEXT,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE mt5_hosts IS 'MT5 API Bridge连接配置';

-- 2. 账户表
CREATE TABLE accounts (
    id BIGSERIAL PRIMARY KEY,
    account_number BIGINT UNIQUE NOT NULL,
    broker VARCHAR(100) NOT NULL,
    account_type VARCHAR(20) NOT NULL,  -- 'REAL' / 'DEMO'
    
    -- MT5连接信息（关联到mt5_hosts）
    mt5_host_id BIGINT REFERENCES mt5_hosts(id),
    
    -- 账户信息
    initial_balance DECIMAL(10, 2),
    balance DECIMAL(10, 2) DEFAULT 0,
    equity DECIMAL(10, 2) DEFAULT 0,
    margin DECIMAL(10, 2) DEFAULT 0,
    free_margin DECIMAL(10, 2) DEFAULT 0,
    
    -- 状态
    status VARCHAR(20) DEFAULT 'ACTIVE',  -- ACTIVE/INACTIVE
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_trading_accounts_mt5_host ON accounts(mt5_host_id);

COMMENT ON TABLE accounts IS '真实交易账户（大资金生产账户）';

-- 3. 策略库表（LLM生成的策略代码）
CREATE TABLE strategy_library (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    
    -- 策略代码（Python）
    code TEXT NOT NULL,
    code_hash VARCHAR(64) NOT NULL,  -- SHA256，用于去重和版本控制
    
    -- 参数定义（JSON Schema格式）
    params_schema JSONB,
    -- 示例：
    -- {
    --   "type": "object",
    --   "properties": {
    --     "ema_fast": {"type": "integer", "default": 12, "min": 5, "max": 50},
    --     "ema_slow": {"type": "integer", "default": 26, "min": 20, "max": 100},
    --     "rsi_period": {"type": "integer", "default": 14}
    --   }
    -- }
    
    -- 策略元数据
    strategy_type VARCHAR(50),  -- TREND/REVERSAL/SCALPING/GRID等
    applicable_symbols JSONB,   -- ["EURUSD", "GBPUSD"] 或 ["*"] 表示通用
    applicable_timeframes JSONB,  -- ["H1", "H4"] 或 ["*"]
    
    -- 生成信息
    generated_by VARCHAR(50),  -- 'LLM' / 'MANUAL' / 'IMPORTED'
    llm_model VARCHAR(50),     -- 'claude-sonnet-4.6'
    llm_prompt_hash VARCHAR(64),  -- 用于追踪生成来源
    
    -- 验证状态
    validation_status VARCHAR(20) DEFAULT 'PENDING',
    -- PENDING: 未验证
    -- BACKTEST_PASSED: 历史回测通过
    -- LIVE_TESTING: 线上验证中
    -- APPROVED: 已批准上生产
    -- REJECTED: 已拒绝
    
    validation_summary JSONB,  -- 验证结果摘要
    
    -- 版本管理
    version INT DEFAULT 1,
    parent_id BIGINT REFERENCES strategy_library(id),  -- 基于哪个版本改进
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    approved_at TIMESTAMP,
    approved_by VARCHAR(100)
);

CREATE INDEX idx_strategy_library_status ON strategy_library(validation_status);
CREATE INDEX idx_strategy_library_code_hash ON strategy_library(code_hash);
CREATE INDEX idx_strategy_library_type ON strategy_library(strategy_type);

COMMENT ON TABLE strategy_library IS 'LLM生成的策略代码库';
COMMENT ON COLUMN strategy_library.code IS 'Python策略代码';
COMMENT ON COLUMN strategy_library.params_schema IS 'JSON Schema定义参数';
COMMENT ON COLUMN strategy_library.validation_status IS '验证状态：PENDING/BACKTEST_PASSED/LIVE_TESTING/APPROVED/REJECTED';

-- 4. 策略表（策略实例）
CREATE TABLE strategies (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    
    -- 关联到策略库
    strategy_library_id BIGINT REFERENCES strategy_library(id),
    
    -- 交易配置
    symbol VARCHAR(20) NOT NULL,
    timeframe VARCHAR(10) NOT NULL,
    
    -- 策略参数（JSON存储，覆盖strategy_library的默认值）
    params JSONB,
    
    -- 状态
    status VARCHAR(20) DEFAULT 'ACTIVE',  -- ACTIVE/PAUSED/STOPPED
    
    -- 统计信息（可从trades聚合）
    total_trades INT DEFAULT 0,
    total_profit DECIMAL(10, 2) DEFAULT 0,
    win_rate DECIMAL(5, 2) DEFAULT 0,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_trading_strategies_library ON strategies(strategy_library_id);
CREATE INDEX idx_trading_strategies_status ON strategies(status);

COMMENT ON TABLE strategies IS '策略实例（基于strategy_library的具体配置）';

-- 5. 交易记录表
CREATE TABLE trades (
    id BIGSERIAL PRIMARY KEY,
    ticket BIGINT UNIQUE NOT NULL,  -- MT5订单号
    
    -- 关联
    strategy_id BIGINT NOT NULL REFERENCES strategies(id),
    account_id BIGINT NOT NULL REFERENCES accounts(id),
    
    -- 交易信息
    symbol VARCHAR(20) NOT NULL,
    type VARCHAR(10) NOT NULL,  -- BUY/SELL
    volume DECIMAL(10, 2) NOT NULL,
    
    -- 价格信息
    open_price DECIMAL(10, 5) NOT NULL,
    close_price DECIMAL(10, 5),
    stop_loss DECIMAL(10, 5),
    take_profit DECIMAL(10, 5),
    
    -- 时间信息
    open_time TIMESTAMP NOT NULL,
    close_time TIMESTAMP,
    
    -- 盈亏信息
    profit DECIMAL(10, 2) DEFAULT 0,
    commission DECIMAL(10, 2) DEFAULT 0,
    swap DECIMAL(10, 2) DEFAULT 0,
    
    -- 状态
    status VARCHAR(20) NOT NULL DEFAULT 'OPEN',  -- OPEN/CLOSED/CANCELLED
    
    -- MT5机器信息
    mt5_host VARCHAR(100),
    mt5_port INT,
    
    -- 元数据
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_trading_trades_strategy_time ON trades(strategy_id, open_time DESC);
CREATE INDEX idx_trading_trades_account_time ON trades(account_id, open_time DESC);
CREATE INDEX idx_trading_trades_symbol_time ON trades(symbol, open_time DESC);
CREATE INDEX idx_trading_trades_status ON trades(status);
CREATE INDEX idx_trading_trades_open_time ON trades(open_time DESC);

COMMENT ON TABLE trades IS '真实交易记录（MT5 Worker执行，大手数）';

-- 6. 持仓视图
CREATE VIEW positions AS
SELECT 
    t.id,
    t.ticket,
    t.strategy_id,
    s.name as strategy_name,
    t.account_id,
    a.account_number,
    t.symbol,
    t.type,
    t.volume,
    t.open_price,
    t.stop_loss,
    t.take_profit,
    t.open_time,
    EXTRACT(EPOCH FROM (NOW() - t.open_time))/3600 as hours_held
FROM trades t
JOIN strategies s ON t.strategy_id = s.id
JOIN accounts a ON t.account_id = a.id
WHERE t.status = 'OPEN'
ORDER BY t.open_time DESC;

COMMENT ON VIEW positions IS '当前持仓视图';
```

### 查询示例

```sql
-- 今日交易统计
SELECT 
    COUNT(*) as trades,
    SUM(profit) as total_profit,
    AVG(profit) as avg_profit,
    COUNT(CASE WHEN profit > 0 THEN 1 END) * 100.0 / COUNT(*) as win_rate
FROM trading.trades
WHERE DATE(open_time) = CURRENT_DATE
  AND status = 'CLOSED';

-- 按策略分组统计
SELECT 
    s.name,
    COUNT(t.id) as trades,
    SUM(t.profit) as profit,
    COUNT(CASE WHEN t.profit > 0 THEN 1 END) * 100.0 / COUNT(t.id) as win_rate
FROM trading.trades t
JOIN trading.strategies s ON t.strategy_id = s.id
WHERE DATE(t.open_time) = CURRENT_DATE
  AND t.status = 'CLOSED'
GROUP BY s.name
ORDER BY profit DESC;

-- 查看当前持仓
SELECT * FROM trading.positions;
```

---

## Schema 3: validation（策略验证）

### 设计理念

- 策略验证数据，Demo或小资金账户
- **两类验证**：
  1. **线上交易验证**：真实下单（有ticket），从技术层面和trading完全一样
  2. **历史数据验证**：纯回测（无ticket），不下真单
- 用途：验证策略准确性，不是为了盈利

### 两类验证对比

| 维度 | 线上交易验证 | 历史数据验证 |
|------|------------|------------|
| **下单方式** | 真实调用MT5 API ✅ | 纯模拟，不调用MT5 ❌ |
| **有ticket** | ✅ 有 | ❌ 无 |
| **账户** | Demo或Real小资金 | 无账户（虚拟） |
| **资金** | $10-$10,000 | 虚拟资金 |
| **手数** | 小（如0.01手） | 虚拟手数 |
| **数据来源** | 实时行情 | historical_data历史K线 |
| **execution_type** | 'LIVE' | 'BACKTEST' |
| **用途** | 验证策略在真实环境的表现 | 快速验证策略逻辑 |
| **与trading对比** | 技术实现完全相同 | 技术实现完全不同 |

### 表结构

```sql
-- ============================================================
-- Validation Schema
-- ============================================================

CREATE SCHEMA IF NOT EXISTS validation;
COMMENT ON SCHEMA validation IS '策略验证数据（Demo或小资金账户）';

SET search_path TO validation;

-- 1. 验证账户表
CREATE TABLE accounts (
    id BIGSERIAL PRIMARY KEY,
    account_number BIGINT UNIQUE NOT NULL,
    broker VARCHAR(100) NOT NULL,
    
    -- 账户类型
    account_type VARCHAR(20) NOT NULL,
    -- 'DEMO' = Demo账户（模拟资金）
    -- 'REAL_SMALL' = Real小资金账户（真钱，$10-$100）
    
    -- MT5连接信息（关联到trading.mt5_hosts）
    mt5_host_id BIGINT REFERENCES trading.mt5_hosts(id),
    
    -- 账户信息
    initial_balance DECIMAL(10, 2),
    current_balance DECIMAL(10, 2),
    equity DECIMAL(10, 2),
    margin DECIMAL(10, 2),
    free_margin DECIMAL(10, 2),
    
    -- 状态
    status VARCHAR(20) DEFAULT 'ACTIVE',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_validation_accounts_mt5_host ON accounts(mt5_host_id);

COMMENT ON TABLE accounts IS 'Validator验证账户：Demo账户或Real小资金账户';

-- 2. 回测批次表（仅用于历史数据验证）
CREATE TABLE backtest_runs (
    id BIGSERIAL PRIMARY KEY,
    strategy_id BIGINT NOT NULL,
    
    -- 回测参数
    symbol VARCHAR(20) NOT NULL,
    timeframe VARCHAR(10) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    bars_count INT,
    
    -- 回测结果汇总
    total_trades INT DEFAULT 0,
    total_profit DECIMAL(10, 2) DEFAULT 0,
    win_rate DECIMAL(5, 2) DEFAULT 0,
    max_drawdown DECIMAL(10, 2) DEFAULT 0,
    sharpe_ratio DECIMAL(5, 2),
    
    -- 执行信息
    run_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    duration_seconds INT,
    status VARCHAR(20) DEFAULT 'RUNNING',  -- RUNNING/SUCCESS/FAILED
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE backtest_runs IS '历史数据回测批次（不下真单）';

-- 3. 统一的交易表（包含两类验证）✅
CREATE TABLE trades (
    id BIGSERIAL PRIMARY KEY,
    
    -- ✅ 关键字段：区分两类验证
    ticket BIGINT,  -- 线上交易有ticket，历史回测为NULL
    execution_type VARCHAR(20) NOT NULL,
    -- 'LIVE' = 线上交易验证（真实下单，有ticket）
    -- 'BACKTEST' = 历史数据验证（纯模拟，无ticket）
    
    -- 关联（根据execution_type选择性关联）
    strategy_id BIGINT NOT NULL,
    account_id BIGINT REFERENCES accounts(id),  -- LIVE必须有，BACKTEST为NULL
    backtest_run_id BIGINT REFERENCES backtest_runs(id),  -- BACKTEST必须有，LIVE为NULL
    
    -- 交易信息（与trading.trades完全相同）
    symbol VARCHAR(20) NOT NULL,
    type VARCHAR(10) NOT NULL,  -- BUY/SELL
    volume DECIMAL(10, 2) NOT NULL,
    
    -- 价格信息
    open_price DECIMAL(10, 5) NOT NULL,
    close_price DECIMAL(10, 5),
    stop_loss DECIMAL(10, 5),
    take_profit DECIMAL(10, 5),
    
    -- 时间信息
    open_time TIMESTAMP NOT NULL,
    close_time TIMESTAMP,
    
    -- 盈亏信息
    profit DECIMAL(10, 2) DEFAULT 0,
    commission DECIMAL(10, 2) DEFAULT 0,
    swap DECIMAL(10, 2) DEFAULT 0,
    
    -- 状态
    status VARCHAR(20) NOT NULL DEFAULT 'OPEN',  -- OPEN/CLOSED/CANCELLED
    
    -- MT5机器信息（仅LIVE有值）
    mt5_host VARCHAR(100),
    mt5_port INT,
    
    -- 元数据
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- 约束：确保数据一致性
    CONSTRAINT chk_live_has_ticket CHECK (
        execution_type != 'LIVE' OR (ticket IS NOT NULL AND account_id IS NOT NULL)
    ),
    CONSTRAINT chk_backtest_no_ticket CHECK (
        execution_type != 'BACKTEST' OR (ticket IS NULL AND backtest_run_id IS NOT NULL)
    )
);

CREATE INDEX idx_validation_trades_execution_type ON trades(execution_type);
CREATE INDEX idx_validation_trades_ticket ON trades(ticket) WHERE ticket IS NOT NULL;
CREATE INDEX idx_validation_trades_strategy_time ON trades(strategy_id, open_time DESC);
CREATE INDEX idx_validation_trades_account_time ON trades(account_id, open_time DESC);
CREATE INDEX idx_validation_trades_backtest_run ON trades(backtest_run_id);
CREATE INDEX idx_validation_trades_status ON trades(status);

COMMENT ON TABLE trades IS 'Validator交易记录（包含线上验证和历史回测）';
COMMENT ON COLUMN trades.execution_type IS 'LIVE=线上真实下单, BACKTEST=历史数据回测';
COMMENT ON COLUMN trades.ticket IS 'LIVE有MT5订单号, BACKTEST为NULL';

-- 4. 线上持仓视图（仅查询LIVE交易）
CREATE VIEW positions AS
SELECT 
    t.id,
    t.ticket,
    t.strategy_id,
    t.account_id,
    a.account_number,
    a.account_type,
    t.symbol,
    t.type,
    t.volume,
    t.open_price,
    t.stop_loss,
    t.take_profit,
    t.open_time,
    EXTRACT(EPOCH FROM (NOW() - t.open_time))/3600 as hours_held
FROM trades t
JOIN accounts a ON t.account_id = a.id
WHERE t.status = 'OPEN'
  AND t.execution_type = 'LIVE'  -- ✅ 只看线上真实交易
ORDER BY t.open_time DESC;

COMMENT ON VIEW positions IS 'Validator当前线上持仓（Demo或小资金账户）';

-- 5. 回测结果汇总视图
CREATE VIEW backtest_summary AS
SELECT 
    br.id as run_id,
    br.strategy_id,
    br.symbol,
    br.timeframe,
    br.start_date,
    br.end_date,
    br.run_at,
    br.status,
    
    -- 统计信息
    COUNT(t.id) as trades_count,
    SUM(t.profit) as total_profit,
    AVG(t.profit) as avg_profit,
    COUNT(CASE WHEN t.profit > 0 THEN 1 END) * 100.0 / NULLIF(COUNT(t.id), 0) as win_rate,
    MAX(t.profit) as best_trade,
    MIN(t.profit) as worst_trade
    
FROM backtest_runs br
LEFT JOIN trades t ON br.id = t.backtest_run_id
    AND t.execution_type = 'BACKTEST'  -- ✅ 只看回测交易
GROUP BY br.id, br.strategy_id, br.symbol, br.timeframe, 
         br.start_date, br.end_date, br.run_at, br.status;

COMMENT ON VIEW backtest_summary IS '历史回测结果汇总';
```

### 查询示例

```sql
-- 1. Validator线上交易今日表现
SELECT 
    a.account_number,
    a.account_type,  -- DEMO / REAL_SMALL
    COUNT(t.id) as trades,
    SUM(t.profit) as profit,
    AVG(t.profit) as avg_profit,
    COUNT(CASE WHEN t.profit > 0 THEN 1 END) * 100.0 / COUNT(t.id) as win_rate
FROM validation.trades t
JOIN validation.accounts a ON t.account_id = a.id
WHERE t.execution_type = 'LIVE'  -- ✅ 线上交易
  AND DATE(t.open_time) = CURRENT_DATE
  AND t.status = 'CLOSED'
GROUP BY a.account_number, a.account_type;

-- 2. 最近一次历史回测结果
SELECT 
    br.id as run_id,
    br.run_at,
    br.symbol,
    br.timeframe,
    COUNT(t.id) as trades,
    SUM(t.profit) as profit
FROM validation.backtest_runs br
LEFT JOIN validation.trades t ON br.id = t.backtest_run_id
    AND t.execution_type = 'BACKTEST'  -- ✅ 历史回测
WHERE br.strategy_id = 1
  AND br.status = 'SUCCESS'
GROUP BY br.id, br.run_at, br.symbol, br.timeframe
ORDER BY br.run_at DESC
LIMIT 1;

-- 3. 策略对比（Trading vs Validator线上）
WITH trading_stats AS (
    SELECT 
        strategy_id,
        COUNT(*) as trades,
        SUM(profit) as profit,
        AVG(profit) as avg_profit
    FROM trading.trades
    WHERE strategy_id = 1 
      AND DATE(open_time) = CURRENT_DATE
      AND status = 'CLOSED'
    GROUP BY strategy_id
),
validation_live_stats AS (
    SELECT 
        strategy_id,
        COUNT(*) as trades,
        SUM(profit) as profit,
        AVG(profit) as avg_profit
    FROM validation.trades
    WHERE strategy_id = 1
      AND execution_type = 'LIVE'  -- ✅ 只看线上验证
      AND DATE(open_time) = CURRENT_DATE
      AND status = 'CLOSED'
    GROUP BY strategy_id
)
SELECT 
    t.trades as trading_trades,
    t.profit as trading_profit,
    v.trades as validation_trades,
    v.profit as validation_profit,
    
    -- 偏差分析
    (t.profit - v.profit) / NULLIF(v.profit, 0) * 100 as deviation_pct
    
FROM trading_stats t
FULL OUTER JOIN validation_live_stats v ON t.strategy_id = v.strategy_id;

-- 4. 查看Validator持仓（线上+回测）
SELECT * FROM validation.positions;  -- 线上持仓
SELECT * FROM validation.backtest_summary WHERE run_id = 123;  -- 回测结果
```

---

## 策略生命周期管理

### 设计理念

**strategy_library（策略库）** 和 **strategies（策略实例）** 的关系：

- **strategy_library** = 策略代码模板（Python代码 + 参数Schema）
- **strategies** = 策略实例（具体品种 + 具体参数 + 运行状态）

一个strategy_library可以被多个strategies引用，就像"类"和"对象"的关系。

### 策略生命周期流程

```
1. LLM生成策略代码
   ↓ (strategy service)
   策略代码 → trading.strategy_library
   (状态: PENDING)

2. 历史回测验证
   ↓ (validator service)
   从historical_data拉取数据
   → validation.backtest_runs
   → validation.trades (execution_type='BACKTEST')
   
   通过 → strategy_library.validation_status = 'BACKTEST_PASSED'
   不通过 → strategy_library.validation_status = 'REJECTED'

3. 线上验证（Demo/小资金）
   ↓ (validator service)
   创建策略实例 → trading.strategies
   (strategy_library_id → 关联到库)
   
   配置验证账户 → validation.accounts
   真实下单 → validation.trades (execution_type='LIVE')
   
   运行7-30天，观察表现
   → strategy_library.validation_status = 'LIVE_TESTING'

4. 批准上生产
   ↓ (manual approval or orchestrator)
   strategy_library.validation_status = 'APPROVED'
   strategy_library.approved_by = 'admin'
   strategy_library.approved_at = NOW()

5. 生产交易
   ↓ (execution service)
   创建策略实例 → trading.strategies
   (基于approved的strategy_library)
   
   配置生产账户 → trading.accounts
   真实下单（大手数）→ trading.trades
```

### MT5连接架构

```
trading.mt5_hosts（MT5 API Bridge连接配置）
    ↓ (多对一)
trading.accounts（生产账户）→ mt5_host_id
validation.accounts（验证账户）→ mt5_host_id

配置示例：
- mt5_hosts:
  - demo_1 (192.168.1.101:9090) → 用于validation.accounts
  - real_1 (192.168.1.100:9090) → 用于trading.accounts（主交易）
  - real_2 (192.168.1.100:9091) → 用于trading.accounts（备用）

好处：
✅ 集中管理连接配置
✅ 一个MT5 Host可以服务多个账户
✅ 易于切换和容灾
```

### 查询示例

```sql
-- 1. 查看策略库统计
SELECT 
    validation_status,
    COUNT(*) as count,
    COUNT(CASE WHEN generated_by = 'LLM' THEN 1 END) as llm_generated
FROM trading.strategy_library
GROUP BY validation_status
ORDER BY 
    CASE validation_status
        WHEN 'APPROVED' THEN 1
        WHEN 'LIVE_TESTING' THEN 2
        WHEN 'BACKTEST_PASSED' THEN 3
        WHEN 'PENDING' THEN 4
        WHEN 'REJECTED' THEN 5
    END;

-- 结果：
-- validation_status  | count | llm_generated
-- -------------------+-------+--------------
-- APPROVED          |    15 |    12
-- LIVE_TESTING      |     5 |     4
-- BACKTEST_PASSED   |    20 |    18
-- PENDING           |    30 |    30
-- REJECTED          |    10 |     8

-- 2. 查看策略实例及其代码库来源
SELECT 
    s.id,
    s.name,
    s.symbol,
    s.timeframe,
    s.status,
    sl.name as library_name,
    sl.validation_status,
    sl.generated_by,
    s.total_trades,
    s.total_profit
FROM trading.strategies s
LEFT JOIN trading.strategy_library sl ON s.strategy_library_id = sl.id
WHERE s.status = 'ACTIVE'
ORDER BY s.total_profit DESC;

-- 3. 查看策略的完整验证历史
SELECT 
    sl.name as strategy_name,
    sl.validation_status,
    
    -- 历史回测数据
    COUNT(DISTINCT br.id) as backtest_runs,
    
    -- 线上验证数据
    COUNT(DISTINCT CASE WHEN vt.execution_type = 'LIVE' THEN vt.id END) as live_trades,
    SUM(CASE WHEN vt.execution_type = 'LIVE' THEN vt.profit ELSE 0 END) as live_profit,
    
    -- 生产交易数据
    COUNT(DISTINCT tt.id) as production_trades,
    SUM(tt.profit) as production_profit
    
FROM trading.strategy_library sl
LEFT JOIN trading.strategies s ON sl.id = s.strategy_library_id
LEFT JOIN validation.backtest_runs br ON s.id = br.strategy_id
LEFT JOIN validation.trades vt ON s.id = vt.strategy_id
LEFT JOIN trading.trades tt ON s.id = tt.strategy_id
WHERE sl.id = 1
GROUP BY sl.id, sl.name, sl.validation_status;

-- 4. 查看MT5连接分布
SELECT 
    mh.name as host_name,
    mh.host,
    mh.port,
    mh.status,
    COUNT(DISTINCT ta.id) as trading_accounts,
    COUNT(DISTINCT va.id) as validation_accounts,
    COUNT(DISTINCT ta.id) + COUNT(DISTINCT va.id) as total_accounts
FROM trading.mt5_hosts mh
LEFT JOIN trading.accounts ta ON mh.id = ta.mt5_host_id
LEFT JOIN validation.accounts va ON mh.id = va.mt5_host_id
GROUP BY mh.id, mh.name, mh.host, mh.port, mh.status
ORDER BY total_accounts DESC;
```

---

## 使用场景代码示例

### 场景0：LLM生成策略并保存到策略库

```python
import hashlib
import json
from anthropic import Anthropic

class StrategyGenerator:
    """策略生成服务（strategy service）"""
    
    def __init__(self):
        self.anthropic_client = Anthropic(api_key=settings.anthropic_api_key)
    
    def generate_strategy(self, user_prompt: str):
        """
        根据用户Prompt生成策略代码
        
        Args:
            user_prompt: 用户描述，如"基于双均线交叉的趋势策略"
        """
        # 1. 调用LLM生成策略代码
        system_prompt = """
        你是一个专业的量化交易策略开发专家。
        根据用户需求，生成Python策略代码。
        
        返回JSON格式：
        {
            "name": "策略名称",
            "description": "策略描述",
            "code": "完整的Python代码",
            "params_schema": {...},  // JSON Schema
            "strategy_type": "TREND/REVERSAL/SCALPING",
            "applicable_symbols": ["*"] 或 ["EURUSD", "GBPUSD"],
            "applicable_timeframes": ["*"] 或 ["H1", "H4"]
        }
        """
        
        response = self.anthropic_client.messages.create(
            model="claude-sonnet-4.6",
            max_tokens=4096,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}]
        )
        
        strategy_data = json.loads(response.content[0].text)
        
        # 2. 计算code_hash（去重）
        code = strategy_data['code']
        code_hash = hashlib.sha256(code.encode()).hexdigest()
        
        # 3. 检查是否已存在相同代码
        existing = session.query(StrategyLibrary).filter(
            StrategyLibrary.code_hash == code_hash
        ).first()
        
        if existing:
            print(f"⚠️  相同代码已存在: {existing.name}")
            return existing
        
        # 4. 保存到策略库
        prompt_hash = hashlib.sha256(user_prompt.encode()).hexdigest()
        
        strategy_lib = StrategyLibrary(
            name=strategy_data['name'],
            description=strategy_data['description'],
            code=code,
            code_hash=code_hash,
            params_schema=strategy_data['params_schema'],
            strategy_type=strategy_data['strategy_type'],
            applicable_symbols=strategy_data['applicable_symbols'],
            applicable_timeframes=strategy_data['applicable_timeframes'],
            
            generated_by='LLM',
            llm_model='claude-sonnet-4.6',
            llm_prompt_hash=prompt_hash,
            
            validation_status='PENDING'  # 等待验证
        )
        
        session.add(strategy_lib)
        session.commit()
        
        print(f"✅ 策略已生成: {strategy_lib.name} (ID: {strategy_lib.id})")
        print(f"   状态: {strategy_lib.validation_status}")
        
        # 5. 自动触发历史回测
        self.trigger_backtest(strategy_lib)
        
        return strategy_lib
    
    def trigger_backtest(self, strategy_lib: StrategyLibrary):
        """触发历史回测验证"""
        # 创建策略实例
        strategy_instance = Strategy(
            name=f"{strategy_lib.name}_backtest",
            strategy_library_id=strategy_lib.id,
            symbol='EURUSD',  # 默认品种
            timeframe='H1',   # 默认周期
            params=strategy_lib.params_schema.get('properties', {}),
            status='ACTIVE'
        )
        session.add(strategy_instance)
        session.commit()
        
        # 通知Validator服务开始回测
        # （通过消息队列或API调用）
        print(f"📊 已触发回测: strategy_id={strategy_instance.id}")

# 使用示例
generator = StrategyGenerator()
strategy_lib = generator.generate_strategy(
    "创建一个基于EMA 12/26交叉的趋势跟踪策略，加入RSI过滤"
)
```

### 场景1：历史数据验证（纯回测）

```python
class Validator:
    def run_historical_backtest(self, strategy, start_date, end_date):
        """历史数据验证：不下真单"""
        # 1. 创建回测批次
        backtest_run = BacktestRun(
            strategy_id=strategy.id,
            symbol=strategy.symbol,
            timeframe=strategy.timeframe,
            start_date=start_date,
            end_date=end_date,
            status='RUNNING'
        )
        session.add(backtest_run)
        session.commit()
        
        # 2. 从historical_data获取历史K线
        bars = self.get_historical_bars(
            symbol=strategy.symbol,
            timeframe=strategy.timeframe,
            start_date=start_date,
            end_date=end_date
        )
        
        # 3. 模拟交易（不调用MT5 API）
        for signal in self.backtest_logic(strategy, bars):
            simulated_result = self._simulate_trade(signal)
            
            # 4. 写入validation.trades
            trade = Trade(
                ticket=None,                    # ❌ 无ticket
                execution_type='BACKTEST',      # ✅ 历史回测
                strategy_id=strategy.id,
                account_id=None,                # ❌ 不关联账户
                backtest_run_id=backtest_run.id,  # ✅ 关联回测批次
                
                symbol=signal.symbol,
                type=signal.type,
                volume=signal.volume,
                open_price=simulated_result.open_price,
                close_price=simulated_result.close_price,
                open_time=simulated_result.open_time,
                close_time=simulated_result.close_time,
                profit=simulated_result.profit,
                status='CLOSED'
            )
            session.add(trade)
        
        # 5. 更新回测批次状态
        backtest_run.status = 'SUCCESS'
        session.commit()
```

### 场景2：线上交易验证（真实下单）

```python
class Validator:
    def __init__(self):
        # 获取验证账户（Demo或Real小资金）
        self.validation_account = session.query(ValidationAccount).filter(
            ValidationAccount.account_type.in_(['DEMO', 'REAL_SMALL']),
            ValidationAccount.status == 'ACTIVE'
        ).first()
        
        # 获取MT5连接配置
        mt5_host = session.query(MT5Host).filter(
            MT5Host.id == self.validation_account.mt5_host_id
        ).first()
        
        # 初始化MT5客户端（与trading完全相同）
        self.mt5_client = UnifiedMT5Client(
            host=mt5_host.host,
            port=mt5_host.port,
            api_key=mt5_host.api_key,
            timeout=mt5_host.timeout
        )
    
    def run_live_validation(self, strategy):
        """线上交易验证：真实下单（从技术层面和trading完全一样）"""
        while True:
            # 1. 获取实时tick
            tick = self.mt5_client.get_tick(strategy.symbol)
            
            # 2. 策略生成信号
            signal = strategy.on_tick(tick)
            
            if signal:
                # 3. ✅ 真实下单（调用MT5 API）
                result = self.mt5_client.place_order(
                    symbol=signal.symbol,
                    type=signal.type,
                    volume=0.01,  # 小仓位
                    stop_loss=signal.stop_loss,
                    take_profit=signal.take_profit
                )
                
                # 4. 写入validation.trades
                trade = Trade(
                    ticket=result['ticket'],        # ✅ 有真实ticket
                    execution_type='LIVE',          # ✅ 线上交易
                    strategy_id=strategy.id,
                    account_id=self.validation_account.id,  # ✅ 关联验证账户
                    backtest_run_id=None,           # ❌ 不关联回测批次
                    
                    symbol=signal.symbol,
                    type=signal.type,
                    volume=0.01,
                    open_price=result['open_price'],
                    stop_loss=signal.stop_loss,
                    take_profit=signal.take_profit,
                    open_time=result['open_time'],
                    status='OPEN',
                    
                    mt5_host=self.mt5_client.host,
                    mt5_port=self.mt5_client.port
                )
                session.add(trade)
                session.commit()
```

### 场景3：Trading主账户交易

```python
class MT5Worker:
    def __init__(self):
        # 主账户（大资金Real账户）
        self.account = session.query(TradingAccount).filter(
            TradingAccount.id == 1,
            TradingAccount.account_type == 'REAL'
        ).first()
        
        # 获取MT5连接配置
        mt5_host = session.query(MT5Host).filter(
            MT5Host.id == self.account.mt5_host_id
        ).first()
        
        self.mt5_client = UnifiedMT5Client(
            host=mt5_host.host,
            port=mt5_host.port,
            api_key=mt5_host.api_key,
            timeout=mt5_host.timeout
        )
    
    def execute_signal(self, signal):
        """执行真实交易（大资金账户）"""
        # 真实下单
        result = self.mt5_client.place_order(
            symbol=signal.symbol,
            type=signal.type,
            volume=1.0  # 大手数
        )
        
        # 写入trading.trades
        trade = Trade(
            ticket=result['ticket'],
            strategy_id=signal.strategy_id,
            account_id=self.account.id,
            
            symbol=signal.symbol,
            type=signal.type,
            volume=1.0,
            open_price=result['open_price'],
            status='OPEN',
            
            mt5_host=self.mt5_client.host,
            mt5_port=self.mt5_client.port
        )
        session.add(trade)
        session.commit()
```

---

## 配置文件

```yaml
# config/cloud.yaml

# MT5连接配置（对应trading.mt5_hosts表）
mt5_hosts:
  demo_1:
    host: 192.168.1.101
    port: 9090
    api_key: demo_api_key_xxx
    max_connections: 5
    timeout: 30
    description: Demo账户MT5连接
    
  real_1:
    host: 192.168.1.100
    port: 9090
    api_key: real_api_key_xxx
    max_connections: 10
    timeout: 30
    description: 生产主MT5连接
    
  real_2:
    host: 192.168.1.100
    port: 9091
    api_key: real_api_key_yyy
    max_connections: 5
    timeout: 30
    description: 生产备用MT5连接

# Historical Data配置
historical_data:
  symbols:
    tier1:  # 核心货币对
      - symbol: EURUSD
        timeframes: [M5, M15, H1, H4, D1]
        enabled: true
      - symbol: GBPUSD
        timeframes: [M5, M15, H1, H4, D1]
        enabled: true
    
    tier2:  # 主流货币对
      - symbol: USDJPY
        timeframes: [H1, H4, D1]
        enabled: true
    
    tier3:  # 贵金属
      - symbol: XAUUSD
        timeframes: [M15, H1, H4, D1]
        enabled: true
  
  partitions:
    start_year: 2000
    end_year: 2040

# Trading主账户（大资金生产交易）
trading:
  accounts:
    - type: REAL
      number: 87654321
      broker: IC Markets
      initial_balance: 100000  # $10万
      mt5_host_name: real_1    # 关联到mt5_hosts.real_1
  
  risk_management:
    max_position_size: 5.0     # 最大5手
    max_daily_loss: 2000
    max_drawdown_pct: 10

# Validator验证
validation:
  # 线上交易验证账户
  live_validation:
    accounts:
      - type: DEMO
        number: 12345678
        broker: XM Global
        initial_balance: 10000  # Demo虚拟资金
        mt5_host_name: demo_1   # 关联到mt5_hosts.demo_1
        
      - type: REAL_SMALL
        number: 11111111
        broker: IC Markets
        initial_balance: 100    # $100真钱
        mt5_host_name: real_2   # 关联到mt5_hosts.real_2（备用）
    
    risk_management:
      max_position_size: 0.01   # 最大0.01手
      max_daily_loss: 10        # 最大亏损$10
      max_drawdown_pct: 20
  
  # 历史数据回测
  historical_backtest:
    enabled: true
    data_source: historical_data  # 使用historical_data schema
    default_timeframe: H1
    default_bars_count: 3000
```

---

## 权限管理

```sql
-- ============================================================
-- 权限管理（Schema级别隔离）
-- ============================================================

-- 创建不同角色
CREATE ROLE app_user LOGIN PASSWORD 'xxx';
CREATE ROLE dashboard_user LOGIN PASSWORD 'xxx';
CREATE ROLE validator_user LOGIN PASSWORD 'xxx';
CREATE ROLE import_user LOGIN PASSWORD 'xxx';

-- app_user: 全部权限
GRANT USAGE ON SCHEMA historical_data, trading, validation TO app_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA historical_data TO app_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA trading TO app_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA validation TO app_user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA trading, validation TO app_user;

-- dashboard_user: trading只读，validation只读
GRANT USAGE ON SCHEMA trading, validation TO dashboard_user;
GRANT SELECT ON ALL TABLES IN SCHEMA trading TO dashboard_user;
GRANT SELECT ON ALL TABLES IN SCHEMA validation TO dashboard_user;

-- validator_user: validation读写，historical_data只读
GRANT USAGE ON SCHEMA validation, historical_data TO validator_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA validation TO validator_user;
GRANT SELECT ON ALL TABLES IN SCHEMA historical_data TO validator_user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA validation TO validator_user;

-- import_user: historical_data读写
GRANT USAGE ON SCHEMA historical_data TO import_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA historical_data TO import_user;

-- 设置默认search_path
ALTER ROLE app_user SET search_path TO trading, validation, historical_data, public;
ALTER ROLE dashboard_user SET search_path TO trading, public;
ALTER ROLE validator_user SET search_path TO validation, historical_data, public;
ALTER ROLE import_user SET search_path TO historical_data, public;
```

---

## 备份和恢复

```bash
# 备份单个schema
pg_dump -U postgres -d evo_trade -n historical_data > historical_data_backup.sql
pg_dump -U postgres -d evo_trade -n trading > trading_backup.sql
pg_dump -U postgres -d evo_trade -n validation > validation_backup.sql

# 恢复单个schema
psql -U postgres -d evo_trade < historical_data_backup.sql

# 只备份trading schema的数据（不包括结构）
pg_dump -U postgres -d evo_trade -n trading --data-only > trading_data.sql

# 只备份表结构（不包括数据）
pg_dump -U postgres -d evo_trade -n trading --schema-only > trading_schema.sql

# 备份所有schema
pg_dump -U postgres -d evo_trade > full_backup.sql
```

---

## Python代码中使用Schema

```python
# src/common/database/connection.py

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager

class Database:
    def __init__(self):
        self.engine = create_engine(
            'postgresql://user:pass@localhost:5432/evo_trade',
            pool_size=10,
            max_overflow=20
        )
        self.SessionLocal = sessionmaker(bind=self.engine)
    
    @contextmanager
    def get_session(self, schema='trading'):
        """获取session，指定schema"""
        session = self.SessionLocal()
        try:
            # 设置search_path
            session.execute(f"SET search_path TO {schema}, public")
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

# 使用示例
db = Database()

# 操作trading schema
with db.get_session('trading') as session:
    trades = session.query(Trade).filter(...).all()

# 操作validation schema
with db.get_session('validation') as session:
    backtest_trades = session.query(Trade).filter(
        Trade.execution_type == 'BACKTEST'
    ).all()

# 操作historical_data schema
with db.get_session('historical_data') as session:
    bars = session.query(HistoricalBar).filter(...).all()
```

---

## 性能优化

### 索引优化

```sql
-- 查看索引使用情况
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_scan,  -- 索引被使用的次数
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes
WHERE schemaname IN ('historical_data', 'trading', 'validation')
ORDER BY idx_scan DESC;

-- 查看未使用的索引
SELECT 
    schemaname,
    tablename,
    indexname
FROM pg_stat_user_indexes
WHERE idx_scan = 0
  AND schemaname IN ('historical_data', 'trading', 'validation');
```

### 分区维护

```sql
-- 查看分区大小
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE tablename LIKE 'historical_bars_%'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- 添加新年度分区（每年1月1日）
CREATE TABLE IF NOT EXISTS historical_data.historical_bars_2041 
    PARTITION OF historical_data.historical_bars
    FOR VALUES FROM ('2041-01-01') TO ('2042-01-01');

-- 删除旧分区（如果不再需要）
DROP TABLE IF EXISTS historical_data.historical_bars_2000;

-- 分离旧分区（归档但不删除）
ALTER TABLE historical_data.historical_bars 
    DETACH PARTITION historical_data.historical_bars_2000;
```

### 查询优化

```sql
-- VACUUM ANALYZE（定期执行）
VACUUM ANALYZE historical_data.historical_bars;
VACUUM ANALYZE trading.trades;
VACUUM ANALYZE validation.trades;

-- 查看表膨胀
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as total_size,
    pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) as table_size,
    pg_size_pretty(pg_indexes_size(schemaname||'.'||tablename)) as indexes_size
FROM pg_tables
WHERE schemaname IN ('historical_data', 'trading', 'validation')
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

---

## 方案对比

### Schema分离 vs 单Schema

| 项目 | Schema分离（当前方案） | 单Schema+字段区分 |
|------|---------------------|------------------|
| **逻辑隔离** | ✅ 非常清晰 | ⚠️ 需要字段判断 |
| **权限管理** | ✅ Schema级别控制 | ⚠️ 行级别控制（复杂） |
| **备份恢复** | ✅ 可以单独备份schema | ⚠️ 需要条件过滤 |
| **查询复杂度** | ⚠️ 跨schema需要全路径 | ✅ 单表查询简单 |
| **表维护** | ⚠️ trading和validation两份 | ✅ 只维护一份 |
| **数据对比** | ⚠️ 需要JOIN不同schema | ✅ 单表过滤即可 |
| **推荐场景** | 大型系统、多团队协作 | 中小型系统、单团队 |

**结论**：Schema分离适合长期运营、多团队协作的专业系统 ✅

---

## 总结

### 核心设计

| Schema | 用途 | 账户类型 | 资金规模 | 下单方式 | 有ticket |
|--------|------|---------|---------|---------|----------|
| **historical_data** | 历史K线 | - | - | - | - |
| **trading** | 真实交易 | Real大资金 | $10万+ | MT5 Worker | ✅ 有 |
| **validation (LIVE)** | 线上验证 | Demo/Real小资金 | $10-$10,000 | Validator真实下单 | ✅ 有 |
| **validation (BACKTEST)** | 历史验证 | 无（虚拟） | 虚拟 | Validator模拟 | ❌ 无 |

### 关键理解

1. ✅ **使用3个独立Schema**（historical_data, trading, validation）
2. ✅ **trading schema包含元数据配置**（mt5_hosts, strategy_library）
3. ✅ **strategy_library（策略库）+ strategies（策略实例）分离设计**
   - 一个策略库代码可以生成多个实例
   - LLM生成 → 历史回测 → 线上验证 → 批准 → 生产
4. ✅ **mt5_hosts统一管理MT5连接配置**
   - trading.accounts和validation.accounts都关联到mt5_hosts
   - 一个MT5 Host可以服务多个账户
5. ✅ **Validation有两类验证**：
   - 线上交易验证（execution_type='LIVE'，有ticket）
   - 历史数据验证（execution_type='BACKTEST'，无ticket）
6. ✅ **线上交易验证从技术层面和trading完全一样**
7. ✅ **唯一区别是账户和仓位大小**
8. ✅ **大部分查询只访问单个schema**
9. ✅ **少数对比场景用应用层合并或CTE**

### 新增功能亮点 ⭐

- **LLM策略生成**：strategy_library表存储Claude生成的策略代码
- **策略验证流程**：PENDING → BACKTEST_PASSED → LIVE_TESTING → APPROVED
- **版本管理**：code_hash去重，parent_id支持迭代改进
- **集中连接管理**：mt5_hosts表统一管理所有MT5连接配置
- **灵活容灾**：一个账户可以快速切换到备用MT5 Host

### 优势

- ✅ 逻辑清晰、权限隔离、备份方便
- ✅ 数据安全（误删validation不影响trading）
- ✅ 性能隔离（validation大量写入不影响trading）
- ✅ 支持长期运营（40年分区，TB级数据）
- ✅ 符合PostgreSQL专业实践
- ✅ **支持AI驱动的策略生成和验证** ⭐
- ✅ **灵活的MT5连接管理和容灾** ⭐

**这个设计可以稳定使用20-30年！** 🚀
