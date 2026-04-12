# 历史数据回测 - 详细操作分解

## 📊 四个核心指标的深度解析

### 1️⃣ 首次导入（一次性操作）

首次导入是指**第一次**从MT5获取历史数据并写入数据库的过程。这是一次性操作，之后只需要每日增量更新。

---

#### **Phase 1：3品种×3周期×2年（67K行，15MB）**

##### **详细步骤拆解**

```python
# 伪代码展示完整流程

def first_time_import_phase1():
    """Phase 1 首次导入"""
    
    # 配置
    symbols = ['EURUSD', 'GBPUSD', 'USDJPY']  # 3个品种
    timeframes = ['H1', 'H4', 'D1']            # 3个周期
    bars_per_symbol = 10000                    # 约2年数据
    
    total_bars = 0
    start_time = time.time()
    
    # ========== 步骤1：连接MT5 ========== (5-10秒)
    print("步骤1: 连接MT5...")
    if not mt5_manager.connect(use_investor=True):
        raise RuntimeError("MT5连接失败")
    
    mt5_client = mt5_manager.get_client()
    print(f"   ✅ 已连接MT5 (耗时: 5秒)")
    
    # ========== 步骤2：循环获取数据 ========== (60-180秒)
    print("\n步骤2: 从MT5获取历史数据...")
    
    for symbol in symbols:
        for timeframe in timeframes:
            print(f"   正在获取 {symbol} {timeframe}...")
            
            # 2.1 发送请求到MT5服务器
            bars_data = mt5_client.get_bars(
                symbol=symbol,
                timeframe=timeframe,
                count=bars_per_symbol
            )
            # 耗时分析：
            # - 网络延迟: 5-10秒（取决于MT5服务器速度）
            # - 数据传输: 5-15秒（约22,630根K线）
            # 小计: ~20秒/组合
            
            total_bars += len(bars_data)
            print(f"      ✅ 获取 {len(bars_data)} 根K线 (耗时: 20秒)")
    
    print(f"\n   总计获取 {total_bars} 根K线")
    print(f"   步骤2总耗时: {9 * 20 = 180}秒 (3分钟)")
    
    # ========== 步骤3：写入数据库 ========== (30-60秒)
    print("\n步骤3: 写入PostgreSQL数据库...")
    
    with db.session_scope() as session:
        batch = []
        
        for symbol in symbols:
            for timeframe in timeframes:
                bars_data = get_cached_bars(symbol, timeframe)
                
                # 3.1 构造数据对象
                for bar in bars_data:
                    historical_bar = HistoricalBar(
                        symbol=symbol,
                        timeframe=timeframe,
                        time=bar['time'],
                        open=bar['open'],
                        high=bar['high'],
                        low=bar['low'],
                        close=bar['close'],
                        volume=bar.get('volume', 0)
                    )
                    batch.append(historical_bar)
                    
                    # 3.2 批量插入（每5000条提交一次）
                    if len(batch) >= 5000:
                        session.bulk_save_objects(batch)
                        session.commit()
                        batch = []
                        print(f"      ✅ 已写入 5000 行")
        
        # 3.3 最后一批
        if batch:
            session.bulk_save_objects(batch)
            session.commit()
    
    print(f"   步骤3总耗时: 60秒")
    
    # ========== 步骤4：创建索引 ========== (10-20秒)
    print("\n步骤4: 创建数据库索引...")
    
    # PostgreSQL自动创建以下索引：
    # - 主键索引: id (自动)
    # - 复合索引: (symbol, timeframe, time)
    # - 唯一约束索引: (symbol, timeframe, time)
    
    # 数据量小，索引创建很快
    print(f"   ✅ 索引创建完成 (耗时: 15秒)")
    
    # ========== 完成 ==========
    total_time = time.time() - start_time
    print(f"\n✅ 首次导入完成！")
    print(f"   总行数: 67,890行")
    print(f"   数据量: ~15MB")
    print(f"   总耗时: {total_time:.0f}秒 (约{total_time/60:.1f}分钟)")
```

##### **时间分解表**

| 步骤 | 操作 | 时间 | 占比 | 说明 |
|------|------|------|------|------|
| **1** | 连接MT5 | 5-10秒 | 3% | 一次性连接 |
| **2** | 获取数据（9组） | 60-180秒 | 60% | **最耗时**，网络IO |
| | 单组（EURUSD H1） | ~20秒 | | 22,630根K线 |
| | 9组并行（可优化） | ~30秒 | | 多线程获取 |
| **3** | 写入数据库 | 30-60秒 | 25% | 批量插入优化 |
| | 构造对象 | ~20秒 | | Python处理 |
| | SQL插入 | ~30秒 | | PostgreSQL批量 |
| **4** | 创建索引 | 10-20秒 | 12% | 自动优化 |
| **总计** | | **3-8分钟** | 100% | 正常范围 |

##### **优化措施**

```python
# 优化1：并行获取数据（推荐）
from concurrent.futures import ThreadPoolExecutor

def fetch_parallel():
    """并行获取，速度提升3-5倍"""
    
    tasks = [
        (symbol, tf) 
        for symbol in symbols 
        for tf in timeframes
    ]
    
    with ThreadPoolExecutor(max_workers=4) as executor:
        # 4个线程同时获取
        results = executor.map(fetch_bars, tasks)
    
    # 优化后：180秒 → 45秒

# 优化2：批量插入（已实现）
session.bulk_save_objects(batch)  # 比逐条insert快10-50倍

# 优化3：延迟索引创建
# 1. 先禁用索引
# 2. 导入所有数据
# 3. 最后创建索引
# 优化后：总时间减少20-30%
```

##### **实际体验**

```bash
# 用户视角（命令行输出）

$ python scripts/import_historical_data.py

🚀 开始首次导入历史数据...

步骤1: 连接MT5...
   ✅ 已连接MT5 Investor账户
   耗时: 5秒

步骤2: 从MT5获取历史数据...
   [1/9] EURUSD H1... ✅ 17,520根 (20秒)
   [2/9] EURUSD H4... ✅ 4,380根 (15秒)
   [3/9] EURUSD D1... ✅ 730根 (10秒)
   [4/9] GBPUSD H1... ✅ 17,520根 (20秒)
   [5/9] GBPUSD H4... ✅ 4,380根 (15秒)
   [6/9] GBPUSD D1... ✅ 730根 (10秒)
   [7/9] USDJPY H1... ✅ 17,520根 (20秒)
   [8/9] USDJPY H4... ✅ 4,380根 (15秒)
   [9/9] USDJPY D1... ✅ 730根 (10秒)
   
   总计: 67,890根K线
   耗时: 2分15秒

步骤3: 写入PostgreSQL...
   ✅ 批量写入 67,890 行
   耗时: 45秒

步骤4: 创建索引...
   ✅ 创建复合索引 (symbol, timeframe, time)
   耗时: 15秒

✅ 首次导入完成！
   数据量: 15.2 MB
   总耗时: 4分15秒

📊 数据统计：
   品种: 3个 (EURUSD, GBPUSD, USDJPY)
   周期: 3个 (H1, H4, D1)
   时间跨度: 2024-04-11 → 2022-04-11 (2年)
```

---

#### **Phase 2：10品种×5周期×5年（3.2M行，500MB）**

##### **时间分解表**

| 步骤 | 操作 | 时间（未优化） | 时间（优化后） | 说明 |
|------|------|----------------|----------------|------|
| **1** | 连接MT5 | 10秒 | 10秒 | 一次性 |
| **2** | 获取数据（50组） | 30-60分钟 | 10-15分钟 | 并行8线程 |
| | 单组（EURUSD M15） | ~1-2分钟 | | 175,200根 |
| **3** | 写入数据库 | 10-20分钟 | 5-8分钟 | 批量优化 |
| **4** | 创建索引 | 5-10分钟 | 5-10分钟 | 数据量大 |
| **总计** | | **45-90分钟** | **20-35分钟** | 3倍加速 |

##### **优化方案**

```python
# Phase 2 优化版导入脚本

def import_phase2_optimized():
    """优化版Phase 2导入"""
    
    # 优化1：并行获取（8线程）
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = []
        for symbol in symbols:  # 10个品种
            for tf in timeframes:  # 5个周期
                future = executor.submit(fetch_and_cache, symbol, tf)
                futures.append(future)
        
        # 等待所有完成
        for future in as_completed(futures):
            result = future.result()
            print(f"   ✅ {result['symbol']} {result['timeframe']}")
    
    # 优化2：禁用索引，批量插入
    session.execute("DROP INDEX IF EXISTS idx_symbol_tf_time")
    
    # 批量插入（每10000行提交）
    batch_size = 10000
    for batch in chunked(all_bars, batch_size):
        session.bulk_insert_mappings(HistoricalBar, batch)
        session.commit()
    
    # 优化3：重建索引
    session.execute("CREATE INDEX idx_symbol_tf_time ON historical_bars(symbol, timeframe, time)")
```

---

#### **Phase 3：30品种×7周期×10年（50M行，3-4GB）**

##### **时间分解表**

| 步骤 | 操作 | 时间（未优化） | 时间（优化后） | 说明 |
|------|------|----------------|----------------|------|
| **1** | 连接MT5 | 10秒 | 10秒 | 一次性 |
| **2** | 获取数据（210组） | 4-8小时 | 1-2小时 | 并行16线程 |
| | 单组（EURUSD M5） | ~2-3分钟 | | 1,051,200根 |
| **3** | 写入数据库 | 2-4小时 | 30-60分钟 | 批量+分区 |
| **4** | 创建索引 | 30-60分钟 | 30-60分钟 | 数据量大 |
| **总计** | | **6-12小时** | **2-4小时** | 3-4倍加速 |

**重要**：Phase 3建议**分批后台运行**，不需要一次性完成。

```bash
# 分批策略：每天晚上导入几个品种
Day 1: 导入 EURUSD, GBPUSD, USDJPY (3个) - 1小时
Day 2: 导入 EURJPY, EURGBP, AUDUSD (3个) - 1小时
...
Day 10: 全部完成
```

---

### 2️⃣ 每日更新（自动任务）

每日更新是指**每天自动**从MT5获取最新K线数据，保持数据库最新。这是增量更新，速度很快。

---

#### **Phase 1：3品种×3周期（~15秒）**

##### **详细步骤拆解**

```python
def daily_update_phase1():
    """Phase 1 每日更新"""
    
    symbols = ['EURUSD', 'GBPUSD', 'USDJPY']
    timeframes = ['H1', 'H4', 'D1']
    
    start_time = time.time()
    
    # ========== 步骤1：连接MT5 ========== (5秒)
    mt5_manager.connect(use_investor=True)
    
    # ========== 步骤2：获取最新数据 ========== (5秒)
    for symbol in symbols:
        for timeframe in timeframes:
            # 2.1 查询数据库最新时间
            with db.session_scope() as session:
                latest_time = session.query(func.max(HistoricalBar.time)).filter(
                    HistoricalBar.symbol == symbol,
                    HistoricalBar.timeframe == timeframe
                ).scalar()
            
            # 2.2 计算需要更新的K线数量
            if latest_time:
                hours_since = (datetime.now() - latest_time).total_seconds() / 3600
                bars_needed = int(hours_since) + 10  # 加缓冲
            else:
                bars_needed = 100  # 首次更新
            
            # 2.3 从MT5获取增量数据
            new_bars = mt5_client.get_bars(symbol, timeframe, bars_needed)
            
            # 耗时：~1秒（数据量小）
            
            # 2.4 写入数据库（增量）
            with db.session_scope() as session:
                for bar in new_bars:
                    if bar['time'] > latest_time:
                        historical_bar = HistoricalBar(...)
                        session.merge(historical_bar)  # 存在则更新
                
                session.commit()
            
            # 耗时：~0.5秒
    
    # ========== 完成 ==========
    total_time = time.time() - start_time
    print(f"✅ 每日更新完成 (耗时: {total_time:.1f}秒)")
```

##### **时间分解表**

| 步骤 | 操作 | 时间 | 说明 |
|------|------|------|------|
| **1** | 连接MT5 | 5秒 | 一次性连接 |
| **2** | 查询最新时间（9次） | 2秒 | 数据库查询快（有索引） |
| **3** | 获取增量数据（9组） | 5秒 | 每组约10-30根新K线 |
| **4** | 写入数据库（9组） | 3秒 | 增量写入，数据量小 |
| **总计** | | **~15秒** | 自动任务，凌晨执行 |

##### **每日新增数据量**

```
每天新增K线数：

H1: 24根/天 × 3品种 = 72根
H4: 6根/天 × 3品种 = 18根
D1: 1根/天 × 3品种 = 3根
─────────────────────────────
总计: 93根/天

数据量: 93根 × 80字节 ≈ 7.4 KB/天
一年: 7.4KB × 365 = 2.7 MB/年

结论：数据增长极慢，无压力
```

##### **自动任务配置**

```bash
# crontab 配置（每天凌晨2点）
0 2 * * * cd /path/to/MT4-Factory && /path/to/venv/bin/python scripts/update_daily.py >> logs/daily_update.log 2>&1

# 或使用 systemd timer（推荐）
# 文件：/etc/systemd/system/mt4-daily-update.timer
[Timer]
OnCalendar=daily 02:00
Persistent=true

[Install]
WantedBy=timers.target
```

##### **实际日志输出**

```bash
# logs/daily_update.log

2026-04-12 02:00:05 - 开始每日更新...
2026-04-12 02:00:10 - 连接MT5成功
2026-04-12 02:00:11 - EURUSD H1: 查询最新时间 2026-04-11 23:00
2026-04-12 02:00:12 - EURUSD H1: 获取26根新K线
2026-04-12 02:00:13 - EURUSD H1: 写入完成
2026-04-12 02:00:13 - EURUSD H4: 查询最新时间 2026-04-11 20:00
2026-04-12 02:00:14 - EURUSD H4: 获取7根新K线
2026-04-12 02:00:14 - EURUSD H4: 写入完成
...
2026-04-12 02:00:20 - ✅ 更新完成，新增93根K线
2026-04-12 02:00:20 - 总耗时: 15秒
```

---

#### **Phase 2：10品种×5周期（~40秒）**

##### **时间分解**

| 步骤 | 操作 | 时间 | 说明 |
|------|------|------|------|
| **1** | 连接MT5 | 5秒 | 一次性 |
| **2** | 查询最新时间（50次） | 5秒 | 数据库查询 |
| **3** | 获取增量数据（50组） | 20秒 | 每组约10-50根 |
| **4** | 写入数据库（50组） | 10秒 | 增量写入 |
| **总计** | | **~40秒** | 可接受 |

##### **每日新增数据量**

```
M15: 96根/天 × 10品种 = 960根
M30: 48根/天 × 10品种 = 480根
H1:  24根/天 × 10品种 = 240根
H4:  6根/天 × 10品种 = 60根
D1:  1根/天 × 10品种 = 10根
─────────────────────────────
总计: 1,750根/天

数据量: 1,750根 × 80字节 ≈ 140 KB/天
一年: 140KB × 365 = 51 MB/年
```

---

#### **Phase 3：30品种×7周期（~2.5分钟）**

##### **时间分解**

| 步骤 | 操作 | 时间 | 说明 |
|------|------|------|------|
| **1** | 连接MT5 | 10秒 | 一次性 |
| **2** | 查询最新时间（210次） | 15秒 | 数据库查询 |
| **3** | 获取增量数据（210组） | 80秒 | 每组约10-100根 |
| **4** | 写入数据库（210组） | 45秒 | 增量写入 |
| **总计** | | **~2.5分钟** | 凌晨执行，可接受 |

##### **每日新增数据量**

```
M5:  288根/天 × 30品种 = 8,640根
M15: 96根/天 × 30品种 = 2,880根
M30: 48根/天 × 30品种 = 1,440根
H1:  24根/天 × 30品种 = 720根
H4:  6根/天 × 30品种 = 180根
D1:  1根/天 × 30品种 = 30根
W1:  0.14根/天 × 30品种 = 4根
─────────────────────────────
总计: 13,894根/天

数据量: 13,894根 × 80字节 ≈ 1.1 MB/天
一年: 1.1MB × 365 = 400 MB/年

结论：数据库增长可控（400MB/年）
```

---

### 3️⃣ 单次回测（策略评估）

单次回测是指**运行一个策略**在历史数据上进行完整的回测，包括数据查询、策略执行、指标计算。

---

#### **Phase 1：2年数据，3000根K线（0.3-0.6秒）**

##### **详细步骤拆解**

```python
def single_backtest_phase1(strategy_code: str, symbol='EURUSD', timeframe='H1'):
    """单次回测 Phase 1"""
    
    start_time = time.time()
    
    # ========== 步骤1：查询数据 ========== (30-50ms)
    with db.session_scope() as session:
        bars = session.query(HistoricalBar).filter(
            HistoricalBar.symbol == symbol,
            HistoricalBar.timeframe == timeframe
        ).order_by(
            HistoricalBar.time.desc()
        ).limit(3000).all()
    
    query_time = (time.time() - start_time) * 1000
    print(f"步骤1: 数据库查询 - {query_time:.0f}ms")
    
    # ========== 步骤2：转换DataFrame ========== (20ms)
    df = pd.DataFrame([{
        'time': b.time,
        'open': b.open,
        'high': b.high,
        'low': b.low,
        'close': b.close,
        'volume': b.volume
    } for b in bars])
    df = df.sort_values('time').reset_index(drop=True)
    
    convert_time = (time.time() - start_time - query_time/1000) * 1000
    print(f"步骤2: 转换DataFrame - {convert_time:.0f}ms")
    
    # ========== 步骤3：运行回测引擎 ========== (200-500ms)
    evaluator = HistoricalDataEvaluator()
    
    # 3.1 加载策略代码
    strategy = evaluator._load_strategy(strategy_code)
    # 耗时: ~5ms
    
    # 3.2 遍历K线，执行策略
    for idx in range(50, len(df)):
        window_data = df.iloc[:idx+1]
        signal = strategy.on_tick(window_data)
        # 处理开仓/平仓逻辑
        # ...
    
    # 耗时: ~200-500ms（取决于策略复杂度）
    # - 简单MA策略: 200ms
    # - 复杂策略（多指标）: 500ms
    
    backtest_time = (time.time() - start_time - query_time/1000 - convert_time/1000) * 1000
    print(f"步骤3: 运行回测 - {backtest_time:.0f}ms")
    
    # ========== 步骤4：计算性能指标 ========== (50ms)
    metrics = evaluator.calculate_metrics()
    # 计算：Sharpe、回撤、胜率、盈亏比...
    # 耗时: ~50ms
    
    metrics_time = (time.time() - start_time - query_time/1000 - convert_time/1000 - backtest_time/1000) * 1000
    print(f"步骤4: 计算指标 - {metrics_time:.0f}ms")
    
    # ========== 完成 ==========
    total_time = (time.time() - start_time) * 1000
    print(f"\n单次回测完成: {total_time:.0f}ms ({total_time/1000:.2f}秒)")
    
    return metrics
```

##### **时间分解表**

| 步骤 | 操作 | 时间 | 占比 | 说明 |
|------|------|------|------|------|
| **1** | 数据库查询 | 30-50ms | 10% | **有索引很快** |
| | SQL查询执行 | ~20ms | | PostgreSQL优化 |
| | 网络传输（本地） | ~10ms | | 本地连接快 |
| **2** | 转换DataFrame | 20ms | 5% | Pandas处理 |
| **3** | 运行回测引擎 | 200-500ms | 70% | **最耗时** |
| | 加载策略代码 | ~5ms | | 动态exec() |
| | 遍历K线（2950根） | ~200-500ms | | 策略逻辑执行 |
| | 每根K线 | ~0.07-0.17ms | | Python计算 |
| **4** | 计算性能指标 | 50ms | 15% | NumPy计算 |
| | 基础指标 | ~20ms | | 简单统计 |
| | 风险指标 | ~20ms | | 回撤/Sharpe |
| | 推荐系统 | ~10ms | | 评分逻辑 |
| **总计** | | **300-600ms** | 100% | 0.3-0.6秒 |

##### **性能影响因素**

```python
# 影响因素1：数据库索引（关键！）
# 有索引: 30-50ms
# 无索引: 3000-5000ms (慢100倍！)

CREATE INDEX idx_symbol_tf_time ON historical_bars(symbol, timeframe, time);

# 影响因素2：策略复杂度
# 简单MA交叉: 200ms
# RSI + MACD + 布林带: 500ms

# 影响因素3：K线数量
# 1000根: 100ms
# 3000根: 300ms
# 10000根: 1000ms

# 影响因素4：Python版本
# Python 3.9: 500ms
# Python 3.11: 400ms (性能优化)
# Python 3.13: 350ms (更快！)
```

##### **实际输出示例**

```bash
$ python test_backtest.py

单次回测测试 - Phase 1
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

步骤1: 数据库查询
   SQL: SELECT * FROM historical_bars 
        WHERE symbol='EURUSD' AND timeframe='H1'
        ORDER BY time DESC LIMIT 3000
   
   ✅ 查询完成: 3000根K线
   耗时: 42ms
   
   索引使用: idx_symbol_tf_time ✅
   扫描行数: 3000/67890 (4.4%)

步骤2: 转换DataFrame
   ✅ 转换完成: 3000行 × 6列
   耗时: 18ms
   内存: 140KB

步骤3: 运行回测引擎
   策略: MA交叉 (快线5/慢线28)
   
   [进度] 遍历K线: 2950/2950 ━━━━━━━━━━━━━━━━ 100%
   
   ✅ 回测完成
   耗时: 285ms
   
   交易次数: 24笔
   胜率: 58.3%
   盈亏比: 1.85

步骤4: 计算性能指标
   ✅ 指标计算完成
   耗时: 48ms
   
   指标项: 35个
   综合评分: 68.5分

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ 单次回测完成
   总耗时: 393ms (0.39秒)
   
   分解:
   - 数据查询: 42ms (10.7%)
   - 数据处理: 18ms (4.6%)
   - 回测执行: 285ms (72.5%)
   - 指标计算: 48ms (12.2%)
```

---

#### **Phase 2：5年数据（0.66秒）**

##### **时间分解**

| 步骤 | 时间 | 说明 |
|------|------|------|
| **1** | 60-80ms | 数据库查询（3.2M行，有索引） |
| **2** | 30ms | 转换DataFrame |
| **3** | 500ms | 运行回测（3000根） |
| **4** | 60ms | 计算指标 |
| **总计** | **~660ms** | 0.66秒 |

---

#### **Phase 3：10年数据（0.8秒，需优化）**

##### **时间分解（未优化）**

| 步骤 | 时间（未优化） | 时间（优化后） | 说明 |
|------|---------------|----------------|------|
| **1** | 5000-8000ms | 80-100ms | **必须优化**：分区/TimescaleDB |
| **2** | 40ms | 40ms | 数据处理 |
| **3** | 600ms | 600ms | 回测执行 |
| **4** | 60ms | 60ms | 指标计算 |
| **总计** | **5.7-8.7秒** | **~800ms** | 优化至关重要！ |

##### **优化方案**

```sql
-- 优化1：分区表（按年分区）
CREATE TABLE historical_bars_2024 PARTITION OF historical_bars
FOR VALUES FROM ('2024-01-01') TO ('2025-01-01');

CREATE TABLE historical_bars_2023 PARTITION OF historical_bars
FOR VALUES FROM ('2023-01-01') TO ('2024-01-01');
-- ...

-- 查询最近3000根只扫描最近表
-- 查询时间: 8000ms → 100ms (80倍加速！)

-- 优化2：TimescaleDB（自动分区+压缩）
SELECT create_hypertable('historical_bars', 'time');

-- 自动优化查询
-- 查询时间: 8000ms → 80ms
```

---

### 4️⃣ 100策略批量（AI生成场景）

批量回测是指**同时生成和回测100个策略**，模拟AI批量生成策略的场景。

---

#### **Phase 1：100策略（1分钟）**

##### **详细流程**

```python
def batch_generate_100_strategies():
    """批量生成100个策略"""
    
    start_time = time.time()
    
    strategies = []
    
    for i in range(100):
        # ========== 生成策略代码 ========== (~0.1秒)
        strategy_code = generate_strategy_code()
        # AI生成（未来）：调用OpenAI API，~1-2秒
        # 当前（随机参数）：~0.1秒
        
        # ========== 回测策略 ========== (~0.6秒)
        # 步骤1: 数据库查询 (40ms)
        # 步骤2: 转换DataFrame (20ms)
        # 步骤3: 运行回测 (300ms)
        # 步骤4: 计算指标 (50ms)
        metrics = backtest(strategy_code)
        
        # ========== 保存策略 ========== (~0.05秒)
        strategy = Strategy(
            id=generate_id(),
            code=strategy_code,
            performance=metrics
        )
        session.add(strategy)
        
        strategies.append(strategy)
        
        if (i+1) % 10 == 0:
            print(f"   [{i+1}/100] 已完成")
    
    session.commit()
    
    total_time = time.time() - start_time
    print(f"\n✅ 批量生成完成")
    print(f"   策略数: 100个")
    print(f"   总耗时: {total_time:.1f}秒 ({total_time/60:.1f}分钟)")
```

##### **时间分解**

| 步骤 | 单个耗时 | 100个耗时 | 占比 |
|------|---------|-----------|------|
| **生成代码** | 0.1秒 | 10秒 | 17% |
| **回测** | 0.6秒 | 60秒 | 83% |
| 数据查询 | 0.04秒 | 4秒 | |
| 回测执行 | 0.5秒 | 50秒 | |
| 指标计算 | 0.05秒 | 5秒 | |
| **保存数据库** | 0.05秒 | 5秒 | 7% |
| **总计** | 0.75秒 | **~75秒** | 100% |

**实际耗时约1分钟（考虑数据库提交等）**

##### **并行优化**

```python
# 并行回测（4核）
from multiprocessing import Pool

def parallel_batch_backtest(strategies, workers=4):
    """并行回测，提速4倍"""
    
    with Pool(processes=workers) as pool:
        results = pool.map(backtest, strategies)
    
    return results

# 优化后：
# 100个策略: 60秒 → 15秒 (4倍加速)
```

---

#### **Phase 2：100策略（1.1分钟）**

| 步骤 | 单个耗时 | 100个耗时 |
|------|---------|-----------|
| **生成代码** | 0.1秒 | 10秒 |
| **回测** | 0.66秒 | 66秒 |
| **保存** | 0.05秒 | 5秒 |
| **总计** | 0.81秒 | **~81秒** |

**实际耗时约1.1分钟**

##### **并行优化后**

- 4核: 81秒 → 20秒
- 8核: 81秒 → 10秒

---

#### **Phase 3：100策略（80秒，并行10秒）**

##### **串行执行**

| 步骤 | 单个耗时 | 100个耗时 |
|------|---------|-----------|
| **生成代码** | 0.1秒 | 10秒 |
| **回测** | 0.8秒 | 80秒 |
| **保存** | 0.05秒 | 5秒 |
| **总计** | 0.95秒 | **~95秒** |

##### **并行执行（8核）**

```
100个策略 ÷ 8核 = 12.5组
每组耗时: 0.8秒 × 12.5 = 10秒

总耗时: ~10-15秒 ✅
```

---

## 🎯 总结对比表

### **首次导入对比**

| 阶段 | 数据量 | 未优化 | 优化后 | 是否必需优化 |
|------|--------|--------|--------|-------------|
| **Phase 1** | 15MB | 3-8分钟 | 3-5分钟 | ❌ 不必需 |
| **Phase 2** | 500MB | 45-90分钟 | 20-30分钟 | ✅ 推荐 |
| **Phase 3** | 3-4GB | 6-12小时 | 2-4小时 | ✅ 必需 |

### **每日更新对比**

| 阶段 | 新增数据 | 耗时 | 自动化 |
|------|---------|------|--------|
| **Phase 1** | 93根/天 (7KB) | 15秒 | ✅ cron |
| **Phase 2** | 1,750根/天 (140KB) | 40秒 | ✅ cron |
| **Phase 3** | 13,894根/天 (1.1MB) | 2.5分钟 | ✅ cron |

### **单次回测对比**

| 阶段 | 数据量 | 未优化 | 优化后 | 瓶颈 |
|------|--------|--------|--------|------|
| **Phase 1** | 67K行 | 0.3-0.6秒 | 0.3-0.6秒 | 无 |
| **Phase 2** | 3.2M行 | 0.66秒 | 0.66秒 | 无 |
| **Phase 3** | 50M行 | 5.7-8.7秒 | 0.8秒 | **数据库查询** |

### **100策略批量对比**

| 阶段 | 串行 | 并行(4核) | 并行(8核) |
|------|------|-----------|-----------|
| **Phase 1** | 75秒 | 19秒 | 10秒 |
| **Phase 2** | 81秒 | 20秒 | 10秒 |
| **Phase 3** | 95秒 | 24秒 | 12秒 |

---

## 💡 关键结论

1. **Phase 1-2 无需特别优化**，性能已经很好
2. **Phase 3 必须优化数据库查询**（分区/TimescaleDB）
3. **并行回测可选**，但在AI批量生成时很有价值
4. **每日更新成本极低**，完全自动化
5. **首次导入是一次性成本**，可分批后台运行