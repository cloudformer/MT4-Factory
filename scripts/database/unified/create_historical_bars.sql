-- ============================================================
-- 历史K线表 - 三库通用版本
-- 适用于：SQLite、MySQL 8.0+、PostgreSQL 12+
-- ============================================================

-- 注意：根据数据库类型，部分语法需要调整
-- 使用时请选择对应的SQL块执行

-- ============================================================
-- SQLite 版本（Mac开发环境）
-- ============================================================
/*
CREATE TABLE IF NOT EXISTS historical_bars (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol VARCHAR(20) NOT NULL,
    timeframe VARCHAR(10) NOT NULL,
    time DATETIME NOT NULL,
    open DECIMAL(10, 5) NOT NULL,
    high DECIMAL(10, 5) NOT NULL,
    low DECIMAL(10, 5) NOT NULL,
    close DECIMAL(10, 5) NOT NULL,
    volume INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    -- 唯一约束
    UNIQUE(symbol, timeframe, time)
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_symbol_timeframe_time
    ON historical_bars(symbol, timeframe, time DESC);

CREATE INDEX IF NOT EXISTS idx_time
    ON historical_bars(time);
*/

-- ============================================================
-- MySQL 8.0+ 版本（生产环境 <30GB）
-- ============================================================
/*
CREATE TABLE IF NOT EXISTS historical_bars (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    timeframe VARCHAR(10) NOT NULL,
    time DATETIME NOT NULL,
    open DECIMAL(10, 5) NOT NULL,
    high DECIMAL(10, 5) NOT NULL,
    low DECIMAL(10, 5) NOT NULL,
    close DECIMAL(10, 5) NOT NULL,
    volume BIGINT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- 复合索引
    INDEX idx_symbol_timeframe_time (symbol, timeframe, time DESC),
    INDEX idx_time (time),

    -- 唯一约束
    UNIQUE KEY uk_symbol_timeframe_time (symbol, timeframe, time)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci
  ROW_FORMAT=COMPRESSED;

-- 数据量 >5GB 时启用分区（可选）
-- ALTER TABLE historical_bars
-- PARTITION BY RANGE (YEAR(time)) (
--     PARTITION p2020 VALUES LESS THAN (2021),
--     PARTITION p2021 VALUES LESS THAN (2022),
--     PARTITION p2022 VALUES LESS THAN (2023),
--     PARTITION p2023 VALUES LESS THAN (2024),
--     PARTITION p2024 VALUES LESS THAN (2025),
--     PARTITION p2025 VALUES LESS THAN (2026),
--     PARTITION p_future VALUES LESS THAN MAXVALUE
-- );
*/

-- ============================================================
-- PostgreSQL 12+ 版本（大规模数据 >30GB）
-- ============================================================
/*
CREATE TABLE IF NOT EXISTS historical_bars (
    id BIGSERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    timeframe VARCHAR(10) NOT NULL,
    time TIMESTAMP NOT NULL,
    open DECIMAL(10, 5) NOT NULL,
    high DECIMAL(10, 5) NOT NULL,
    low DECIMAL(10, 5) NOT NULL,
    close DECIMAL(10, 5) NOT NULL,
    volume BIGINT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- 唯一约束
    UNIQUE(symbol, timeframe, time)
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_symbol_timeframe_time
    ON historical_bars(symbol, timeframe, time DESC);

CREATE INDEX IF NOT EXISTS idx_time
    ON historical_bars(time);

-- 分区表（推荐）
-- 先删除表，重新创建为分区表
/*
DROP TABLE IF EXISTS historical_bars CASCADE;

CREATE TABLE historical_bars (
    id BIGSERIAL,
    symbol VARCHAR(20) NOT NULL,
    timeframe VARCHAR(10) NOT NULL,
    time TIMESTAMP NOT NULL,
    open DECIMAL(10, 5) NOT NULL,
    high DECIMAL(10, 5) NOT NULL,
    low DECIMAL(10, 5) NOT NULL,
    close DECIMAL(10, 5) NOT NULL,
    volume BIGINT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (time, symbol, timeframe)
) PARTITION BY RANGE (time);

-- 创建年度分区
CREATE TABLE historical_bars_2020 PARTITION OF historical_bars
    FOR VALUES FROM ('2020-01-01') TO ('2021-01-01');

CREATE TABLE historical_bars_2021 PARTITION OF historical_bars
    FOR VALUES FROM ('2021-01-01') TO ('2022-01-01');

CREATE TABLE historical_bars_2022 PARTITION OF historical_bars
    FOR VALUES FROM ('2022-01-01') TO ('2023-01-01');

CREATE TABLE historical_bars_2023 PARTITION OF historical_bars
    FOR VALUES FROM ('2023-01-01') TO ('2024-01-01');

CREATE TABLE historical_bars_2024 PARTITION OF historical_bars
    FOR VALUES FROM ('2024-01-01') TO ('2025-01-01');

CREATE TABLE historical_bars_2025 PARTITION OF historical_bars
    FOR VALUES FROM ('2025-01-01') TO ('2026-01-01');

CREATE TABLE historical_bars_future PARTITION OF historical_bars
    FOR VALUES FROM ('2026-01-01') TO ('2030-01-01');

-- 索引（在每个分区上自动创建）
CREATE INDEX idx_symbol_timeframe_time ON historical_bars(symbol, timeframe, time DESC);
*/

-- ============================================================
-- PostgreSQL + TimescaleDB（超大规模 >100GB）
-- ============================================================
/*
-- 先安装TimescaleDB扩展
CREATE EXTENSION IF NOT EXISTS timescaledb;

CREATE TABLE IF NOT EXISTS historical_bars (
    time TIMESTAMP NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    timeframe VARCHAR(10) NOT NULL,
    open DECIMAL(10, 5) NOT NULL,
    high DECIMAL(10, 5) NOT NULL,
    low DECIMAL(10, 5) NOT NULL,
    close DECIMAL(10, 5) NOT NULL,
    volume BIGINT
);

-- 转换为时序表（Hypertable）
SELECT create_hypertable('historical_bars', 'time');

-- 创建索引
CREATE INDEX idx_symbol_timeframe_time
    ON historical_bars(symbol, timeframe, time DESC);

-- 数据保留策略（可选）
SELECT add_retention_policy('historical_bars', INTERVAL '3 years');

-- 自动压缩（节省50-70%空间）
ALTER TABLE historical_bars SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'symbol,timeframe'
);

SELECT add_compression_policy('historical_bars', INTERVAL '30 days');
*/
