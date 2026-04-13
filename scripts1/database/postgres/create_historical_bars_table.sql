-- 创建历史K线数据表
-- 用于存储Phase 1/2/3的历史数据

CREATE TABLE IF NOT EXISTS historical_bars (
    id BIGSERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    timeframe VARCHAR(10) NOT NULL,
    time TIMESTAMP NOT NULL,

    -- OHLCV数据
    open DECIMAL(10,5) NOT NULL,
    high DECIMAL(10,5) NOT NULL,
    low DECIMAL(10,5) NOT NULL,
    close DECIMAL(10,5) NOT NULL,
    volume BIGINT,

    created_at TIMESTAMP DEFAULT NOW()
);

-- 创建索引（非常重要，查询性能提升10-100倍）
CREATE INDEX IF NOT EXISTS idx_historical_bars_symbol ON historical_bars(symbol);
CREATE INDEX IF NOT EXISTS idx_historical_bars_timeframe ON historical_bars(timeframe);
CREATE INDEX IF NOT EXISTS idx_historical_bars_time ON historical_bars(time);

-- 复合索引（最关键，用于快速查询）
CREATE INDEX IF NOT EXISTS idx_historical_bars_symbol_timeframe_time
    ON historical_bars(symbol, timeframe, time DESC);

CREATE INDEX IF NOT EXISTS idx_historical_bars_time_symbol
    ON historical_bars(time, symbol);

-- 唯一约束（防止重复数据）
CREATE UNIQUE INDEX IF NOT EXISTS idx_historical_bars_unique
    ON historical_bars(symbol, timeframe, time);

-- 注释
COMMENT ON TABLE historical_bars IS '历史K线数据表';
COMMENT ON COLUMN historical_bars.symbol IS '交易品种：EURUSD, GBPUSD等';
COMMENT ON COLUMN historical_bars.timeframe IS '时间周期：M5, M15, H1, H4, D1, W1等';
COMMENT ON COLUMN historical_bars.time IS 'K线时间';
COMMENT ON COLUMN historical_bars.open IS '开盘价';
COMMENT ON COLUMN historical_bars.high IS '最高价';
COMMENT ON COLUMN historical_bars.low IS '最低价';
COMMENT ON COLUMN historical_bars.close IS '收盘价';
COMMENT ON COLUMN historical_bars.volume IS '成交量';

-- 显示表信息
SELECT 'historical_bars 表创建成功' AS status;
\d historical_bars
