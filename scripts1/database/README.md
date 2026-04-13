# Database Scripts 数据库脚本

数据库脚本按照数据库类型分类管理。

## 目录结构

```
scripts/database/
├── postgres/               # PostgreSQL专用脚本
│   ├── init_db.sql        # 数据库初始化
│   └── add_validator_fields.sql  # 添加Validator字段
├── sqlite/                 # SQLite专用脚本
│   └── add_validator_fields.sql  # 添加Validator字段
└── migrate_sqlite_to_postgres.py  # 迁移工具
```

---

## 三种数据库环境

| 环境 | 数据库 | 配置文件 | 脚本目录 |
|------|--------|---------|---------|
| Mac本地 | SQLite | `config/mac.yaml` | `sqlite/` |
| Windows Docker | PostgreSQL | `config/windows.yaml` | `postgres/` |
| 云端生产 | PostgreSQL RDS | `config/cloud.yaml` | `postgres/` |

**统一使用标准PostgreSQL**，保持环境一致性，不引入额外技术栈。

---

## PostgreSQL脚本 (`postgres/`)

### 适用环境
- Windows Docker容器
- 云端PostgreSQL RDS
- 任何PostgreSQL 12+数据库

### 脚本说明

#### `init_db.sql` - 数据库初始化
```bash
# Docker容器
docker exec -i mt4-factory-postgres psql -U evo_trade_user -d evo_trade < scripts/database/postgres/init_db.sql

# 云端RDS（需要先配置连接）
psql -h your-rds.xxx.rds.amazonaws.com -U evo_trade_user -d evo_trade < scripts/database/postgres/init_db.sql
```

**功能**：
- 启用UUID扩展
- 设置时区为UTC
- 添加数据库注释

#### `add_validator_fields.sql` - 添加Validator字段
```bash
# Docker容器
docker exec -i mt4-factory-postgres psql -U evo_trade_user -d evo_trade < scripts/database/postgres/add_validator_fields.sql

# 云端RDS
psql -h your-rds.xxx.rds.amazonaws.com -U evo_trade_user -d evo_trade < scripts/database/postgres/add_validator_fields.sql
```

**功能**：
- 添加 `params` 字段（JSON类型）
- 添加 `last_validation_time` 字段
- 添加6个验证结果字段
- 创建性能索引

**字段列表**：
- `validation_win_rate` - 验证胜率
- `validation_total_return` - 验证总收益率
- `validation_total_trades` - 验证总交易数
- `validation_sharpe_ratio` - Sharpe比率
- `validation_max_drawdown` - 最大回撤
- `validation_profit_factor` - 盈亏比

---

## SQLite脚本 (`sqlite/`)

### 适用环境
- Mac本地开发（`data/evo_trade.db`）

### 脚本说明

#### `add_validator_fields.sql` - 添加Validator字段
```bash
# Mac本地
sqlite3 data/evo_trade.db < scripts/database/sqlite/add_validator_fields.sql
```

**注意**：
- SQLite不支持 `IF NOT EXISTS`，如果字段已存在会报错
- JSON字段使用TEXT类型存储
- FLOAT字段使用REAL类型

**与PostgreSQL版本的差异**：
| 特性 | PostgreSQL | SQLite |
|------|-----------|--------|
| JSON类型 | `JSON` | `TEXT` |
| Float类型 | `FLOAT` | `REAL` |
| IF NOT EXISTS | ✅ 支持 | ❌ 不支持 |
| 扩展 | ✅ uuid-ossp | ❌ 无 |
| 注释 | ✅ COMMENT ON | ❌ 不支持 |

---

## 迁移工具

### `migrate_sqlite_to_postgres.py` - 数据迁移

从SQLite迁移数据到PostgreSQL（Docker或RDS）。

```bash
# 配置源和目标数据库
export DEVICE=mac
python scripts/database/migrate_sqlite_to_postgres.py
```

**功能**：
- 读取SQLite数据
- 转换数据格式
- 写入PostgreSQL
- 验证迁移结果

**支持迁移**：
- Mac SQLite → Windows Docker PostgreSQL
- Mac SQLite → Cloud RDS PostgreSQL

---

## 使用场景

### 场景1：Mac首次使用
SQLite自动创建，无需手动初始化。

```bash
# 如果需要添加Validator字段
sqlite3 data/evo_trade.db < scripts/database/sqlite/add_validator_fields.sql
```

### 场景2：Windows首次使用
```bash
# 1. 启动PostgreSQL容器
docker-compose up -d postgres

# 2. 等待容器启动
timeout /t 5

# 3. 初始化数据库
docker exec -i mt4-factory-postgres psql -U evo_trade_user -d evo_trade < scripts/database/postgres/init_db.sql

# 4. 添加Validator字段
docker exec -i mt4-factory-postgres psql -U evo_trade_user -d evo_trade < scripts/database/postgres/add_validator_fields.sql
```

### 场景3：Mac数据迁移到Windows
```bash
# Mac上运行迁移脚本
python scripts/database/migrate_sqlite_to_postgres.py
```

### 场景4：云端RDS初始化
```bash
# 配置RDS连接信息
export DB_HOST=your-rds.xxx.rds.amazonaws.com
export DB_USER=evo_trade_user
export DB_PASS=your_password
export DB_NAME=evo_trade

# 初始化
psql -h $DB_HOST -U $DB_USER -d $DB_NAME < scripts/database/postgres/init_db.sql
psql -h $DB_HOST -U $DB_USER -d $DB_NAME < scripts/database/postgres/add_validator_fields.sql
```

---

## PostgreSQL vs SQLite 对比

| 维度 | SQLite | PostgreSQL Docker | PostgreSQL RDS |
|------|--------|------------------|----------------|
| **部署** | 单文件 | Docker容器 | 云端托管 |
| **性能** | 轻量快速 | 中等 | 高性能 |
| **并发** | 单写多读 | 多写多读 | 多写多读 |
| **扩展** | 无 | ✅ 丰富 | ✅ 丰富 |
| **备份** | 复制文件 | Docker volume | RDS自动备份 |
| **适用** | 开发测试 | 完整测试 | 生产环境 |
| **成本** | 免费 | 免费 | 按需付费 |

---

## 数据库表结构

### strategies 表

```sql
-- PostgreSQL版本
CREATE TABLE strategies (
    id VARCHAR(32) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    code TEXT NOT NULL,
    status VARCHAR(9) NOT NULL,  -- candidate/active/archived
    performance JSON,              -- 初始回测结果
    params JSON,                   -- 策略参数（symbol, timeframe等）
    
    -- Validator验证结果字段
    last_validation_time TIMESTAMP,
    validation_win_rate FLOAT,
    validation_total_return FLOAT,
    validation_total_trades INTEGER,
    validation_sharpe_ratio FLOAT,
    validation_max_drawdown FLOAT,
    validation_profit_factor FLOAT,
    
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
);

-- 索引
CREATE INDEX idx_strategies_status ON strategies(status);
CREATE INDEX idx_strategies_last_validation ON strategies(last_validation_time);
```

---

## 常见问题

### 1. SQLite字段已存在错误
```bash
Error: duplicate column name: params
```

**解决**：字段已存在，忽略此错误即可。

### 2. PostgreSQL连接失败
```bash
# 检查容器状态
docker-compose ps postgres

# 查看日志
docker-compose logs postgres

# 测试连接
docker exec -it mt4-factory-postgres psql -U evo_trade_user -d evo_trade
```

### 3. RDS连接超时
- 检查安全组配置
- 确认端口5432已开放
- 验证VPC/网络配置

---

## 最佳实践

### 开发环境（Mac）
- 使用SQLite轻量快速
- 定期备份 `data/evo_trade.db`

### 测试环境（Windows）
- 使用PostgreSQL Docker
- 测试完整数据库功能
- 验证迁移脚本

### 生产环境（Cloud）
- 使用PostgreSQL RDS
- 启用自动备份
- 配置读写分离
- 监控性能指标

---

## 相关文档

- [启动指南](../../docs/STARTUP_GUIDE.md)
- [配置文件说明](../../config/README.md)
- [Validator功能](../../docs/VALIDATOR_FEATURES_SUMMARY.md)
