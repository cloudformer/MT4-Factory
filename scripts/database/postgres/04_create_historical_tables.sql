-- ============================================================
-- 04. 历史数据层（Historical Data Layer）
-- 用途: 历史K线数据（40年分区）
-- ============================================================

\set ON_ERROR_STOP on

\echo '▶ 04. 创建历史数据层...'

BEGIN;

-- 创建分区表
CREATE TABLE IF NOT EXISTS historical_bars (
    symbol VARCHAR(20) NOT NULL,
    timeframe VARCHAR(10) NOT NULL CHECK (timeframe IN ('M1', 'M5', 'M15', 'M30', 'H1', 'H4', 'D1', 'W1', 'MN')),
    time TIMESTAMP NOT NULL,
    open DECIMAL(10, 5) NOT NULL CHECK (open > 0),
    high DECIMAL(10, 5) NOT NULL CHECK (high > 0),
    low DECIMAL(10, 5) NOT NULL CHECK (low > 0),
    close DECIMAL(10, 5) NOT NULL CHECK (close > 0),
    volume BIGINT CHECK (volume >= 0),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    PRIMARY KEY (time, symbol, timeframe),
    CHECK (high >= low),
    CHECK (high >= open),
    CHECK (high >= close),
    CHECK (low <= open),
    CHECK (low <= close)
) PARTITION BY RANGE (time);

-- 创建2000-2040年分区（41年）
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

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_historical_bars_symbol_timeframe_time
    ON historical_bars(symbol, timeframe, time DESC);
CREATE INDEX IF NOT EXISTS idx_historical_bars_symbol ON historical_bars(symbol);
CREATE INDEX IF NOT EXISTS idx_historical_bars_timeframe ON historical_bars(timeframe);

COMMENT ON TABLE historical_bars IS '历史K线数据（40年分区，用于回测和策略验证）';

COMMIT;

\echo '✅ 04. 历史数据层创建完成 (historical_bars: 2000-2040, 41个分区)'
\echo ''
