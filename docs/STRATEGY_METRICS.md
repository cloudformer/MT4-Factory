# 策略指标计算文档

## 📊 指标计算说明

所有策略评估指标在 `src/services/strategy/evaluator/base_evaluator.py` 中计算。

---

## ⚙️ 可调参数

### 1. 配置文件参数 (`config/development.yaml`)

```yaml
strategy_evaluation:
  parameters:
    initial_balance: 10000.0     # 初始资金（USD）
    synthetic_bars: 3000          # K线数量
    symbol: "EURUSD"             # 交易品种
```

### 2. 代码固定参数 (`base_evaluator.py`)

| 参数 | 位置 | 值 | 说明 |
|------|------|-----|------|
| `volume` | 行104 | 0.1 | 固定手数 |
| `contract_size` | 行74,76,116,117 | 100000 | 标准手（1手=100000基础货币）|
| `warm_up_period` | 行37 | 50 | 预热K线数（用于计算均线等指标）|

---

## 📈 核心指标计算公式

### 收益指标

#### 1. 总收益率 (Total Return)
```python
total_return = (final_balance - initial_balance) / initial_balance
# 例: (17462 - 10000) / 10000 = 0.7462 = 74.62%
```

#### 2. 胜率 (Win Rate)
```python
win_rate = winning_trades_count / total_trades
# 例: 12 / 15 = 0.8 = 80%
```

#### 3. 盈亏比 (Profit Factor)
```python
profit_factor = total_profit / abs(total_loss)
# 例: 14650 / 123 = 119.1
```

#### 4. 平均盈利/亏损
```python
avg_win = sum(winning_pnl) / winning_count
avg_loss = sum(abs(losing_pnl)) / losing_count
avg_win_loss_ratio = avg_win / avg_loss
# 例: 1465 / 41 = 36.03
```

---

### 风险指标

#### 5. 最大回撤 (Max Drawdown)
```python
# 计算每个时刻的回撤
equity_array = [balance_at_each_bar]
running_max = np.maximum.accumulate(equity_array)
drawdown = (equity_array - running_max) / running_max
max_drawdown = abs(min(drawdown))
# 例: 2.0% = 0.02
```

#### 6. 波动率 (Volatility)
```python
equity_returns = diff(equity_array) / equity_array[:-1]
volatility = std(equity_returns) * sqrt(8760)  # 年化
# 例: 9.6% = 0.096
```

#### 7. Sharpe Ratio
```python
annual_factor = sqrt(8760 / len(returns))  # 假设H1周期
sharpe_ratio = (mean(returns) / std(returns)) * annual_factor
# 例: 0.57
```

#### 8. Sortino Ratio
```python
# 只考虑下行波动
downside_returns = returns[returns < 0]
downside_std = std(downside_returns)
sortino_ratio = (mean(returns) / downside_std) * annual_factor
# 例: 0.85
```

---

### 交易特征

#### 9. 交易频率
```python
trade_frequency = (total_trades / total_bars) * 100
# 例: (15 / 3000) * 100 = 0.5 笔/100K线
```

#### 10. 平均持仓时间
```python
avg_holding_time = mean([exit_idx - entry_idx for each trade])
# 以K线数为单位，例: 192根K线 = 192小时（H1周期）
```

#### 11. 最大连续胜/负
```python
# 遍历所有交易，统计连续盈利/亏损次数
max_consecutive_wins = 9
max_consecutive_losses = 1
```

---

### 稳定性指标

#### 12. 稳定性评分 (Stability Score)
```python
# 基于收益变异系数
trade_returns = [pnl / initial_balance for each trade]
cv = std(trade_returns) / abs(mean(trade_returns))
stability_score = 1 / (1 + cv)  # 0-1，越高越稳定
# 例: 35% = 0.35
```

#### 13. 一致性评分 (Consistency Score)
```python
# 胜率和盈亏比的均衡性
consistency = min(win_rate, 1-win_rate) * 2 * min(profit_factor/3, 1)
# 例: 40% = 0.40
```

---

### 综合评分

#### 14. 推荐度评分 (Recommendation Score)
```python
# 加权综合评分 (0-100)
return_score = min(total_return * 100, 100)
risk_score = max(0, 100 - risk_profile_score * 10)
stability_score = stability * 100

overall_score = (
    return_score * 0.4 +      # 40% 收益权重
    risk_score * 0.35 +       # 35% 风险权重
    stability_score * 0.25    # 25% 稳定性权重
)
```

#### 15. 风险评分 (Risk Score)
```python
# 0-10分，越低越安全
risk_score = 0

# 胜率贡献 (0-2分)
if win_rate < 0.4: risk_score += 2
elif win_rate < 0.5: risk_score += 1

# 回撤贡献 (0-3分)
if max_dd > 0.20: risk_score += 3
elif max_dd > 0.12: risk_score += 2
elif max_dd > 0.08: risk_score += 1

# Sharpe贡献 (0-2分)
if sharpe < 0.5: risk_score += 2
elif sharpe < 1: risk_score += 1

# 波动率贡献 (0-3分)
if volatility > 0.40: risk_score += 3
elif volatility > 0.25: risk_score += 2
elif volatility > 0.15: risk_score += 1
```

---

## 🤖 LLM生成策略 + 自定义参数

### 方式1：通过API生成策略

```python
# POST /strategies/generate
{
    "count": 1,
    "base_strategy_type": "ma_cross",  # 可选：ma_cross, rsi, bollinger等
    "custom_params": {                   # 可选：自定义参数
        "fast_period": 10,
        "slow_period": 30
    }
}
```

### 方式2：直接修改策略代码中的参数

```python
class Strategy_XXX:
    def __init__(self):
        # 可调参数
        self.fast_period = 12      # 快线周期
        self.slow_period = 60      # 慢线周期
        self.volume = 0.1          # 固定手数
```

### 方式3：通过配置文件批量生成

```yaml
# config/strategy_generation.yaml
strategy_templates:
  ma_cross:
    fast_periods: [5, 10, 12, 15, 20]
    slow_periods: [30, 40, 50, 60]
```

---

## 🔧 自定义评估参数

### 修改初始资金

```python
# 方法1: 配置文件
config/development.yaml:
  strategy_evaluation:
    parameters:
      initial_balance: 50000.0  # 改为5万美元

# 方法2: 代码调用
from src.services.strategy.evaluator.strategy_evaluator import StrategyEvaluator

evaluator = StrategyEvaluator(initial_balance=50000.0)
result = evaluator.evaluate_synthetic(strategy_code)
```

### 修改固定手数

```python
# 编辑 base_evaluator.py 第104行
def _open_position(self, direction: str, bar: pd.Series, idx: int) -> Tuple:
    entry_price = bar['close']
    volume = 0.2  # 改为0.2手
    return (direction, entry_price, volume, idx)
```

### 修改K线数量

```python
# 方法1: 配置文件
config/development.yaml:
  strategy_evaluation:
    parameters:
      synthetic_bars: 5000  # 改为5000根K线

# 方法2: 代码调用
evaluator.evaluate_synthetic(strategy_code, symbol="EURUSD", bars=5000)
```

---

## 📝 策略代码规范

### 必须实现的接口

```python
class Strategy_XXX:
    def __init__(self):
        # 初始化参数
        self.fast_period = 10
        self.slow_period = 20
    
    def on_tick(self, data: pd.DataFrame) -> Optional[str]:
        """
        策略逻辑
        
        Args:
            data: 历史K线数据，包含 open, high, low, close, volume
        
        Returns:
            'buy' - 买入信号
            'sell' - 卖出信号
            None - 无信号
        """
        # 计算指标
        fast_ma = data['close'].rolling(self.fast_period).mean()
        slow_ma = data['close'].rolling(self.slow_period).mean()
        
        # 交叉判断
        if fast_ma.iloc[-1] > slow_ma.iloc[-1] and fast_ma.iloc[-2] <= slow_ma.iloc[-2]:
            return 'buy'
        elif fast_ma.iloc[-1] < slow_ma.iloc[-1] and fast_ma.iloc[-2] >= slow_ma.iloc[-2]:
            return 'sell'
        
        return None
```

---

## 🎯 示例：用户场景

### 场景1：生成并评估带自定义参数的策略

```python
from src.services.strategy.service.generator import StrategyGenerator
from src.services.strategy.evaluator.strategy_evaluator import StrategyEvaluator

# 1. 生成策略（通过LLM）
generator = StrategyGenerator()
strategy_code = generator.generate_ma_cross_strategy(
    fast_period=12,
    slow_period=60
)

# 2. 评估策略（自定义资金）
evaluator = StrategyEvaluator(initial_balance=20000.0)
result = evaluator.evaluate_synthetic(
    strategy_code=strategy_code,
    symbol="GBPUSD",
    bars=5000
)

print(f"推荐度: {result['recommendation_summary']['recommendation_score']}")
print(f"总收益: {result['total_return']*100:.2f}%")
print(f"Sharpe: {result['sharpe_ratio']}")
```

### 场景2：批量测试不同参数组合

```python
# 参数网格搜索
fast_periods = [10, 12, 15, 20]
slow_periods = [30, 40, 50, 60]

best_score = 0
best_params = None

for fast in fast_periods:
    for slow in slow_periods:
        # 生成策略
        code = generator.generate_ma_cross_strategy(fast, slow)
        
        # 评估
        result = evaluator.evaluate_synthetic(code)
        score = result['recommendation_summary']['recommendation_score']
        
        if score > best_score:
            best_score = score
            best_params = (fast, slow)

print(f"最佳参数: MA({best_params[0]}, {best_params[1]}) - 评分: {best_score}")
```

---

## 📚 相关文件

- **评估器**: `src/services/strategy/evaluator/base_evaluator.py`
- **配置**: `src/common/config/evaluation_config.py`
- **策略生成**: `src/services/strategy/service/generator.py`
- **配置文件**: `config/development.yaml`
