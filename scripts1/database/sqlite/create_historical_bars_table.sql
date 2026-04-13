-- SQLite版本：创建历史K线数据表
-- 用于Mac本地开发

CREATE TABLE IF NOT EXISTS historical_bars (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    time DATETIME NOT NULL,

    -- OHLCV数据
    open REAL NOT NULL,
    high REAL NOT NULL,
    low REAL NOT NULL,
    close REAL NOT NULL,
    volume INTEGER,

    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_historical_bars_symbol ON historical_bars(symbol);
CREATE INDEX IF NOT EXISTS idx_historical_bars_timeframe ON historical_bars(timeframe);
CREATE INDEX IF NOT EXISTS idx_historical_bars_time ON historical_bars(time);

-- 复合索引（最关键）
CREATE INDEX IF NOT EXISTS idx_historical_bars_symbol_timeframe_time
    ON historical_bars(symbol, timeframe, time DESC);

CREATE INDEX IF NOT EXISTS idx_historical_bars_time_symbol
    ON historical_bars(time, symbol);

-- 唯一约束
CREATE UNIQUE INDEX IF NOT EXISTS idx_historical_bars_unique
    ON historical_bars(symbol, timeframe, time);

-- 查看表结构
.schema historical_bars
