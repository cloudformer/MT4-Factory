-- SQLite版本：添加Validator验证结果字段到strategies表
-- 用途：存储Validator服务的验证结果

-- SQLite不支持 IF NOT EXISTS，需要先检查
-- 使用时如果字段已存在会报错，可以忽略

-- 添加params字段
ALTER TABLE strategies ADD COLUMN params TEXT;

-- 添加验证时间字段
ALTER TABLE strategies ADD COLUMN last_validation_time DATETIME;

-- 添加验证结果字段
ALTER TABLE strategies ADD COLUMN validation_win_rate REAL;
ALTER TABLE strategies ADD COLUMN validation_total_return REAL;
ALTER TABLE strategies ADD COLUMN validation_total_trades INTEGER;
ALTER TABLE strategies ADD COLUMN validation_sharpe_ratio REAL;
ALTER TABLE strategies ADD COLUMN validation_max_drawdown REAL;
ALTER TABLE strategies ADD COLUMN validation_profit_factor REAL;

-- SQLite创建索引
CREATE INDEX IF NOT EXISTS idx_strategies_status ON strategies(status);
CREATE INDEX IF NOT EXISTS idx_strategies_last_validation ON strategies(last_validation_time);
