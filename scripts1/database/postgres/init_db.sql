-- MT4 Factory 数据库初始化脚本
-- 创建必要的扩展和配置

-- 1. 启用UUID扩展（如果需要）
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 2. 设置时区
SET timezone = 'UTC';

-- 3. 创建数据库注释
COMMENT ON DATABASE evo_trade IS 'MT4 Factory - Strategy Trading System Database';

-- 4. 数据库配置（性能优化）
-- 注意：这些配置在Docker容器中会自动应用

-- 完成
SELECT 'Database initialized successfully' AS status;
