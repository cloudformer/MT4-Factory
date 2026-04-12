# 策略验证系统路线图

## 🎯 确定的目标

### 1. 未来一定接入AI批量生成策略

```
当前状态：
  └── 硬编码策略模板（MA交叉，随机参数）

未来愿景：
  └── AI策略生成引擎
      ├── OpenAI/Claude API
      ├── 输入：市场描述、风险偏好、交易理念
      ├── 输出：完整策略代码（Python/MQL5）
      └── 批量生成：每天生成10-100个候选策略
```

**这意味着：验证系统必须自动化、可扩展、高质量。**

---

## 📊 当前模拟数据评估系统状态

### ✅ 已完成且完善

**评估能力分析**：

1. **数据生成**（SyntheticDataEvaluator）
   ```python
   ✅ 随机游走 + 市场制度切换
   ✅ 震荡/趋势交替模拟
   ✅ 真实波动特征模拟
   ```

2. **回测引擎**（BaseEvaluator）
   ```python
   ✅ 动态加载策略代码
   ✅ 逐K线执行
   ✅ 完整持仓管理
   ✅ 权益曲线追踪
   ```

3. **评估指标**（极其全面！）
   ```python
   ✅ 基础性能：收益率、交易数、最终余额
   ✅ 收益指标：Sharpe、Sortino、Calmar、盈亏比、胜率
   ✅ 风险指标：最大回撤、平均回撤、波动率、恢复因子
   ✅ 交易特征：交易频率、平均持仓时间、连续盈亏
   ✅ 稳定性：收益稳定性评分、一致性评分
   ✅ 风险分类：5种风险类型、风险等级评分
   ✅ 市场适应性：滑点敏感度、市场制度识别
   ✅ 策略适用性：投资者类型、推荐场景、账户要求
   ✅ 推荐系统：综合评分、一句话总结、emoji分级
   ```

### 🎯 系统完善度评估

| 维度 | 状态 | 评分 |
|------|------|------|
| **数据生成质量** | 已优化（制度切换） | ⭐⭐⭐⭐ |
| **回测引擎** | 完整实现 | ⭐⭐⭐⭐⭐ |
| **指标计算** | 极其全面 | ⭐⭐⭐⭐⭐ |
| **推荐系统** | 完整且人性化 | ⭐⭐⭐⭐⭐ |
| **整体成熟度** | 生产就绪 | ⭐⭐⭐⭐⭐ |

**结论：模拟数据评估系统已非常完善，可以进入历史数据阶段。** ✅

---

## 🗄️ 历史数据回测方案

### 数据规模评估

#### **场景1：保守起步（推荐Phase 1）**

```yaml
配置：
  品种：3个主流对（EURUSD, GBPUSD, USDJPY）
  周期：3个（H1, H4, D1）
  历史：2年
  
计算：
  H1: 24根/天 × 365天 × 2年 = 17,520根/品种
  H4: 6根/天 × 365天 × 2年 = 4,380根/品种
  D1: 1根/天 × 365天 × 2年 = 730根/品种
  
  小计: 22,630根/品种 × 3品种 = 67,890根K线
  
数据量：
  原始数据: 67,890根 × 80字节 ≈ 5.4 MB
  + 索引: ≈ 10-15 MB
  
存储方案: ✅ PostgreSQL（主数据库）
```

#### **场景2：中等扩展（Phase 2）**

```yaml
配置：
  品种：10个货币对
  周期：5个（M15, M30, H1, H4, D1）
  历史：5年
  
计算：
  M15: 96根/天
  M30: 48根/天
  H1: 24根/天
  H4: 6根/天
  D1: 1根/天
  ────────────────
  总计: 175根/天 × 365天 × 5年 = 319,375根/品种
  319,375根 × 10品种 = 3,193,750根
  
数据量：
  原始数据: 3.2M根 × 80字节 ≈ 256 MB
  + 索引: ≈ 400-500 MB
  
存储方案: ✅ PostgreSQL（主数据库）+ 分区表优化
```

#### **场景3：大规模（未来）**

```yaml
配置：
  品种：30个货币对 + 黄金、原油、指数
  周期：7个（M5, M15, M30, H1, H4, D1, W1）
  历史：10年
  
数据量: 约 2-3 GB
  
存储方案: 
  方案A: ✅ TimescaleDB（时间序列优化的PostgreSQL）
  方案B: PostgreSQL + 分区 + 冷热数据分离
  方案C: S3归档 + PostgreSQL缓存（最近1年）
```

---

### 存储方案对比与选择

#### **方案对比**

| 方案 | 适用规模 | 优点 | 缺点 | 成本 | 推荐 |
|------|---------|------|------|------|------|
| **PostgreSQL（主库）** | <500MB | • 无需额外组件<br>• 事务一致性<br>• 简单运维 | • 大规模时慢 | 💰 | ⭐⭐⭐⭐⭐ Phase 1-2 |
| **TimescaleDB** | 500MB-10GB | • 时间序列优化<br>• 自动分区<br>• 压缩高效 | • 需额外安装 | 💰💰 | ⭐⭐⭐⭐ Phase 3 |
| **S3 + 缓存** | >10GB | • 无限扩展<br>• 低成本存储<br>• 可分离冷热 | • 访问延迟<br>• 架构复杂 | 💰 | ⭐⭐⭐ 大规模场景 |
| **InfluxDB** | 不限 | • 专业时序库<br>• 高性能查询 | • 独立维护<br>• 数据隔离 | 💰💰💰 | ⭐⭐ 过度设计 |

#### **✅ 推荐方案：渐进式架构**

```
┌─────────────────────────────────────────────────────────┐
│              历史数据服务架构（渐进式）                   │
└─────────────────────────────────────────────────────────┘

Phase 1-2（现在-6个月内）：PostgreSQL主库
  └── historical_bars 表
      ├── 索引：(symbol, timeframe, time)
      ├── 数据量：<500MB
      └── 查询速度：<100ms

Phase 3（6个月-2年）：PostgreSQL + 分区
  └── historical_bars_partitioned
      ├── 按年分区：_2024, _2023, _2022...
      ├── 自动分区管理
      ├── 数据量：500MB-3GB
      └── 查询速度：<200ms

Phase 4（2年后，如需要）：混合架构
  ├── PostgreSQL（最近1年热数据）
  ├── S3（2年前冷数据）
  └── 数据生命周期管理
```

---

### 数据服务设计

#### **是否需要独立服务？**

**结论：NO（Phase 1-2），YES（Phase 3+）**

```
Phase 1-2（<500MB）：
  ✅ 使用主数据库
  ✅ 共享连接池
  ✅ 简单查询接口
  ❌ 不需要独立服务（过度设计）

Phase 3+（>500MB）：
  ✅ 独立 Historical Data Service
  ✅ 专用缓存层（Redis）
  ✅ 数据预加载
  ✅ 批量查询优化
```

#### **Phase 1-2 架构（推荐立即实施）**

```python
# 在主数据库中添加表
# src/common/models/historical_bar.py

class HistoricalBar(Base):
    """历史K线数据"""
    __tablename__ = "historical_bars"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    symbol = Column(String(10), nullable=False, index=True)
    timeframe = Column(String(3), nullable=False, index=True)  # H1, H4, D1
    time = Column(DateTime, nullable=False, index=True)
    
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Float, default=0)
    
    created_at = Column(DateTime, default=datetime.now)
    
    __table_args__ = (
        # 复合索引（查询优化）
        Index('idx_symbol_tf_time', 'symbol', 'timeframe', 'time'),
        
        # 唯一约束（防止重复）
        UniqueConstraint('symbol', 'timeframe', 'time', name='uq_bar'),
    )

# 数据导入脚本
# scripts/import_historical_data.py

def import_from_mt5(symbol: str, timeframe: str, bars: int = 10000):
    """从MT5导入历史数据"""
    if not mt5_manager.connect(use_investor=True):
        raise RuntimeError("MT5连接失败")
    
    mt5_client = mt5_manager.get_client()
    bars_data = mt5_client.get_bars(symbol, timeframe, bars)
    
    with db.session_scope() as session:
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
            session.merge(historical_bar)  # 存在则更新
        
        session.commit()
    
    print(f"✅ 导入 {symbol} {timeframe} {len(bars_data)} 根K线")

# 修改 HistoricalDataEvaluator
# src/services/strategy/evaluator/historical_evaluator.py

def _fetch_historical_data(self, symbol, timeframe, bars, 
                           start_date=None, end_date=None):
    """从数据库获取历史数据"""
    with db.session_scope() as session:
        query = session.query(HistoricalBar).filter(
            HistoricalBar.symbol == symbol,
            HistoricalBar.timeframe == timeframe
        )
        
        if start_date:
            query = query.filter(HistoricalBar.time >= start_date)
        if end_date:
            query = query.filter(HistoricalBar.time <= end_date)
        
        results = query.order_by(HistoricalBar.time.desc()).limit(bars).all()
        
        if not results:
            # 回退：从MT5获取（首次使用）
            print("   ⚠️  数据库无数据，从MT5获取...")
            self._import_and_retry(symbol, timeframe, bars)
            return self._fetch_historical_data(symbol, timeframe, bars)
        
        # 转换为DataFrame
        df = pd.DataFrame([{
            'time': r.time,
            'open': r.open,
            'high': r.high,
            'low': r.low,
            'close': r.close,
            'volume': r.volume
        } for r in results])
        
        return df.sort_values('time').reset_index(drop=True)
```

#### **数据更新策略**

```python
# scripts/update_historical_data_daily.py

def update_daily():
    """每天自动更新最新数据"""
    symbols = ['EURUSD', 'GBPUSD', 'USDJPY']
    timeframes = ['H1', 'H4', 'D1']
    
    for symbol in symbols:
        for tf in timeframes:
            # 获取数据库最新时间
            with db.session_scope() as session:
                latest = session.query(func.max(HistoricalBar.time)).filter(
                    HistoricalBar.symbol == symbol,
                    HistoricalBar.timeframe == tf
                ).scalar()
                
                if latest:
                    # 计算需要更新的K线数量
                    hours_since = (datetime.now() - latest).total_seconds() / 3600
                    bars_needed = int(hours_since) + 100  # 加缓冲
                else:
                    bars_needed = 10000  # 首次导入
                
                # 从MT5获取更新
                import_from_mt5(symbol, tf, bars_needed)
    
    print("✅ 每日更新完成")

# crontab 配置（每天凌晨2点）
# 0 2 * * * cd /path/to/MT4-Factory && python scripts/update_historical_data_daily.py
```

---

## 🏭 Strategy Validator服务架构

### 定位：策略工厂的QA系统

```
┌─────────────────────────────────────────────────────────┐
│           Strategy Factory QA Architecture              │
└─────────────────────────────────────────────────────────┘

策略生命周期验证：

1️⃣ 初筛（CANDIDATE生成时）
   ├── 评估器：SyntheticDataEvaluator
   ├── 时间：<1分钟
   ├── 目的：快速淘汰明显不行的策略
   └── 通过率：60-70%

2️⃣ 精筛（CANDIDATE激活前）
   ├── 评估器：HistoricalDataEvaluator
   ├── 数据：2年真实历史数据
   ├── 时间：<1分钟
   ├── 目的：验证真实市场表现
   └── 通过率：30-40%

3️⃣ 实战验证（ACTIVE状态）⭐ Validator Service
   ├── 环境：Demo账户 + 实时行情
   ├── 资金：$100小金额
   ├── 时间：持续7x24运行
   ├── 目的：最终质量验证
   └── 通过率：10-20% → 真正优质策略
```

### Validator Service详细架构

```
┌─────────────────────────────────────────────────────────────┐
│              Live Validator Service（独立服务）             │
│                    策略工厂QA系统核心                        │
└─────────────────────────────────────────────────────────────┘

服务组件：

src/services/validator/
├── __init__.py
├── main.py                     # 服务启动入口
├── core/
│   ├── validator.py            # 核心验证器
│   ├── strategy_runner.py      # 策略运行器
│   ├── performance_tracker.py  # 性能追踪器
│   └── health_checker.py       # 健康检查
├── monitors/
│   ├── risk_monitor.py         # 风险监控
│   ├── drawdown_monitor.py     # 回撤监控
│   └── alert_manager.py        # 告警管理
├── api/
│   ├── app.py                  # 监控API
│   └── routes/
│       ├── status.py           # 状态查询
│       ├── strategies.py       # 策略管理
│       └── reports.py          # 报告生成
└── config/
    └── validator_config.yaml   # 配置文件
```

### 核心流程

```python
# src/services/validator/core/validator.py

class LiveValidator:
    """实时验证器 - 策略工厂QA核心"""
    
    def __init__(self):
        self.mt5_manager = mt5_manager
        self.db = db
        
        # QA配置
        self.qa_config = {
            'initial_balance': 100.0,       # Demo账户$100
            'max_active_strategies': 10,     # 最多同时验证10个
            'evaluation_period_hours': 24,   # 24小时评估周期
            
            # 降级阈值（严格的QA标准）
            'thresholds': {
                'max_drawdown': 0.20,        # 最大回撤20%
                'min_sharpe': 0.5,           # 最低Sharpe 0.5
                'stop_loss': 0.30,           # 亏损30%立即停止
                'min_trades': 3,             # 最少3笔交易才评估
                'max_consecutive_losses': 5  # 最多连续亏损5次
            },
            
            # 晋升条件（严格筛选优质策略）
            'promotion': {
                'min_days': 7,               # 最少运行7天
                'min_sharpe': 1.0,           # Sharpe > 1.0
                'max_drawdown': 0.15,        # 回撤 < 15%
                'min_profit': 0.05,          # 盈利 > 5%
                'min_trades': 10             # 最少10笔交易
            }
        }
        
        # 运行中的策略
        self.running_strategies: Dict[str, StrategyRunner] = {}
    
    async def start(self):
        """启动QA验证服务"""
        print("🏭 启动策略工厂QA服务...")
        
        # 1. 连接MT5
        if not self.mt5_manager.connect(use_investor=True):
            raise RuntimeError("MT5连接失败")
        
        # 2. 加载ACTIVE策略
        await self.load_active_strategies()
        
        # 3. 启动验证循环
        await self.run_qa_loop()
    
    async def run_qa_loop(self):
        """QA验证主循环"""
        print("🔄 QA验证循环运行中...")
        
        tick_count = 0
        
        while True:
            try:
                # 获取最新Tick
                tick = await self._get_latest_tick()
                tick_count += 1
                
                # 对每个策略运行验证
                for strategy_id, runner in self.running_strategies.items():
                    await self._qa_validate_strategy(runner, tick)
                
                # 每小时：性能评估
                if tick_count % 3600 == 0:  # 假设1秒1个tick
                    await self._hourly_qa_check()
                
                # 每天：生成QA报告
                if tick_count % (3600 * 24) == 0:
                    await self._daily_qa_report()
                
                await asyncio.sleep(1)
                
            except KeyboardInterrupt:
                print("\n⏹️  停止QA服务")
                break
            except Exception as e:
                print(f"❌ QA循环错误: {e}")
                await asyncio.sleep(5)
    
    async def _hourly_qa_check(self):
        """每小时QA检查"""
        print("\n⏰ [QA] 每小时质量检查...")
        
        for strategy_id, runner in list(self.running_strategies.items()):
            metrics = runner.calculate_performance()
            
            # QA判断1: 是否需要降级
            if self._should_downgrade(metrics):
                await self._downgrade_strategy(strategy_id, metrics, 
                                               reason="qa_quality_check_failed")
            
            # QA判断2: 是否达到晋升标准
            elif self._should_promote(runner, metrics):
                await self._promote_strategy(strategy_id, metrics)
            
            # QA判断3: 风险告警
            elif self._has_risk_warning(metrics):
                await self._send_risk_alert(strategy_id, metrics)
    
    def _should_downgrade(self, metrics: dict) -> bool:
        """QA降级判断（严格标准）"""
        thresholds = self.qa_config['thresholds']
        
        # 1. Sharpe过低
        if metrics['sharpe_ratio'] < thresholds['min_sharpe']:
            return True
        
        # 2. 回撤过大
        if metrics['max_drawdown'] > thresholds['max_drawdown']:
            return True
        
        # 3. 连续亏损过多
        if metrics.get('consecutive_losses', 0) >= thresholds['max_consecutive_losses']:
            return True
        
        # 4. 交易数太少（24小时内）
        if metrics['total_trades'] < thresholds['min_trades']:
            # 交易太少，可能策略失效
            return True
        
        return False
    
    def _should_promote(self, runner: StrategyRunner, metrics: dict) -> bool:
        """QA晋升判断（严格标准）"""
        promo = self.qa_config['promotion']
        
        # 1. 运行天数足够
        run_days = (datetime.now() - runner.start_time).days
        if run_days < promo['min_days']:
            return False
        
        # 2. Sharpe优异
        if metrics['sharpe_ratio'] < promo['min_sharpe']:
            return False
        
        # 3. 回撤控制良好
        if metrics['max_drawdown'] > promo['max_drawdown']:
            return False
        
        # 4. 盈利达标
        profit_pct = (runner.current_balance - runner.initial_balance) / runner.initial_balance
        if profit_pct < promo['min_profit']:
            return False
        
        # 5. 交易数量足够
        if metrics['total_trades'] < promo['min_trades']:
            return False
        
        return True
    
    async def _promote_strategy(self, strategy_id: str, metrics: dict):
        """晋升策略（标记为"已验证"）"""
        print(f"🌟 [QA] 策略 {strategy_id} 通过QA验证！")
        
        with self.db.session_scope() as session:
            strategy = session.query(Strategy).get(strategy_id)
            
            # 添加QA验证标记
            strategy.metadata = strategy.metadata or {}
            strategy.metadata['qa_validated'] = True
            strategy.metadata['qa_validation_date'] = datetime.now().isoformat()
            strategy.metadata['qa_metrics'] = metrics
            strategy.metadata['qa_grade'] = 'A'  # A/B/C等级
            
            session.commit()
        
        print(f"   ✅ QA等级: A")
        print(f"   📊 Sharpe: {metrics['sharpe_ratio']:.2f}")
        print(f"   📉 回撤: {metrics['max_drawdown']*100:.1f}%")
        print(f"   💰 盈利: {metrics['total_profit']:.2f}")
    
    async def _daily_qa_report(self):
        """每日QA报告"""
        print("\n📊 [QA] 生成每日质量报告...")
        
        report = {
            'date': datetime.now().date().isoformat(),
            'strategies_tested': len(self.running_strategies),
            'strategies_passed': 0,
            'strategies_failed': 0,
            'average_sharpe': 0,
            'average_drawdown': 0,
            'total_profit': 0
        }
        
        all_metrics = []
        
        for runner in self.running_strategies.values():
            metrics = runner.calculate_performance()
            all_metrics.append(metrics)
            
            if self._should_promote(runner, metrics):
                report['strategies_passed'] += 1
            elif self._should_downgrade(metrics):
                report['strategies_failed'] += 1
        
        if all_metrics:
            report['average_sharpe'] = np.mean([m['sharpe_ratio'] for m in all_metrics])
            report['average_drawdown'] = np.mean([m['max_drawdown'] for m in all_metrics])
            report['total_profit'] = sum([m['total_profit'] for m in all_metrics])
        
        # 保存报告
        with self.db.session_scope() as session:
            qa_report = QAReport(
                date=report['date'],
                data=report
            )
            session.add(qa_report)
            session.commit()
        
        print(f"   ✅ 测试中: {report['strategies_tested']}")
        print(f"   🌟 通过: {report['strategies_passed']}")
        print(f"   ❌ 失败: {report['strategies_failed']}")
```

### 部署架构

```
┌─────────────────────────────────────────────────────────────┐
│                    Validator 部署方案                        │
└─────────────────────────────────────────────────────────────┘

方案A：独立Windows VPS（推荐）
  ├── Windows Server 2022
  ├── MT5 Terminal（Demo账户）
  ├── Python 3.11
  ├── Validator Service（后台运行）
  └── 监控API（Port 9000）

方案B：Docker容器（开发环境）
  ├── docker-compose.yml
  │   ├── validator-service
  │   └── mt5-mock（macOS模拟）
  └── 特点：适合本地测试

配置：
  - CPU: 2核
  - 内存: 4GB
  - 存储: 20GB
  - 网络: 稳定连接MT5服务器
  - 成本: $10-20/月
```

---

## 📅 实施路线图

### **Phase 1：历史数据回测（1-2周）** ← 立即开始

```
Week 1：
  ✅ Day 1-2: 创建 historical_bars 表
  ✅ Day 3-4: 实现数据导入脚本（从MT5）
  ✅ Day 5: 导入基础数据（EURUSD/GBPUSD/USDJPY，H1/H4/D1，2年）

Week 2：
  ✅ Day 6-7: 修改 HistoricalDataEvaluator
  ✅ Day 8-9: 更新配置，启用历史数据评估
  ✅ Day 10: 测试验证（生成策略，对比模拟vs历史）
```

**交付物**：
- ✅ 历史数据导入完成（~70K根K线，~15MB）
- ✅ 策略生成自动使用历史数据回测
- ✅ 每日自动更新数据脚本

### **Phase 2：Validator服务基础（2-3周）**

```
Week 3-4：
  ✅ 搭建Validator服务框架
  ✅ 实现 LiveValidator 核心逻辑
  ✅ 实现 StrategyRunner 运行器
  ✅ 添加性能追踪和监控

Week 5：
  ✅ 部署到Windows VPS
  ✅ 接入MT5 Demo账户
  ✅ 测试运行（1-2个ACTIVE策略）
```

**交付物**：
- ✅ Validator服务上线运行
- ✅ 监控API可访问
- ✅ 自动降级功能工作

### **Phase 3：Dashboard集成（1周）**

```
Week 6：
  ✅ Dashboard显示Validator状态
  ✅ 显示ACTIVE策略实时性能
  ✅ QA报告展示
  ✅ 告警通知
```

**交付物**：
- ✅ 完整的策略工厂QA系统上线

### **Phase 4：AI策略生成接入（未来）**

```
准备工作：
  ✅ Phase 1-3完成
  ✅ 验证系统稳定运行3个月
  ✅ 收集至少100个策略的评估数据

接入AI：
  ✅ 接入OpenAI/Claude API
  ✅ 设计策略生成Prompt
  ✅ 批量生成 → 自动评估 → 优胜劣汰
```

---

## 🎯 总结

### 三个确定的目标与实施路径

| 目标 | 当前状态 | 下一步 | 时间线 |
|------|---------|--------|--------|
| **1. 准备AI批量生成** | 模拟评估完善 ✅ | 历史数据验证 | 1-2周 |
| **2. 历史数据回测** | 架构设计完成 | 立即实施 Phase 1 | 1-2周 |
| **3. Validator QA服务** | 详细设计完成 | Phase 2-3 实施 | 3-4周 |

### 存储方案决策

- ✅ **Phase 1-2（现在-6个月）**：PostgreSQL主库（<500MB）
- ⏳ **Phase 3（6个月-2年）**：PostgreSQL + 分区（500MB-3GB）
- 🔮 **Phase 4（2年后）**：混合架构（热数据+S3冷存储）

### 关键里程碑

```
Week 2:  ✅ 历史数据回测上线
Week 5:  ✅ Validator服务上线
Week 6:  ✅ 完整QA系统上线
Month 3: ✅ 系统稳定运行，准备接入AI
```

**这是一个完整的策略工厂QA流水线：AI生成 → 模拟评估 → 历史验证 → 实战测试 → 优质策略产出。** 🏭⭐
