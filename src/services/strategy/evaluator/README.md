# 策略评估器模块 (Strategy Evaluator)

## 📖 概述

策略评估器模块负责对生成的交易策略进行回测和评估，支持三种评估模式：

1. **合成数据评估** (Synthetic Data) - 使用模拟数据快速评估 ✅ 已实现
2. **历史数据评估** (Historical Data) - 使用真实历史数据回测 🚧 待实现
3. **实时数据评估** (Realtime Data) - 在实时行情中纸面交易测试 🚧 待实现

## 📁 目录结构

```
evaluator/
├── __init__.py                    # 模块导出
├── base_evaluator.py              # 基础评估器（核心逻辑）
├── synthetic_evaluator.py         # 合成数据评估器 ✅
├── historical_evaluator.py        # 历史数据评估器 🚧
├── realtime_evaluator.py          # 实时数据评估器 🚧
├── strategy_evaluator.py          # 主评估器（统一接口）
└── README.md                      # 本文档
```

## 🚀 快速开始

### 基本使用

```python
from src.services.strategy.evaluator import StrategyEvaluator

# 创建评估器
evaluator = StrategyEvaluator(initial_balance=10000.0)

# 评估策略（默认使用合成数据）
strategy_code = """
class Strategy_xxx:
    def on_tick(self, data):
        # 策略逻辑
        pass
"""

result = evaluator.evaluate_synthetic(strategy_code, symbol="EURUSD", bars=3000)
print(f"推荐度: {result['recommendation_summary']['recommendation_score']}分")
```

### 运行所有评估

```python
# 运行所有已实现的评估方式
results = evaluator.evaluate_all(
    strategy_code,
    symbol="EURUSD",
    include_synthetic=True,      # ✅ 合成数据
    include_historical=False,    # ❌ 暂未实现
    include_realtime=False       # ❌ 未来使用
)

# 查看综合评分
print(results['summary'])
```

## 📊 评估器详解

### 1. 合成数据评估器 (SyntheticDataEvaluator) ✅

**用途**: 使用模拟数据快速评估策略

**特点**:
- 快速生成3000根H1 K线
- 模拟市场制度切换（趋势/震荡交替）
- 无需外部数据，开箱即用
- 适合开发阶段快速验证策略逻辑

**使用场景**:
- ✅ 策略生成后的初步筛选
- ✅ 开发阶段快速迭代
- ✅ 参数优化对比
- ❌ 最终实盘决策（需要历史数据验证）

**示例**:
```python
from src.services.strategy.evaluator import SyntheticDataEvaluator

evaluator = SyntheticDataEvaluator(initial_balance=10000.0)
result = evaluator.evaluate(strategy_code, symbol="EURUSD", bars=3000)

print(f"数据来源: {result['data_source']}")  # 'synthetic'
print(f"总收益: {result['total_return']*100:.2f}%")
print(f"Sharpe比率: {result['sharpe_ratio']}")
```

**数据生成逻辑**:
```python
# 基础随机游走
returns = np.random.normal(0, 0.003, bars)  # 0.3%标准差

# 市场制度切换（每200根K线）
- 50%概率趋势期 → 添加单边趋势
- 50%概率震荡期 → 保持随机游走
```

---

### 2. 历史数据评估器 (HistoricalDataEvaluator) 🚧

**用途**: 使用真实历史数据回测策略

**状态**: 🚧 待实现，接口已预留

**计划实现方式**:
1. **从MT5获取** (Windows环境)
   ```python
   evaluator.load_from_mt5(symbol="EURUSD", timeframe="H1", bars=3000)
   ```

2. **从CSV文件加载**
   ```python
   evaluator.load_from_csv("data/EURUSD_H1.csv")
   ```
   CSV格式：
   ```
   time,open,high,low,close,volume
   2024-01-01 00:00:00,1.0850,1.0855,1.0845,1.0852,500
   ```

3. **从数据库查询**
   ```python
   # TODO: 实现数据库历史数据表
   ```

**使用场景**:
- ✅ 策略通过合成数据筛选后的进一步验证
- ✅ 实盘前的最终测试
- ✅ 对比不同历史时期的表现

---

### 3. 实时数据评估器 (RealtimeDataEvaluator) 🚧

**用途**: 在实时行情中进行纸面交易测试

**状态**: 🚧 待实现，接口已预留

**计划实现方式**:
```python
evaluator = RealtimeDataEvaluator(initial_balance=10000.0)

# 运行60分钟纸面交易测试
result = evaluator.evaluate(
    strategy_code,
    symbol="EURUSD",
    duration_minutes=60
)
```

**使用场景**:
- ✅ 策略通过历史回测后的实时验证
- ✅ 检测策略在真实行情节奏下的表现
- ✅ 实盘前的最后一道测试

---

## 🎯 主评估器 (StrategyEvaluator)

**统一接口，协调所有评估方式，使用加权平均计算综合评分**

```python
from src.services.strategy.evaluator import StrategyEvaluator

evaluator = StrategyEvaluator(initial_balance=10000.0)

# 方式1：单独评估
synthetic_result = evaluator.evaluate_synthetic(strategy_code)
historical_result = evaluator.evaluate_historical(strategy_code)  # 🚧 待实现
realtime_result = evaluator.evaluate_realtime(strategy_code)      # 🚧 待实现

# 方式2：统一评估（使用加权平均）
all_results = evaluator.evaluate_all(
    strategy_code,
    include_synthetic=True,
    include_historical=True,
    include_realtime=False
)

# 综合总结（加权平均结果）
print(all_results['summary'])
{
    'overall_score': 71.3,                    # 综合评分（加权平均）
    'calculation_method': 'weighted_average', # 计算方法
    'individual_scores': {                    # 各评估方式的分数
        'synthetic': 68.5,
        'historical': 72.8
    },
    'weights_used': {                         # 实际使用的权重
        'historical': '75%',
        'synthetic': '25%'
    },
    'consistency': 'high',                    # 一致性（各评估方式结果差异）
    'consistency_note': '各评估方式结果高度一致',
    'successful_evaluations': 2,
    'failed_evaluations': 0
}

# 对比分析
comparison = evaluator.compare_evaluations(all_results)
print(comparison['discrepancies'])  # 查看重大差异
```

### 📊 加权平均规则

评估器会根据实际启用的评估方式，**动态调整权重**：

| 启用的评估方式 | 权重分配 | 说明 |
|---------------|---------|------|
| 仅 synthetic | synthetic: **100%** | 开发阶段，单一评估 |
| synthetic + historical | historical: **75%**, synthetic: **25%** | 历史数据为主 |
| synthetic + realtime | synthetic: **60%**, realtime: **40%** | 合成数据为主 |
| historical + realtime | historical: **75%**, realtime: **25%** | 历史数据为主 |
| **全部三个** | historical: **60%**, synthetic: **20%**, realtime: **20%** | 历史为主，其他辅助 |

**设计原理**：
- **历史数据权重最高(60-75%)** - 真实市场数据最可靠
- **合成数据权重较低(20-25%)** - 作为辅助参考，不主导决策
- **实时数据权重较低(20-40%)** - 防止短期噪声影响长期评估

**权重配置** (可在代码中修改):
```python
# src/services/strategy/evaluator/strategy_evaluator.py
self.evaluation_weights = {
    'historical': 0.60,  # 历史数据最可靠，权重最高
    'synthetic': 0.20,   # 合成数据作为辅助参考
    'realtime': 0.20     # 实时数据权重较低，防止短期噪声
}
```

---

## 📈 评估指标

每种评估方式都会返回22个性能指标 + 适用性评估：

### 基础指标
- `total_return`: 总收益率
- `final_balance`: 最终余额
- `total_trades`: 总交易数

### 收益指标
- `sharpe_ratio`: Sharpe比率
- `sortino_ratio`: Sortino比率
- `calmar_ratio`: Calmar比率
- `profit_factor`: 盈亏比
- `win_rate`: 胜率
- `avg_win`: 平均盈利
- `avg_loss`: 平均亏损

### 风险指标
- `max_drawdown`: 最大回撤
- `avg_drawdown`: 平均回撤
- `volatility`: 年化波动率
- `recovery_factor`: 回撤恢复因子

### 交易特征
- `trade_frequency`: 交易频率（每100根K线）
- `avg_holding_time`: 平均持仓时间（K线数）
- `max_consecutive_wins`: 最大连续盈利
- `max_consecutive_losses`: 最大连续亏损

### 稳定性
- `stability_score`: 稳定性评分 (0-1)
- `consistency_score`: 一致性评分 (0-1)

### 风险分类
- `risk_type`: 风险类型（5种）
- `risk_score`: 风险分数 (0-10)
- `risk_level`: 风险等级 (low/medium/high)

### 适用性评估
- `suitability`: 完整的适用性分析
- `recommendation_summary`: 简洁推荐摘要

---

## 🔧 在generator中的使用

策略生成服务已集成新的评估器：

```python
# src/services/strategy/service/generator.py

def generate_strategies(self, count: int, template: str = "ma_crossover"):
    for i in range(count):
        strategy_code = self._generate_code(...)
        
        # 使用评估器
        evaluator = StrategyEvaluator(initial_balance=10000.0)
        
        results = evaluator.evaluate_all(
            strategy_code,
            include_synthetic=True,      # ✅ 生成时默认使用
            include_historical=False,    # ❌ 可按需开启
            include_realtime=False       # ❌ 未来使用
        )
        
        performance = results['evaluations']['synthetic']
        
        # 保存策略
        strategy = Strategy(..., performance=performance)
```

---

## 🛠️ 扩展指南

### 实现历史数据获取

1. **从MT5获取**（Windows环境）
   ```python
   # historical_evaluator.py
   
   def load_from_mt5(self, symbol: str, timeframe: str, bars: int):
       import MetaTrader5 as mt5
       
       mt5.initialize()
       
       # 时间周期映射
       tf_map = {
           'M1': mt5.TIMEFRAME_M1,
           'H1': mt5.TIMEFRAME_H1,
           # ...
       }
       
       rates = mt5.copy_rates_from_pos(
           symbol, 
           tf_map[timeframe], 
           0, 
           bars
       )
       
       df = pd.DataFrame(rates)
       df['time'] = pd.to_datetime(df['time'], unit='s')
       
       mt5.shutdown()
       return df
   ```

2. **从CSV加载**（已实现接口）
   ```python
   evaluator = HistoricalDataEvaluator()
   data = evaluator.load_from_csv("data/EURUSD_H1.csv")
   ```

### 实现实时tick获取

```python
# realtime_evaluator.py

def _fetch_realtime_tick(self, symbol: str):
    import MetaTrader5 as mt5
    
    tick = mt5.symbol_info_tick(symbol)
    
    return {
        'time': datetime.fromtimestamp(tick.time),
        'bid': tick.bid,
        'ask': tick.ask
    }
```

---

## 🎯 使用建议

### 开发阶段
```
生成策略 → 合成数据评估（快速筛选） → 筛选出推荐度>65的策略
```

### 准实盘阶段
```
合成数据筛选 → 历史数据验证 → 实时纸面测试 → 实盘小仓位
```

### 评估一致性检查
```python
results = evaluator.evaluate_all(strategy_code, include_synthetic=True, include_historical=True)

if results['summary']['consistency'] == 'low':
    print("⚠️  不同评估方式结果差异较大，谨慎使用")
```

---

## 📝 常见问题

**Q: 为什么合成数据评估的结果可能不准确？**
A: 合成数据是随机模拟的，不包含真实市场的微观结构、流动性、新闻事件等因素。适合初步筛选，但不能作为最终决策依据。

**Q: 历史数据评估何时可用？**
A: 预计在v2实现，需要：
1. MT5历史数据接口（Windows环境）
2. 或CSV数据导入功能
3. 或数据库历史数据表

**Q: 实时评估和实盘的区别？**
A: 实时评估是纸面交易，不会真实下单，用于测试策略在真实行情节奏下的表现。实盘才会真实交易。

**Q: 如何选择评估方式？**
A:
- 开发阶段：合成数据（快速迭代）
- 准实盘前：历史数据（真实验证）
- 实盘前：实时评估（最后测试）

---

## 🔗 相关文档

- [策略生成服务](../service/generator.py)
- [回测引擎（已废弃）](../service/backtester.py)
- [策略适用性评估示例](../../../../docs/strategy_suitability_example.md)
