# 环境配置说明

## 三个环境的角色定位

| 环境 | 用途 | 数据库 | Validator | 历史数据 | MT5连接 |
|------|------|--------|-----------|---------|---------|
| **Mac** | UI开发和测试 | SQLite | ❌ 不运行 | ❌ 不导入 | ❌ 不连接 |
| **Windows** | 完整测试环境 | PostgreSQL Docker | ✅ 运行 | ✅ Phase 1/2/3 | ✅ 本地MT5 |
| **Cloud** | 生产环境 | PostgreSQL RDS | ✅ 运行 | ✅ Phase 3 | ✅ 远程MT5 |

---

## Mac环境（UI开发）

### 定位
- **纯前端开发**：Dashboard UI界面开发和测试
- **快速迭代**：无需启动复杂服务
- **轻量级**：SQLite数据库，无Docker依赖

### 配置文件
```yaml
# config/mac.yaml
database:
  url: "sqlite:///./data/evo_trade.db"  # 轻量级SQLite

validator:
  enabled: false  # 不运行Validator

mt5:
  enabled: false  # 不连接MT5

historical_data:
  enabled: false  # 不导入历史数据
```

### 启动方式
```bash
export DEVICE=mac
./scripts/mac/start_mac.sh

# 仅启动Dashboard UI
# http://localhost:8001
```

### 适用场景
- ✅ 前端UI开发
- ✅ 页面布局调整
- ✅ 交互逻辑测试
- ✅ 查看模拟数据
- ❌ 不做策略验证
- ❌ 不测试MT5连接
- ❌ 不处理真实交易

---

## Windows环境（完整测试）

### 定位
- **功能完整性测试**：测试所有功能模块
- **性能测试**：验证回测速度和并发能力
- **PostgreSQL优化测试**：索引和分区表优化

### 配置文件
```yaml
# config/windows.yaml
database:
  host: "postgres"  # PostgreSQL Docker容器
  port: 5432
  database: "evo_trade"
  user: "evo_trade_user"
  password: "evo_trade_pass_dev_2024"

validator:
  enabled: true
  concurrency: 20
  data_source: "database"  # 使用历史数据
  bars_count: 3000

mt5:
  host: "host.docker.internal"  # 本地MT5
  port: 9090
  api_key: "demo_key_12345"

historical_data:
  enabled: true
  phase: 1  # 或 2/3
  auto_update: false
```

### 启动方式
```bash
# 1. 启动PostgreSQL
docker-compose up -d postgres

# 2. 启动MT5 API Bridge
scripts\windows\start_mt5_api_bridge.bat

# 3. 导入历史数据（可选）
set DEVICE=windows
python scripts/tools/import_historical_data.py --phase 1

# 4. 启动Dashboard
scripts\windows\start_windows.bat
```

### PostgreSQL优化（Windows环境测试）

**Phase 1/2：索引优化**
```sql
-- 创建表
docker exec -i mt4-factory-postgres psql -U evo_trade_user -d evo_trade < scripts/database/postgres/create_historical_bars_table.sql

-- 索引自动创建，查询速度提升10-100倍
```

**Phase 3：分区表优化**
```sql
-- 创建分区表
docker exec -i mt4-factory-postgres psql -U evo_trade_user -d evo_trade < scripts/database/postgres/create_partitions.sql

-- 查询速度再提升5-10倍
```

### 适用场景
- ✅ 完整功能测试
- ✅ 策略验证测试
- ✅ MT5连接测试
- ✅ 历史数据导入测试
- ✅ PostgreSQL优化验证
- ✅ 性能基准测试

---

## Cloud环境（生产部署）

### 定位
- **7x24生产运行**：持续提供服务
- **大规模数据处理**：Phase 3历史数据
- **高可用性**：云端RDS + 远程MT5

### 配置文件
```yaml
# config/cloud.yaml
database:
  host: "your-rds.amazonaws.com"  # PostgreSQL RDS
  port: 5432
  database: "evo_trade"
  user: "evo_trade_user"
  password: "${DB_PASSWORD}"  # 环境变量

validator:
  enabled: true
  concurrency: 50  # 更高并发
  data_source: "database"
  bars_count: 3000

mt5:
  host: "52.10.20.30"  # 远程Windows VPS
  port: 9090
  api_key: "${MT5_API_KEY}"  # 环境变量

historical_data:
  enabled: true
  phase: 3  # 大规模数据
  auto_update: true  # 每日自动更新
  update_schedule: "0 2 * * *"  # 凌晨2点
```

### 部署步骤
```bash
# 1. 初始化RDS数据库
psql -h your-rds.amazonaws.com -U evo_trade_user -d evo_trade < scripts/database/postgres/create_historical_bars_table.sql
psql -h your-rds.amazonaws.com -U evo_trade_user -d evo_trade < scripts/database/postgres/create_partitions.sql

# 2. 导入历史数据
export DEVICE=cloud
python scripts/tools/import_historical_data.py --phase 3
# 预计6-12小时，建议分批后台运行

# 3. 配置自动更新
crontab -e
# 0 2 * * * cd /app && python scripts/tools/update_historical_data.py --days 1

# 4. 启动服务
export DEVICE=cloud
uvicorn src.services.dashboard.api.app:app --host 0.0.0.0 --port 8001
```

### PostgreSQL优化（与Windows完全一致）

**相同的索引**：
```sql
CREATE INDEX idx_historical_bars_symbol_timeframe_time
    ON historical_bars(symbol, timeframe, time DESC);
```

**相同的分区表**：
```sql
CREATE TABLE historical_bars_2024 PARTITION OF historical_bars
    FOR VALUES FROM ('2024-01-01') TO ('2025-01-01');
```

**相同的查询性能**：
- Phase 1: 50ms
- Phase 2: 80ms
- Phase 3: 100ms（分区表优化后）

### 适用场景
- ✅ 生产环境运行
- ✅ 大规模策略验证
- ✅ 7x24持续服务
- ✅ 自动化数据更新
- ✅ 高并发处理

---

## PostgreSQL优化一致性

### 核心原则
**Windows和Cloud使用完全相同的PostgreSQL配置和优化方案**

### 优化技术（PostgreSQL原生）

| 优化方式 | Phase 1 | Phase 2 | Phase 3 | 说明 |
|---------|---------|---------|---------|------|
| **索引** | ✅ | ✅ | ✅ | 查询提速10-100倍 |
| **分区表** | ❌ | ❌ | ✅ | 查询提速5-10倍 |
| **并行回测** | 可选 | 推荐 | ✅ | Python AsyncIO，提速4-8倍 |

### 相同的SQL脚本

**Windows Docker环境**：
```bash
docker exec -i mt4-factory-postgres psql -U evo_trade_user -d evo_trade < scripts/database/postgres/create_historical_bars_table.sql
```

**Cloud RDS环境**：
```bash
psql -h your-rds.amazonaws.com -U evo_trade_user -d evo_trade < scripts/database/postgres/create_historical_bars_table.sql
```

**结果**：完全相同的表结构、索引和性能！

### 性能保证（Windows = Cloud）

| 阶段 | 数据量 | 查询时间 | 100策略验证 |
|------|--------|---------|-------------|
| Phase 1 | 67K行 | 50ms | 1分钟 |
| Phase 2 | 3.2M行 | 80ms | 1.1分钟 |
| Phase 3 | 50M行 | 100ms | 80秒（并行10秒）|

---

## 数据库版本一致性

### 推荐版本
- **PostgreSQL 16** （Windows Docker + Cloud RDS）
- 不使用任何特殊扩展或插件

### Docker配置
```yaml
# docker-compose.yml
postgres:
  image: postgres:16-alpine  # 与RDS版本一致
  environment:
    POSTGRES_DB: evo_trade
    POSTGRES_USER: evo_trade_user
    POSTGRES_PASSWORD: evo_trade_pass_dev_2024
```

### RDS配置
- 引擎：PostgreSQL 16.x
- 参数组：默认（无特殊配置）
- 扩展：无需安装额外扩展

---

## 环境切换

### 开发流程
```
Mac (UI开发)
    ↓ 提交代码
Windows (完整测试)
    ↓ 测试通过
Cloud (生产部署)
```

### 切换命令
```bash
# Mac环境
export DEVICE=mac
./scripts/mac/start_mac.sh

# Windows环境
set DEVICE=windows
scripts\windows\start_all.bat

# Cloud环境
export DEVICE=cloud
# 使用systemd或Docker Compose部署
```

---

## 总结

### Mac环境
- 🎨 UI开发和测试
- 💡 SQLite轻量级
- ⚡ 快速启动

### Windows环境
- 🧪 完整功能测试
- 🔧 PostgreSQL优化验证
- 📊 性能基准测试

### Cloud环境
- 🚀 生产环境部署
- 📈 大规模数据处理
- 🔄 7x24持续运行

**关键**：Windows和Cloud使用**完全相同的PostgreSQL配置**，保证环境一致性！
