# PostgreSQL 数据库脚本

## 📁 文件说明

所有脚本按照执行顺序编号：

| 脚本 | 说明 | 创建内容 |
|------|------|----------|
| `00_run_all.sql` | **主脚本**，执行所有初始化 | - |
| `01_init.sql` | 环境初始化 | 扩展、时区、配置 |
| `02_create_config_tables.sql` | 配置层表 | mt5_hosts, strategies, signals |
| `03_create_account_tables.sql` | 账户层表 | accounts, registrations |
| `04_create_historical_tables.sql` | 历史数据层 | historical_bars (41个分区) |
| `05_create_trade_tables.sql` | 真实交易层 | real_online_trades (21个分区), trades视图 |
| `06_create_validation_tables.sql` | 验证交易层 | validation_backtest_runs, validation_trades (21个分区) |
| `07_create_triggers.sql` | 触发器 | updated_at自动更新 |
| `08_verify.sql` | 验证脚本 | 统计、检查 |

## 🚀 快速开始

### 方式1：执行主脚本（推荐）

```bash
# 本地PostgreSQL
psql -U mt4factory -d mt4factory -f 00_run_all.sql

# Docker容器
docker exec -i mt4-factory-postgres psql -U mt4factory -d mt4factory < 00_run_all.sql
```

### 方式2：逐个执行

```bash
psql -U mt4factory -d mt4factory -f 01_init.sql
psql -U mt4factory -d mt4factory -f 02_create_config_tables.sql
psql -U mt4factory -d mt4factory -f 03_create_account_tables.sql
psql -U mt4factory -d mt4factory -f 04_create_historical_tables.sql
psql -U mt4factory -d mt4factory -f 05_create_trade_tables.sql
psql -U mt4factory -d mt4factory -f 06_create_validation_tables.sql
psql -U mt4factory -d mt4factory -f 07_create_triggers.sql
psql -U mt4factory -d mt4factory -f 08_verify.sql
```

## 📊 数据库结构

### 1. 配置层 (Config Layer)
- `mt5_hosts` - MT5 Worker节点配置
- `strategies` - 策略代码和性能指标
- `signals` - 交易信号

### 2. 账户层 (Account Layer)
- `accounts` - 统一账户表（REAL/DEMO）
- `registrations` - 策略与账户绑定

### 3. 历史数据层 (Historical Data)
- `historical_bars` - K线数据（2000-2040，41个分区）

### 4. 交易层 (Trading)
- `real_online_trades` - 真实交易（2020-2040，21个分区）
- `validation_trades` - 验证交易（2020-2040，21个分区）
- `validation_backtest_runs` - 回测批次

### 5. 视图 (Views)
- `trades` - 兼容性视图，指向 `real_online_trades`

## ⚙️ 特性

### ✅ 幂等性
所有 `CREATE` 语句都使用 `IF NOT EXISTS`，支持重复执行

### ✅ 分区表
- `historical_bars`: 按年分区（2000-2040）
- `real_online_trades`: 按年分区（2020-2040）
- `validation_trades`: 按年分区（2020-2040）

### ✅ 约束检查
- CHECK 约束：数据有效性（如 volume > 0）
- FOREIGN KEY：引用完整性
- UNIQUE：防止重复数据

### ✅ 自动更新
- `updated_at` 字段通过触发器自动更新

### ✅ 性能优化
- 索引：查询优化
- 分区：大数据性能
- JSONB：灵活存储

## 🔧 维护

### 添加新年度分区

```sql
-- 历史数据（2041年）
CREATE TABLE IF NOT EXISTS historical_bars_2041
PARTITION OF historical_bars
FOR VALUES FROM ('2041-01-01') TO ('2042-01-01');

-- 真实交易（2041年）
CREATE TABLE IF NOT EXISTS real_online_trades_2041
PARTITION OF real_online_trades
FOR VALUES FROM ('2041-01-01') TO ('2042-01-01');

-- 验证交易（2041年）
CREATE TABLE IF NOT EXISTS validation_trades_2041
PARTITION OF validation_trades
FOR VALUES FROM ('2041-01-01') TO ('2042-01-01');
```

### 删除旧分区

```sql
-- 删除2015年历史数据（释放空间）
DROP TABLE IF EXISTS historical_bars_2015;
```

### 重建索引

```sql
-- 重建所有索引
REINDEX DATABASE mt4factory;

-- 重建单个表索引
REINDEX TABLE strategies;
```

### 清理表空间

```sql
-- 清理死元组
VACUUM ANALYZE;

-- 完全清理并回收空间
VACUUM FULL;
```

## 📝 注意事项

1. **执行顺序**：必须按照编号顺序执行（00-08）
2. **外键约束**：表之间有依赖关系，不能单独删除
3. **分区表**：查询时会自动路由到相应分区
4. **备份**：生产环境请先备份后执行

## 🔍 验证

执行 `08_verify.sql` 或查询：

```sql
-- 查看所有表
\dt

-- 查看分区
SELECT tablename FROM pg_tables
WHERE tablename LIKE '%_20%'
ORDER BY tablename;

-- 查看表大小
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

## 🆘 故障排查

### 问题：外键约束错误

```
ERROR: insert or update on table "strategies" violates foreign key constraint
```

**解决：** 确保 `mt5_hosts` 表中存在引用的 `mt5_host_id`

### 问题：分区不存在

```
ERROR: no partition of relation "historical_bars" found for row
```

**解决：** 创建对应年份的分区

### 问题：权限不足

```
ERROR: must be owner of table
```

**解决：** 使用正确的数据库用户（mt4factory）
