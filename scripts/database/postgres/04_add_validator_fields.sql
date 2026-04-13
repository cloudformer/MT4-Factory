-- 添加Validator验证结果字段到strategies表
-- 用途：存储Validator服务的验证结果

-- 添加params字段（如果不存在）
ALTER TABLE strategies ADD COLUMN IF NOT EXISTS params JSON;

-- 添加验证时间字段
ALTER TABLE strategies ADD COLUMN IF NOT EXISTS last_validation_time TIMESTAMP;

-- 添加验证结果字段
ALTER TABLE strategies ADD COLUMN IF NOT EXISTS validation_win_rate FLOAT;
ALTER TABLE strategies ADD COLUMN IF NOT EXISTS validation_total_return FLOAT;
ALTER TABLE strategies ADD COLUMN IF NOT EXISTS validation_total_trades INTEGER;
ALTER TABLE strategies ADD COLUMN IF NOT EXISTS validation_sharpe_ratio FLOAT;
ALTER TABLE strategies ADD COLUMN IF NOT EXISTS validation_max_drawdown FLOAT;
ALTER TABLE strategies ADD COLUMN IF NOT EXISTS validation_profit_factor FLOAT;

-- 创建索引（优化查询性能）
CREATE INDEX IF NOT EXISTS idx_strategies_status ON strategies(status);
CREATE INDEX IF NOT EXISTS idx_strategies_last_validation ON strategies(last_validation_time);

-- 注释
COMMENT ON COLUMN strategies.params IS '策略参数：symbol, timeframe等';
COMMENT ON COLUMN strategies.last_validation_time IS 'Validator最后验证时间';
COMMENT ON COLUMN strategies.validation_win_rate IS 'Validator验证胜率';
COMMENT ON COLUMN strategies.validation_total_return IS 'Validator验证总收益率';
COMMENT ON COLUMN strategies.validation_total_trades IS 'Validator验证总交易数';
COMMENT ON COLUMN strategies.validation_sharpe_ratio IS 'Validator验证Sharpe比率';
COMMENT ON COLUMN strategies.validation_max_drawdown IS 'Validator验证最大回撤';
COMMENT ON COLUMN strategies.validation_profit_factor IS 'Validator验证盈亏比';
