# 历史数据导入指南

## 概述

系统支持三个阶段的历史K线数据导入，用于策略深度回测验证。

| 阶段 | 数据规模 | 首次导入 | 每日更新 | 单次回测 | 100策略批量 |
|------|---------|----------|----------|----------|-------------|
| **Phase 1** | 67K行 / 15MB | 3-8分钟 | 15秒 | 0.3-0.6秒 | **1分钟** ✅ |
| **Phase 2** | 3.2M行 / 500MB | 45-90分钟<br>(优化后20-30分钟) | 40秒 | 0.66秒 | **1.1分钟** ✅ |
| **Phase 3** | 50M行 / 3-4GB | 6-12小时<br>(优化后2-4小时) | 2.5分钟 | 0.8秒<br>(需优化) | **80秒**<br>(并行10秒) ✅ |

---

## Phase 1：保守起步（推荐首选）

### 数据规模
- **品种**：EURUSD, GBPUSD, USDJPY（3个）
- **周期**：H1, H4, D1（3个）
- **历史**：2年
- **数据量**：67,890根K线（约15MB）

### 使用场景
- ✅ 系统初次使用
- ✅ 验证功能可行性
- ✅ 快速测试策略
- ✅ 本地Mac开发

### 导入步骤

#### Windows环境

```bash
# 1. 确保MT5 API Bridge已启动
scripts\windows\start_mt5_api_bridge.bat

# 2. 创建数据库表
docker exec -i mt4-factory-postgres psql -U evo_trade_user -d evo_trade < scripts/database/postgres/create_historical_bars_table.sql

# 3. 导入Phase 1数据
set DEVICE=windows
python scripts/tools/import_historical_data.py --phase 1

# 预计耗时：3-8分钟
```

#### Mac环境（SQLite）

```bash
# 1. 创建数据库表
sqlite3 data/evo_trade.db < scripts/database/sqlite/create_historical_bars_table.sql

# 2. 导入Phase 1数据
# 注意：Mac上需要MT5 API Bridge运行在Windows机器上
export DEVICE=mac
python scripts/tools/import_historical_data.py --phase 1
```

### 预期结果

```
📦 Phase 1 - 保守起步
============================================================
品种数: 3
周期数: 3
历史年数: 2
预计数据量: 67,890 行 (15MB)
============================================================

[1/3] 导入 EURUSD...
  - H1: 预计 17,520 根...
    ✅ 导入 17,520 根
  - H4: 预计 4,380 根...
    ✅ 导入 4,380 根
  - D1: 预计 730 根...
    ✅ 导入 730 根
✅ EURUSD 导入完成

[2/3] 导入 GBPUSD...
  ...

[3/3] 导入 USDJPY...
  ...

============================================================
📊 导入完成
============================================================
✅ 成功品种: 3
❌ 失败品种: 0
📈 总K线数: 67,890 根
⏱️  总耗时: 245.3 秒 (4.1 分钟)
============================================================
```

---

## Phase 2：中等扩展

### 数据规模
- **品种**：10个主流货币对
- **周期**：M15, M30, H1, H4, D1（5个）
- **历史**：5年
- **数据量**：3,193,750根K线（约500MB）

### 使用场景
- ✅ Phase 1验证成功后
- ✅ 需要更多品种支持
- ✅ 策略需要更长历史验证
- ✅ 业务扩展阶段

### 导入步骤

```bash
# Windows环境
set DEVICE=windows
python scripts/tools/import_historical_data.py --phase 2

# 预计耗时：45-90分钟（优化后20-30分钟）
```

### 优化建议

```python
# 并行导入（在脚本中已实现）
# 使用4-8核CPU可以将时间缩短到20-30分钟
```

---

## Phase 3：大规模

### 数据规模
- **品种**：30个（货币对 + 贵金属 + 指数）
- **周期**：M5, M15, M30, H1, H4, D1, W1（7个）
- **历史**：10年
- **数据量**：50,714,100根K线（约3-4GB）

### 使用场景
- ✅ 系统成熟阶段
- ✅ 需要全面市场覆盖
- ✅ AI大规模策略生成
- ✅ 专业级交易系统

### 导入步骤

```bash
# Windows环境
set DEVICE=windows
python scripts/tools/import_historical_data.py --phase 3

# 预计耗时：6-12小时（优化后2-4小时）
# 建议：后台运行，分批导入
```

### 性能优化（必需）

Phase 3数据量大，**必须使用PostgreSQL分区表**：

```sql
-- 按年分区
CREATE TABLE historical_bars_2024 
    PARTITION OF historical_bars 
    FOR VALUES FROM ('2024-01-01') TO ('2025-01-01');

CREATE TABLE historical_bars_2023 
    PARTITION OF historical_bars 
    FOR VALUES FROM ('2023-01-01') TO ('2024-01-01');

-- 每年创建新分区
```

**执行脚本**：
```bash
docker exec -i mt4-factory-postgres psql -U evo_trade_user -d evo_trade < scripts/database/postgres/create_partitions.sql
```

**效果**：
- 查询速度提升5-10倍（8秒 → 0.8秒）
- $0成本，无需额外服务
- PostgreSQL原生支持，稳定可靠

---

## 自定义导入

### 导入特定品种和周期

```bash
# 导入EURUSD和GBPUSD的H1和H4数据，最近2年
python scripts/tools/import_historical_data.py \
    --symbols EURUSD,GBPUSD \
    --timeframes H1,H4 \
    --years 2
```

### 只导入单个品种

```bash
python scripts/tools/import_historical_data.py \
    --symbols EURUSD \
    --timeframes H1,H4,D1 \
    --years 5
```

---

## 每日更新数据

### 手动更新

```bash
# 更新最近1天的数据
python scripts/tools/update_historical_data.py --days 1
```

### 自动更新（推荐）

在 `config/windows.yaml` 或 `config/cloud.yaml` 配置：

```yaml
historical_data:
  auto_update: true
  update_schedule: "0 2 * * *"  # 每天凌晨2点
  update_days: 1
```

---

## 数据验证

### 检查数据完整性

```bash
# 查看数据统计
python scripts/tools/check_historical_data.py

# 输出示例：
# EURUSD: H1=17,520, H4=4,380, D1=730
# GBPUSD: H1=17,520, H4=4,380, D1=730
# ...
```

### SQL查询

```sql
-- 查看总行数
SELECT COUNT(*) FROM historical_bars;

-- 按品种统计
SELECT symbol, timeframe, COUNT(*) as bars_count
FROM historical_bars
GROUP BY symbol, timeframe
ORDER BY symbol, timeframe;

-- 查看最新数据时间
SELECT symbol, timeframe, MAX(time) as latest_time
FROM historical_bars
GROUP BY symbol, timeframe;
```

---

## Validator使用历史数据

### 配置Validator使用数据库

在 `config/windows.yaml` 中：

```yaml
validator:
  enabled: true
  data_source: "database"  # 或 "realtime"（实时MT5）
  bars_count: 3000         # 使用3000根历史数据
```

### 两种验证模式对比

| 模式 | 数据来源 | 优势 | 劣势 |
|------|---------|------|------|
| **Realtime** | 实时MT5 | 数据最新 | 有网络延迟 |
| **Database** | 历史数据库 | 速度快，离线可用 | 需要每日更新 |

**推荐**：Phase 1使用Realtime，Phase 2/3使用Database

---

## 性能对比

### 查询性能（有索引 vs 无索引）

```sql
-- 查询EURUSD最近3000根H1数据
SELECT * FROM historical_bars
WHERE symbol='EURUSD' AND timeframe='H1'
ORDER BY time DESC LIMIT 3000;

-- 有索引：50-100ms ✅
-- 无索引：5000ms ❌（慢50倍）
```

### 回测性能

| 阶段 | 数据量 | 查询时间 | 回测时间 | 总时间 |
|------|--------|---------|---------|--------|
| Phase 1 | 67K行 | 50ms | 300ms | **0.35秒** |
| Phase 2 | 3.2M行 | 80ms | 500ms | **0.58秒** |
| Phase 3 | 50M行 | 100ms | 600ms | **0.70秒** |
| Phase 3（未优化）| 50M行 | 8000ms | 600ms | **8.6秒** ❌ |

**关键**：索引和分区非常重要！

---

## 故障排查

### 1. 导入速度慢

**原因**：MT5连接慢或网络问题

**解决**：
```bash
# 检查MT5 API Bridge
curl http://localhost:9090/health

# 重启MT5 API Bridge
scripts\windows\start_mt5_api_bridge.bat
```

### 2. 数据重复

**原因**：重复导入

**解决**：
```sql
-- 删除重复数据（保留最新）
DELETE FROM historical_bars a USING historical_bars b
WHERE a.id < b.id
AND a.symbol = b.symbol
AND a.timeframe = b.timeframe
AND a.time = b.time;
```

### 3. 查询很慢

**原因**：缺少索引

**解决**：
```sql
-- 重建索引
REINDEX TABLE historical_bars;

-- 或手动创建索引
CREATE INDEX idx_historical_bars_symbol_timeframe_time
    ON historical_bars(symbol, timeframe, time DESC);
```

### 4. 磁盘空间不足（Phase 3）

**解决方案**：

```bash
# 1. 删除旧数据
DELETE FROM historical_bars WHERE time < '2020-01-01';

# 2. 清理数据库
VACUUM FULL historical_bars;

# 3. 压缩旧分区（如果使用分区表）
ALTER TABLE historical_bars_2020 SET (fillfactor = 70);
```

---

## 最佳实践

### 1. 分阶段导入

```
现在：Phase 1（验证可行性）
6个月后：Phase 2（扩展品种）
2年后：Phase 3（全面覆盖）
```

### 2. 定期更新

```bash
# 每天自动更新最新数据
crontab -e

# 添加：每天凌晨2点更新
0 2 * * * cd /path/to/MT4-Factory && python scripts/tools/update_historical_data.py --days 1
```

### 3. 备份数据

```bash
# PostgreSQL备份
pg_dump -U evo_trade_user -d evo_trade -t historical_bars > backup_historical_bars.sql

# SQLite备份
cp data/evo_trade.db data/evo_trade_backup_$(date +%Y%m%d).db
```

### 4. 监控性能

```sql
-- 查看慢查询
SELECT * FROM pg_stat_statements
WHERE query LIKE '%historical_bars%'
ORDER BY mean_exec_time DESC;
```

---

## Python回测准确度评估

### 总结对照表

| 策略类型 | Python准确度 | 是否推荐 | 备注 |
|---------|-------------|---------|------|
| **简单MA/RSI策略** | 95-98% | ✅ 强烈推荐 | 几乎无差异 |
| **多指标组合** | 85-93% | ✅ 推荐 | 注意指标算法 |
| **趋势跟踪** | 90-95% | ✅ 推荐 | 使用M1数据 |
| **网格/马丁** | 80-90% | ⚠️ 可用 | 注意订单管理 |
| **高频剥头皮** | 50-70% | ❌ 不推荐 | 需要tick数据 |
| **新闻交易** | 30-50% | ❌ 不推荐 | 数据不完整 |

### 高准确度的前提

✅ 策略基于K线收盘价  
✅ 不依赖tick数据  
✅ 使用标准技术指标  
✅ 有完整的历史数据  
✅ 模拟真实交易成本  

### 低准确度的原因

❌ 基于tick级别  
❌ 使用自定义MT5指标  
❌ 复杂订单管理逻辑  
❌ 依赖MT5特有功能  

### 适用场景判断

**如果你的MQL5策略是**：
- ✅ 基于常见指标（MA、RSI、MACD、布林带）
- ✅ 使用H1或以上周期
- ✅ 逻辑相对简单

→ **Python回测准确度可以达到90-95%，完全可用**

**如果你的策略是**：
- ❌ 高频剥头皮（M1以下）
- ❌ 依赖MT5自定义指标
- ❌ 复杂的tick级别操作

→ **Python回测准确度只有60-70%，不推荐**

### 验证方法

推荐使用混合验证流程：

1. **Python自动筛选**：用Python回测100个策略，筛选TOP 10
2. **MT5手动验证**：将TOP 10策略转为MQL5，在MT5中回测对比
3. **确认差异**：如果差异<10%即可接受
4. **实盘部署**：验证通过后部署到生产环境

这样既保证了自动化效率，又确保了结果准确性。

---

## 相关文档

- [历史数据性能与成本分析](./STRATEGY_VALIDATION_PERFORMANCE_COST.md)
- [Database脚本说明](../scripts/database/README.md)
- [Validator功能总结](./VALIDATOR_FEATURES_SUMMARY.md)
- [启动指南](./STARTUP_GUIDE.md)
