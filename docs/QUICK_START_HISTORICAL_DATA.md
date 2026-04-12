# 历史数据快速开始

## 5分钟快速导入Phase 1数据

### Windows环境

```bash
# 1. 启动MT5 API Bridge
scripts\windows\start_mt5_api_bridge.bat

# 2. 确保PostgreSQL运行
docker-compose up -d postgres

# 3. 创建历史数据表
docker exec -i mt4-factory-postgres psql -U evo_trade_user -d evo_trade < scripts/database/postgres/create_historical_bars_table.sql

# 4. 导入Phase 1数据（3品种×3周期×2年）
set DEVICE=windows
python scripts/tools/import_historical_data.py --phase 1

# 等待3-8分钟完成
```

### 验证导入结果

```bash
# 查看数据量
docker exec -it mt4-factory-postgres psql -U evo_trade_user -d evo_trade -c "SELECT COUNT(*) FROM historical_bars;"

# 预期结果：约67,890行

# 查看品种分布
docker exec -it mt4-factory-postgres psql -U evo_trade_user -d evo_trade -c "
SELECT symbol, timeframe, COUNT(*) as bars_count
FROM historical_bars
GROUP BY symbol, timeframe
ORDER BY symbol, timeframe;
"

# 预期输出：
#  symbol  | timeframe | bars_count
# ---------+-----------+------------
#  EURUSD  | D1        |        730
#  EURUSD  | H1        |      17520
#  EURUSD  | H4        |       4380
#  GBPUSD  | D1        |        730
#  GBPUSD  | H1        |      17520
#  GBPUSD  | H4        |       4380
#  USDJPY  | D1        |        730
#  USDJPY  | H1        |      17520
#  USDJPY  | H4        |       4380
```

### 测试回测速度

```bash
# 启动Python环境
python

# 测试查询和回测
from src.common.database.connection import db
from src.common.models.historical_bar import HistoricalBar
from sqlalchemy import desc
import time

with db.session_scope() as session:
    start = time.time()
    
    # 查询EURUSD最近3000根H1数据
    bars = session.query(HistoricalBar)\
        .filter(HistoricalBar.symbol == 'EURUSD')\
        .filter(HistoricalBar.timeframe == 'H1')\
        .order_by(desc(HistoricalBar.time))\
        .limit(3000)\
        .all()
    
    end = time.time()
    print(f"查询 {len(bars)} 根K线耗时: {(end-start)*1000:.1f}ms")

# 预期：50-100ms ✅
```

---

## Mac环境（SQLite）

```bash
# 1. 创建历史数据表
sqlite3 data/evo_trade.db < scripts/database/sqlite/create_historical_bars_table.sql

# 2. 导入Phase 1数据
# 注意：需要Windows机器上的MT5 API Bridge运行
export DEVICE=mac
python scripts/tools/import_historical_data.py --phase 1
```

---

## 常见问题

### 1. 导入很慢

**原因**：MT5连接慢

**解决**：
```bash
# 测试MT5 API Bridge
curl http://localhost:9090/health

# 如果失败，重启MT5 API Bridge
scripts\windows\start_mt5_api_bridge.bat
```

### 2. 数据库连接失败

**Windows**：
```bash
# 检查PostgreSQL容器
docker-compose ps postgres

# 重启
docker-compose restart postgres
```

**Mac**：
```bash
# 检查SQLite文件
ls -lh data/evo_trade.db

# 如果不存在，创建表
sqlite3 data/evo_trade.db < scripts/database/sqlite/create_historical_bars_table.sql
```

### 3. 已有数据，不想重复导入

**清空表重新导入**：
```sql
-- PostgreSQL
TRUNCATE TABLE historical_bars;

-- SQLite
DELETE FROM historical_bars;
```

---

## 下一步

### 扩展到Phase 2（6个月后）

```bash
python scripts/tools/import_historical_data.py --phase 2
# 10品种 × 5周期 × 5年
# 预计耗时：45-90分钟
```

### 扩展到Phase 3（2年后）

```bash
# 1. 先创建分区表
docker exec -i mt4-factory-postgres psql -U evo_trade_user -d evo_trade < scripts/database/postgres/create_partitions.sql

# 2. 导入数据
python scripts/tools/import_historical_data.py --phase 3
# 30品种 × 7周期 × 10年
# 预计耗时：6-12小时（建议后台运行）
```

---

## 相关文档

- [历史数据完整指南](./HISTORICAL_DATA_GUIDE.md)
- [性能与成本分析](./STRATEGY_VALIDATION_PERFORMANCE_COST.md)
- [Database脚本说明](../scripts/database/README.md)
