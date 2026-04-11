# 策略评估配置指南

## 📖 概述

策略评估系统的所有重要参数现在都在配置文件中管理，无需修改代码即可调整评估行为。

**配置文件位置**: `config/development.yaml`

## 🎯 配置项说明

### 1. 启用的评估方式

```yaml
strategy_evaluation:
  enabled_evaluators:
    synthetic: true      # ✅ 合成数据评估（默认开启）
    historical: false    # ❌ 历史数据评估（待实现）
    realtime: false      # ❌ 实时数据评估（待实现）
```

**作用**: 控制生成策略时默认使用哪些评估方式

**当前状态**:
- `synthetic: true` → 生成策略时自动运行合成数据回测 ✅
- `historical: false` → 不运行历史数据回测（功能待实现）
- `realtime: false` → 不运行实时测试（功能待实现）

### 2. 评估权重配置

#### 三种评估都启用时的权重

```yaml
weights:
  historical: 0.60     # 60% - 真实历史数据最可靠
  synthetic: 0.20      # 20% - 模拟数据辅助参考
  realtime: 0.20       # 20% - 实时数据防止短期噪声
```

**作用**: 当三种评估方式都启用时，综合评分的权重分配

**设计原理**:
- 历史数据最可靠，权重最高(60%)
- 实时数据权重较低(20%)，防止短期噪声
- 合成数据作为辅助(20%)

#### 双评估权重配置

```yaml
two_evaluator_weights:
  # synthetic + historical
  synthetic_historical:
    historical: 0.75
    synthetic: 0.25
    
  # synthetic + realtime
  synthetic_realtime:
    synthetic: 0.60
    realtime: 0.40
    
  # historical + realtime
  historical_realtime:
    historical: 0.75
    realtime: 0.25
```

**作用**: 当只启用两种评估方式时，自动使用对应的权重

### 3. 评估参数

```yaml
parameters:
  initial_balance: 10000.0        # 初始资金
  synthetic_bars: 3000            # 合成数据K线数量
  historical_bars: 3000           # 历史数据K线数量
  realtime_duration_minutes: 60   # 实时测试持续时间（分钟）
  symbol: "EURUSD"                # 默认交易品种
```

**参数说明**:
- `initial_balance`: 回测初始资金（美元）
- `synthetic_bars`: 合成数据生成的K线数量
- `historical_bars`: 历史数据回测使用的K线数量
- `realtime_duration_minutes`: 实时纸面交易测试的持续时间
- `symbol`: 默认交易品种

## 🚀 使用示例

### 场景1：使用默认配置生成策略

```python
# generator.py 中
evaluator = StrategyEvaluator()  # 自动从配置文件读取参数
results = evaluator.evaluate_all(strategy_code)  # 自动使用配置的启用状态
```

**效果**:
- ✅ 使用 `initial_balance: 10000`
- ✅ 使用 `symbol: EURUSD`
- ✅ 只运行 `synthetic` 评估（配置中只有这个是 true）
- ✅ 生成 3000 根 K线

### 场景2：临时覆盖配置

```python
# 临时覆盖某些参数
evaluator = StrategyEvaluator(initial_balance=50000.0)  # 覆盖初始资金

results = evaluator.evaluate_all(
    strategy_code,
    symbol="GBPUSD",              # 临时换品种
    include_historical=True,      # 临时开启历史数据评估
    include_synthetic=True
)
```

**效果**:
- ✅ 使用 $50,000 初始资金（覆盖配置）
- ✅ 测试 GBPUSD（覆盖配置）
- ✅ 运行 synthetic + historical 评估
- ✅ 自动使用 75/25 权重分配

### 场景3：修改配置文件

**步骤1**: 编辑 `config/development.yaml`

```yaml
strategy_evaluation:
  enabled_evaluators:
    synthetic: true
    historical: true     # 改为 true
    realtime: false
    
  weights:
    historical: 0.70     # 调整权重
    synthetic: 0.15
    realtime: 0.15
    
  parameters:
    symbol: "GBPUSD"     # 改为英镑
    synthetic_bars: 5000  # 增加K线数
```

**步骤2**: 重启服务

```bash
./scripts/restart.sh
```

**效果**:
- ✅ 生成策略时自动运行 synthetic + historical 评估
- ✅ 默认品种变为 GBPUSD
- ✅ 合成数据生成 5000 根 K线
- ✅ 权重调整为 70/15/15

## 📊 权重调整建议

### 保守方案（更信任历史数据）

```yaml
weights:
  historical: 0.70  # 提高到 70%
  synthetic: 0.15   # 降到 15%
  realtime: 0.15    # 降到 15%
```

适用于：风险厌恶型，历史数据质量高

### 激进方案（更重视实时表现）

```yaml
weights:
  historical: 0.50  # 降到 50%
  synthetic: 0.20   # 保持 20%
  realtime: 0.30    # 提高到 30%
```

适用于：追求实时适应性，愿意承担波动

### 均衡方案（当前默认）

```yaml
weights:
  historical: 0.60
  synthetic: 0.20
  realtime: 0.20
```

适用于：大多数场景

## 🔍 验证配置

运行测试脚本查看当前配置：

```bash
source venv/bin/activate
python tests/test_config_evaluation.py
```

输出示例：
```
✅ 配置已加载: config/development.yaml

📊 启用的评估器:
  - Synthetic:  True
  - Historical: False
  - Realtime:   False

⚖️  评估权重:
  - historical: 60%
  - synthetic: 20%
  - realtime: 20%

📈 评估参数:
  - 初始资金: $10,000.00
  - 合成数据K线数: 3000
  - 默认品种: EURUSD
```

## ⚙️ 配置优先级

参数解析优先级（从高到低）：

1. **代码中显式传入的参数** → 最高优先级
   ```python
   evaluator.evaluate_all(strategy_code, symbol="GBPUSD")
   # symbol 使用 "GBPUSD"，不管配置文件写什么
   ```

2. **配置文件中的参数** → 中等优先级
   ```yaml
   symbol: "EURUSD"
   # 如果代码中没传 symbol，使用这个
   ```

3. **代码中的硬编码默认值** → 最低优先级
   ```python
   # 仅当配置文件不存在或读取失败时使用
   ```

## 🎯 常见配置场景

### 场景A：开发阶段 - 快速筛选

```yaml
enabled_evaluators:
  synthetic: true      # ✅ 只用合成数据，快速
  historical: false
  realtime: false

parameters:
  synthetic_bars: 1000  # 减少K线，更快
```

### 场景B：准实盘前 - 严格验证

```yaml
enabled_evaluators:
  synthetic: true      # ✅ 快速初筛
  historical: true     # ✅ 真实数据验证
  realtime: false      # ❌ 实盘前再测

weights:
  historical: 0.75     # 历史数据为主
  synthetic: 0.25
  
parameters:
  historical_bars: 5000  # 增加历史数据量
```

### 场景C：实盘前 - 全面测试

```yaml
enabled_evaluators:
  synthetic: true      # ✅ 全开
  historical: true     # ✅ 全开
  realtime: true       # ✅ 最后一关

weights:
  historical: 0.60
  synthetic: 0.20
  realtime: 0.20

parameters:
  realtime_duration_minutes: 120  # 实时测试2小时
```

## 📝 配置文件模板

完整的配置模板参考：

```yaml
# 策略评估配置
strategy_evaluation:
  # 默认启用的评估方式
  enabled_evaluators:
    synthetic: true      # 合成数据评估
    historical: false    # 历史数据评估
    realtime: false      # 实时数据评估

  # 加权平均配置（三种评估都启用时）
  weights:
    historical: 0.60     # 60%
    synthetic: 0.20      # 20%
    realtime: 0.20       # 20%

  # 双评估权重配置
  two_evaluator_weights:
    synthetic_historical:
      historical: 0.75
      synthetic: 0.25
    synthetic_realtime:
      synthetic: 0.60
      realtime: 0.40
    historical_realtime:
      historical: 0.75
      realtime: 0.25

  # 评估参数
  parameters:
    initial_balance: 10000.0
    synthetic_bars: 3000
    historical_bars: 3000
    realtime_duration_minutes: 60
    symbol: "EURUSD"
```

## 🔗 相关文件

- **配置文件**: `config/development.yaml`
- **配置加载器**: `src/common/config/evaluation_config.py`
- **评估器**: `src/services/strategy/evaluator/strategy_evaluator.py`
- **策略生成**: `src/services/strategy/service/generator.py`
- **测试脚本**: `tests/test_config_evaluation.py`

## 🚨 注意事项

1. **修改配置后需要重启服务**
   ```bash
   ./scripts/restart.sh
   ```

2. **权重总和必须为 1.0**
   ```yaml
   weights:
     historical: 0.60
     synthetic: 0.20
     realtime: 0.20
   # 0.60 + 0.20 + 0.20 = 1.0 ✅
   ```

3. **品种代码必须正确**
   ```yaml
   symbol: "EURUSD"  # ✅ 正确
   symbol: "EUR/USD" # ❌ 错误格式
   ```

4. **K线数量建议范围**
   - 最小: 1000 根（至少能算均线）
   - 推荐: 3000 根（平衡速度和准确性）
   - 最大: 10000 根（更准确，但更慢）

---

**最后更新**: 2026-04-10  
**配置版本**: v1.0
