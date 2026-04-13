-- ============================================================
-- 历史数据层：1张表（无分区）
-- - historical_bars: K线数据
-- ============================================================

CREATE TABLE IF NOT EXISTS historical_bars (
    symbol VARCHAR(20) NOT NULL,
    timeframe VARCHAR(10) NOT NULL CHECK (timeframe IN ('M1', 'M5', 'M15', 'M30', 'H1', 'H4', 'D1', 'W1', 'MN')),
    time TIMESTAMP NOT NULL,
    open DECIMAL(10, 5) NOT NULL,
    high DECIMAL(10, 5) NOT NULL,
    low DECIMAL(10, 5) NOT NULL,
    close DECIMAL(10, 5) NOT NULL,
    volume INTEGER CHECK (volume >= 0),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,

    PRIMARY KEY (time, symbol, timeframe),

    CHECK (high >= low),
    CHECK (high >= open AND high >= close),
    CHECK (low <= open AND low <= close)
);

CREATE INDEX IF NOT EXISTS idx_historical_bars_lookup
    ON historical_bars(symbol, timeframe, time DESC);

SELECT '✓ 历史数据层创建完成：1张表（无分区）' AS progress;
