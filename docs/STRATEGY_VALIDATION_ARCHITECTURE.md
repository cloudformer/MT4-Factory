# 策略验证架构设计

## 📋 当前状态分析

### 1. 策略代码是否就这么简单？

**是的，目前策略代码确实很简单：**

```python
class Strategy_STR_e146a4fd:
    '''MA 交叉策略 - 快线5/慢线28'''

    def __init__(self):
        self.fast_period = 5
        self.slow_period = 28

    def on_tick(self, data):
        # 计算均线
        fast_ma = data['close'].rolling(self.fast_period).mean()
        slow_ma = data['close'].rolling(self.slow_period).mean()

        # 交叉判断
        if fast_ma.iloc[-1] > slow_ma.iloc[-1] and fast_ma.iloc[-2] <= slow_ma.iloc[-2]:
            return 'buy'
        elif fast_ma.iloc[-1] < slow_ma.iloc[-1] and fast_ma.iloc[-2] >= slow_ma.iloc[-2]:
            return 'sell'

        return None
```

**这是设计好的：**
- ✅ **简单 = 可验证性强**：逻辑清晰，容易回测
- ✅ **快速迭代**：生成 → 验证 → 淘汰 循环快
- ✅ **策略工厂模式**：批量生成、批量验证、优胜劣汰
- ✅ **未来扩展**：可以加入AI生成更复杂策略

**代码位置**：
- 生成器：`src/services/strategy/service/generator.py:121-159`
- 未来会接入 AI（OpenAI/Claude）生成更多样化的策略

---

## 🎯 方案2：历史数据回测（替代模拟数据）

### 当前问题

```
现状：使用合成数据（SyntheticDataEvaluator）
  ↓
  生成模拟的正弦波 + 趋势 + 噪声
  ↓
  回测结果不够真实（缺乏市场特征）
```

### 历史数据回测方案

#### **架构设计**

```
┌─────────────────────────────────────────────────────────────┐
│                   历史数据回测系统                            │
└─────────────────────────────────────────────────────────────┘

1. 数据获取层
   ├── MT5 历史数据（Windows环境）
   │   └── from src.common.mt5 import mt5_manager
   │       bars = mt5_client.get_bars(symbol, timeframe, count)
   │
   ├── CSV 文件（跨平台）
   │   └── data/historical/EURUSD_H1_2024.csv
   │
   └── 数据库缓存（推荐）
       └── historical_bars 表

2. 回测引擎（已实现）
   └── BaseEvaluator.run_backtest()
       - 遍历K线
       - 调用策略.on_tick()
       - 模拟订单执行
       - 计算性能指标

3. 评估器调用
   └── HistoricalDataEvaluator.evaluate()
       - 获取真实历史数据
       - 运行回测
       - 返回性能指标
```

#### **数据获取方案对比**

| 方案 | 优点 | 缺点 | 推荐度 |
|------|------|------|--------|
| **方案A：MT5直接获取** | • 数据最新<br>• 无需准备 | • 仅Windows<br>• 网络依赖<br>• 每次获取慢 | ⭐⭐⭐ |
| **方案B：CSV文件** | • 跨平台<br>• 无网络依赖 | • 数据需手动更新<br>• 占用磁盘 | ⭐⭐⭐⭐ |
| **方案C：数据库缓存** | • 最快<br>• 可共享<br>• 支持多品种 | • 需初始导入<br>• 需定期更新 | ⭐⭐⭐⭐⭐ |

#### **推荐方案：C（数据库缓存）+ A（定期更新）**

```python
# 实现步骤

# 1. 数据库表设计
class HistoricalBar(Base):
    __tablename__ = "historical_bars"
    
    id = Column(Integer, primary_key=True)
    symbol = Column(String(10), nullable=False)
    timeframe = Column(String(3), nullable=False)  # H1, H4, D1
    time = Column(DateTime, nullable=False)
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Float)
    
    __table_args__ = (
        Index('idx_symbol_timeframe_time', 'symbol', 'timeframe', 'time'),
        UniqueConstraint('symbol', 'timeframe', 'time')
    )

# 2. 初始数据导入（一次性）
def import_historical_data_from_mt5():
    """从MT5导入历史数据到数据库"""
    if not mt5_manager.is_connected():
        mt5_manager.connect(use_investor=True)
    
    symbols = ['EURUSD', 'GBPUSD', 'USDJPY']
    timeframes = ['H1', 'H4', 'D1']
    bars_count = 10000  # 约1年数据
    
    for symbol in symbols:
        for tf in timeframes:
            print(f"导入 {symbol} {tf}...")
            bars = mt5_client.get_bars(symbol, tf, bars_count)
            
            for bar in bars:
                historical_bar = HistoricalBar(
                    symbol=symbol,
                    timeframe=tf,
                    time=bar['time'],
                    open=bar['open'],
                    high=bar['high'],
                    low=bar['low'],
                    close=bar['close'],
                    volume=bar['volume']
                )
                session.merge(historical_bar)  # 如果存在则更新
            
            session.commit()
            print(f"   ✅ {len(bars)} 根K线")

# 3. 修改 HistoricalDataEvaluator
class HistoricalDataEvaluator(BaseEvaluator):
    
    def _fetch_historical_data(self, symbol, timeframe, bars, 
                               start_date=None, end_date=None):
        """从数据库获取历史数据"""
        query = session.query(HistoricalBar).filter(
            HistoricalBar.symbol == symbol,
            HistoricalBar.timeframe == timeframe
        )
        
        if start_date:
            query = query.filter(HistoricalBar.time >= start_date)
        if end_date:
            query = query.filter(HistoricalBar.time <= end_date)
        
        query = query.order_by(HistoricalBar.time.desc()).limit(bars)
        
        results = query.all()
        
        if not results:
            # 回退到MT5获取（如果数据库没有）
            return self._fetch_from_mt5_fallback(symbol, timeframe, bars)
        
        # 转换为DataFrame
        df = pd.DataFrame([{
            'time': r.time,
            'open': r.open,
            'high': r.high,
            'low': r.low,
            'close': r.close,
            'volume': r.volume
        } for r in results])
        
        return df.sort_values('time')

# 4. 定期更新任务（每天）
def update_historical_data_daily():
    """每天更新最新的历史数据"""
    symbols = ['EURUSD', 'GBPUSD', 'USDJPY']
    
    for symbol in symbols:
        # 获取数据库中最新时间
        latest = session.query(func.max(HistoricalBar.time)).filter(
            HistoricalBar.symbol == symbol,
            HistoricalBar.timeframe == 'H1'
        ).scalar()
        
        # 从MT5获取更新
        if latest:
            # 只获取最新的数据
            bars_needed = calculate_bars_since(latest)
        else:
            bars_needed = 10000
        
        bars = mt5_client.get_bars(symbol, 'H1', bars_needed)
        
        # 插入/更新数据库
        for bar in bars:
            session.merge(HistoricalBar(...))
        
        session.commit()
```

#### **使用方式**

```python
# config/development.yaml
strategy_evaluation:
  include_synthetic: false      # 关闭合成数据
  include_historical: true      # 启用历史数据 ✅
  include_realtime: false
  
  historical_data:
    source: "database"          # database | mt5 | csv
    default_bars: 3000          # 默认K线数量
    fallback_to_mt5: true       # 数据库没有时回退到MT5
```

```python
# 策略生成时自动使用历史数据评估
strategies = service.generate_strategies(count=5)

# 结果：
# 📊 [2/3] 历史数据评估...
#    📊 获取历史数据：EURUSD H1 x 3000根...
#    💾 从数据库加载 3000 根K线
#    ⏱️  时间范围: 2024-01-15 ~ 2024-04-10
#    ✅ 完成 - 综合评分: 65.2
```

---

## 🚀 方案3：ACTIVE策略实时验证架构

### 核心需求

**对于状态为ACTIVE的策略，需要在真实市场环境中持续验证：**
- ✅ 使用Demo账户（避免真实资金风险）
- ✅ 小金额验证（如$100起步）
- ✅ 实时运行，持续收集数据
- ✅ 性能不佳自动降级到CANDIDATE

### 架构设计

```
┌────────────────────────────────────────────────────────────────┐
│              实时验证服务（Live Validation Service）            │
│                        独立进程/容器                            │
└────────────────────────────────────────────────────────────────┘

                        ┌─────────────┐
                        │  Database   │
                        │  strategies │
                        │  (ACTIVE)   │
                        └──────┬──────┘
                               │
                  ┌────────────┴────────────┐
                  │                         │
          ┌───────▼────────┐       ┌───────▼────────┐
          │ Strategy 1     │       │ Strategy 2     │
          │ STR_8a12e1ad   │       │ STR_9b23f2be   │
          │ Demo Account A │       │ Demo Account B │
          │ Balance: $100  │       │ Balance: $100  │
          └───────┬────────┘       └───────┬────────┘
                  │                         │
                  └────────────┬────────────┘
                               │
                   ┌───────────▼───────────┐
                   │  Live Validator       │
                   │                       │
                   │  • Tick监听           │
                   │  • 策略运行           │
                   │  • 订单执行           │
                   │  • 性能监控           │
                   │  • 自动降级           │
                   └───────────┬───────────┘
                               │
                   ┌───────────▼───────────┐
                   │   MT5 Demo Server     │
                   │   (实时行情+交易)      │
                   └───────────────────────┘
```

### 服务设计

#### **目录结构**

```
src/services/live_validator/
├── __init__.py
├── main.py                    # 服务入口
├── validator/
│   ├── __init__.py
│   ├── live_validator.py      # 核心验证器
│   ├── strategy_runner.py     # 策略运行器
│   └── performance_tracker.py # 性能追踪
├── config/
│   └── validator_config.yaml  # 验证配置
└── api/
    └── app.py                 # 监控API
```

#### **核心代码**

```python
# live_validator.py
class LiveValidator:
    """实时验证服务 - 持续运行ACTIVE策略"""
    
    def __init__(self):
        self.mt5_manager = mt5_manager
        self.running_strategies = {}  # {strategy_id: StrategyRunner}
        self.db = db
        
        # 验证配置
        self.config = {
            'initial_balance': 100.0,      # 每个策略$100
            'max_drawdown_threshold': 0.20, # 最大回撤20%
            'min_sharpe_ratio': 0.5,       # 最低Sharpe
            'evaluation_period_hours': 24,  # 评估周期24小时
            'stop_loss_threshold': 0.30     # 亏损30%停止
        }
    
    async def start(self):
        """启动验证服务"""
        print("🚀 启动实时验证服务...")
        
        # 连接MT5
        if not self.mt5_manager.connect(use_investor=True):
            raise RuntimeError("MT5连接失败")
        
        # 加载ACTIVE策略
        await self.load_active_strategies()
        
        # 启动监听循环
        await self.run_validation_loop()
    
    async def load_active_strategies(self):
        """加载所有ACTIVE状态的策略"""
        with self.db.session_scope() as session:
            active_strategies = session.query(Strategy).filter(
                Strategy.status == StrategyStatus.ACTIVE
            ).all()
            
            print(f"📋 找到 {len(active_strategies)} 个ACTIVE策略")
            
            for strategy in active_strategies:
                # 为每个策略创建运行器
                runner = StrategyRunner(
                    strategy=strategy,
                    mt5_client=self.mt5_manager.get_client(),
                    initial_balance=self.config['initial_balance']
                )
                
                self.running_strategies[strategy.id] = runner
                print(f"   ✅ {strategy.name} ({strategy.id})")
    
    async def run_validation_loop(self):
        """主验证循环 - 持续运行"""
        print("🔄 开始验证循环...")
        
        while True:
            try:
                # 获取最新Tick
                tick = await self._get_latest_tick('EURUSD')
                
                # 对每个策略运行验证
                for strategy_id, runner in self.running_strategies.items():
                    await self._validate_strategy(runner, tick)
                
                # 每小时检查性能
                await self._hourly_performance_check()
                
                # 等待下一个Tick
                await asyncio.sleep(1)
                
            except KeyboardInterrupt:
                print("\n⏹️  停止验证服务")
                break
            except Exception as e:
                print(f"❌ 验证循环错误: {e}")
                await asyncio.sleep(5)
    
    async def _validate_strategy(self, runner: StrategyRunner, tick: dict):
        """验证单个策略"""
        # 1. 运行策略逻辑
        signal = runner.on_tick(tick)
        
        # 2. 如果有信号，执行订单
        if signal:
            await self._execute_signal(runner, signal)
        
        # 3. 更新持仓状态
        runner.update_positions(tick)
        
        # 4. 检查止损条件
        if runner.current_balance < runner.initial_balance * (1 - self.config['stop_loss_threshold']):
            await self._stop_strategy(runner, reason="stop_loss_triggered")
    
    async def _hourly_performance_check(self):
        """每小时性能检查"""
        current_hour = datetime.now().hour
        
        if current_hour % 1 == 0:  # 每小时执行一次
            for strategy_id, runner in self.running_strategies.items():
                metrics = runner.calculate_performance()
                
                # 保存性能记录
                await self._save_performance_snapshot(strategy_id, metrics)
                
                # 检查是否需要降级
                if self._should_downgrade(metrics):
                    await self._downgrade_strategy(strategy_id, metrics)
    
    def _should_downgrade(self, metrics: dict) -> bool:
        """判断是否应该降级策略"""
        # 条件1: Sharpe过低
        if metrics['sharpe_ratio'] < self.config['min_sharpe_ratio']:
            return True
        
        # 条件2: 回撤过大
        if metrics['max_drawdown'] > self.config['max_drawdown_threshold']:
            return True
        
        # 条件3: 连续亏损
        if metrics.get('consecutive_losses', 0) > 5:
            return True
        
        return False
    
    async def _downgrade_strategy(self, strategy_id: str, metrics: dict):
        """降级策略到CANDIDATE"""
        print(f"⚠️  策略 {strategy_id} 性能不佳，降级到CANDIDATE")
        
        with self.db.session_scope() as session:
            strategy = session.query(Strategy).get(strategy_id)
            strategy.status = StrategyStatus.CANDIDATE
            
            # 记录降级原因
            strategy.metadata = strategy.metadata or {}
            strategy.metadata['downgrade_reason'] = {
                'time': datetime.now().isoformat(),
                'metrics': metrics,
                'reason': 'poor_live_performance'
            }
            
            session.commit()
        
        # 停止运行
        runner = self.running_strategies.pop(strategy_id)
        runner.stop()

# strategy_runner.py
class StrategyRunner:
    """策略运行器 - 单个策略的实时运行"""
    
    def __init__(self, strategy: Strategy, mt5_client, initial_balance: float):
        self.strategy = strategy
        self.mt5_client = mt5_client
        self.initial_balance = initial_balance
        self.current_balance = initial_balance
        
        # 加载策略代码
        self.strategy_instance = self._load_strategy_code(strategy.code)
        
        # 数据缓存
        self.tick_buffer = []
        self.positions = []
        
        # 性能追踪
        self.trades = []
        self.equity_curve = []
    
    def _load_strategy_code(self, code: str):
        """动态加载策略代码"""
        namespace = {}
        exec(code, namespace)
        
        # 找到策略类
        strategy_class = None
        for name, obj in namespace.items():
            if name.startswith('Strategy_') and isinstance(obj, type):
                strategy_class = obj
                break
        
        if not strategy_class:
            raise ValueError("策略代码中未找到Strategy类")
        
        return strategy_class()
    
    def on_tick(self, tick: dict) -> Optional[str]:
        """处理Tick数据"""
        # 更新缓冲区
        self.tick_buffer.append(tick)
        
        # 保持最近100个Tick
        if len(self.tick_buffer) > 100:
            self.tick_buffer.pop(0)
        
        # 转换为DataFrame（策略需要）
        df = pd.DataFrame(self.tick_buffer)
        
        # 调用策略逻辑
        try:
            signal = self.strategy_instance.on_tick(df)
            return signal
        except Exception as e:
            print(f"策略执行错误: {e}")
            return None
    
    def calculate_performance(self) -> dict:
        """计算当前性能指标"""
        if not self.trades:
            return {
                'sharpe_ratio': 0,
                'max_drawdown': 0,
                'win_rate': 0,
                'total_trades': 0
            }
        
        # 计算指标
        profits = [t['profit'] for t in self.trades]
        returns = np.array(profits) / self.initial_balance
        
        sharpe = np.mean(returns) / (np.std(returns) + 1e-6) * np.sqrt(252)
        
        # 计算回撤
        cumulative = np.cumsum(profits)
        running_max = np.maximum.accumulate(cumulative)
        drawdown = (cumulative - running_max) / self.initial_balance
        max_drawdown = abs(drawdown.min())
        
        # 胜率
        wins = sum(1 for p in profits if p > 0)
        win_rate = wins / len(profits) if profits else 0
        
        return {
            'sharpe_ratio': sharpe,
            'max_drawdown': max_drawdown,
            'win_rate': win_rate,
            'total_trades': len(self.trades),
            'total_profit': sum(profits),
            'current_balance': self.current_balance
        }
```

#### **部署架构**

```
┌─────────────────────────────────────────────────────────┐
│                    服务器架构                            │
└─────────────────────────────────────────────────────────┘

方案1: 独立服务器（推荐）
  ├── VPS/云服务器（Windows Server）
  │   ├── MT5 Terminal（连接Demo服务器）
  │   ├── Live Validator Service（后台运行）
  │   └── 数据库连接（远程连接主数据库）
  │
  └── 特点：
      ✅ 7x24运行
      ✅ 独立资源
      ✅ 不影响其他服务
      
方案2: Docker容器
  ├── docker-compose.yml
  │   ├── live-validator:
  │   │   └── 运行验证服务
  │   └── mt5-mock:（macOS开发环境）
  │       └── 模拟MT5接口
  │
  └── 特点：
      ✅ 易于部署
      ✅ 跨平台（开发环境）
      ⚠️  需要处理MT5兼容性
```

#### **监控API**

```python
# src/services/live_validator/api/app.py
@router.get("/status")
def get_validator_status():
    """获取验证服务状态"""
    return {
        "running": True,
        "active_strategies": len(validator.running_strategies),
        "mt5_connected": mt5_manager.is_connected(),
        "uptime_hours": calculate_uptime()
    }

@router.get("/strategies")
def get_running_strategies():
    """获取正在运行的策略"""
    results = []
    for strategy_id, runner in validator.running_strategies.items():
        metrics = runner.calculate_performance()
        results.append({
            "strategy_id": strategy_id,
            "name": runner.strategy.name,
            "balance": runner.current_balance,
            "trades": len(runner.trades),
            "sharpe": metrics['sharpe_ratio'],
            "drawdown": metrics['max_drawdown']
        })
    return {"strategies": results}

@router.post("/strategies/{strategy_id}/stop")
def stop_strategy(strategy_id: str):
    """手动停止策略"""
    runner = validator.running_strategies.get(strategy_id)
    if runner:
        runner.stop()
        validator.running_strategies.pop(strategy_id)
        return {"success": True}
    return {"success": False, "error": "策略不存在"}
```

---

## 📊 三个阶段的策略验证

```
┌─────────────────────────────────────────────────────────────┐
│                   策略生命周期验证                            │
└─────────────────────────────────────────────────────────────┘

阶段1: CANDIDATE（生成时）
  └── 历史数据回测
      ├── 数据：最近1年真实历史数据
      ├── 时间：<1分钟
      └── 目的：快速筛选明显不行的策略

阶段2: ACTIVE（激活后）
  └── 实时验证（Live Validator）
      ├── 环境：Demo账户 + 真实行情
      ├── 时间：持续运行（7x24）
      ├── 资金：$100小金额
      └── 目的：验证真实市场表现

阶段3: 降级/保留
  ├── 表现好 → 保持ACTIVE → 考虑真实资金
  └── 表现差 → 降级CANDIDATE → 归档/删除
```

---

## 🎯 实施步骤

### **Phase 1: 历史数据回测（1-2天）**

1. ✅ 创建`historical_bars`表
2. ✅ 实现MT5数据导入脚本
3. ✅ 修改`HistoricalDataEvaluator._fetch_historical_data()`
4. ✅ 更新配置：启用历史数据评估
5. ✅ 测试：生成策略，验证使用真实数据

### **Phase 2: 实时验证服务（3-5天）**

1. ✅ 创建`live_validator`服务目录
2. ✅ 实现`LiveValidator`核心逻辑
3. ✅ 实现`StrategyRunner`运行器
4. ✅ 添加性能追踪和自动降级
5. ✅ 部署到独立服务器/容器
6. ✅ 接入监控API到Dashboard

### **Phase 3: Dashboard集成（1天）**

1. ✅ 添加"实时验证"状态显示
2. ✅ 显示ACTIVE策略的实时性能
3. ✅ 一键启动/停止验证
4. ✅ 性能告警提示

---

## 🔧 配置文件

```yaml
# config/development.yaml

# 策略评估配置
strategy_evaluation:
  # 历史数据回测
  include_historical: true
  historical_data:
    source: "database"        # database | mt5 | csv
    default_bars: 3000
    symbols: ['EURUSD', 'GBPUSD', 'USDJPY']
    timeframe: 'H1'
  
  # 实时验证
  live_validation:
    enabled: true
    demo_account: true        # 使用Demo账户
    initial_balance: 100.0
    max_strategies: 10        # 最多同时运行10个策略
    
    # 降级阈值
    thresholds:
      max_drawdown: 0.20      # 最大回撤20%
      min_sharpe: 0.5         # 最低Sharpe 0.5
      stop_loss: 0.30         # 亏损30%停止
      evaluation_hours: 24    # 24小时评估周期
```

---

## 📈 预期效果

### **历史数据回测**
```
生成策略时：
📊 [2/3] 历史数据评估...
   📊 获取历史数据：EURUSD H1 x 3000根...
   💾 从数据库加载（2024-01-15 ~ 2024-04-10）
   ⏱️  回测运行中...
   ✅ 完成 - 推荐度: 72.3分
   
   Sharpe: 1.85
   最大回撤: 8.5%
   胜率: 62.3%
   交易数: 156
```

### **实时验证监控**
```
Dashboard → 策略列表 → STR_8a12e1ad

状态: ACTIVE 🟢 实时运行中
验证时长: 18小时
Demo余额: $112.50 (+12.5%)
交易次数: 8次
当前Sharpe: 1.92
实时回撤: 3.2%

[停止验证] [查看详情]
```

---

## ✅ 总结

| 阶段 | 验证方式 | 数据来源 | 耗时 | 目的 |
|------|---------|---------|------|------|
| **生成时** | 历史回测 | 真实历史数据（数据库） | <1分钟 | 快速筛选 |
| **激活后** | 实时验证 | Demo账户+实时行情 | 持续24h+ | 真实验证 |
| **降级判断** | 性能监控 | 实时交易记录 | 自动 | 优胜劣汰 |

**这是一个完整的策略工厂流水线：生成 → 回测 → 实战 → 淘汰。** 🏭
