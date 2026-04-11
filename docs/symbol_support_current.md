# 货币对支持 - 当前实现

## 📊 现状

**模式**: 单货币对（Default）  
**品种**: EURUSD（欧元/美元）  
**扩展性**: ✅ 已预留架构

## 🎯 当前功能

### 1. 默认使用EURUSD

```yaml
# config/development.yaml
strategy_evaluation:
  parameters:
    symbol: "EURUSD"  # 默认品种
```

所有生成的策略默认在EURUSD上回测。

### 2. 自动标记回测品种

```json
{
  "id": "STR_xxx",
  "name": "MA_12x60",
  "performance": {
    "backtested_symbol": "EURUSD",  // ✅ 新增字段
    "sharpe_ratio": 0.52,
    "win_rate": 0.405,
    // ... 其他指标
  }
}
```

每个策略的performance中都会记录回测使用的品种。

### 3. Dashboard显示品种

策略卡片右上角显示品种标签：

```
MA_12x60
STR_xxx

candidate  aggressive_trend  EURUSD
                             ^^^^^^
                             品种标签
```

紫色标签显示该策略是在哪个品种上回测的。

## 🔧 使用方法

### 方法1：使用默认（推荐）

什么都不用改，直接使用EURUSD。

```python
# 系统自动：
# 1. 在EURUSD上回测
# 2. 标记 backtested_symbol: "EURUSD"
# 3. 实盘时在EURUSD上使用
```

### 方法2：临时换品种

```python
# 在代码中临时指定
evaluator = StrategyEvaluator()
result = evaluator.evaluate_all(strategy_code, symbol="GBPUSD")

# 会自动标记 backtested_symbol: "GBPUSD"
```

### 方法3：修改配置文件

```yaml
# config/development.yaml
strategy_evaluation:
  parameters:
    symbol: "GBPUSD"  # 改为英镑
```

重启服务后，所有新生成的策略都在GBPUSD上回测。

## ⚠️ 重要提示

### 换品种必须重新回测

**错误做法** ❌:
```python
# 在EURUSD上回测
strategy = generate_strategy()  # backtested_symbol: "EURUSD"

# 然后在GBPUSD上实盘使用 ← 错误！
trade_on_symbol(strategy, "GBPUSD")  # 指标可能不准确
```

**正确做法** ✅:
```python
# 方案A：使用回测品种
strategy = generate_strategy()  # backtested_symbol: "EURUSD"
trade_on_symbol(strategy, "EURUSD")  # ✅ 使用回测品种

# 方案B：想用GBPUSD就重新回测
strategy = generate_strategy(symbol="GBPUSD")  # 在GBPUSD上回测
trade_on_symbol(strategy, "GBPUSD")  # ✅ 匹配
```

### 为什么不能直接套用？

同一个策略在不同品种上表现差异很大：

| 策略 | EURUSD | GBPUSD | 差异原因 |
|------|--------|--------|---------|
| MA_12x60 | Sharpe 0.52 | Sharpe 0.35 | GBPUSD波动更大 |
| MA_12x60 | 胜率 40.5% | 胜率 38% | GBPUSD假突破更多 |
| MA_12x60 | 回撤 4.3% | 回撤 8.2% | GBPUSD更剧烈 |

## 🔮 未来扩展

### 已预留的扩展点

1. **配置文件** - 已添加多品种注释
```yaml
# 🔮 未来扩展：多货币对支持
# symbols: ["EURUSD", "GBPUSD", "USDJPY"]
```

2. **数据结构** - JSON字段支持多品种
```python
# 当前：单品种
{"backtested_symbol": "EURUSD", ...}

# 未来：多品种
{"profiles": {"EURUSD": {...}, "GBPUSD": {...}}}
```

3. **代码注释** - 关键位置都有扩展说明

### 启用多品种只需3步

```bash
# 1. 取消配置注释
symbols: ["EURUSD", "GBPUSD"]

# 2. 实现 evaluate_all_symbols() 方法

# 3. 重启服务
./scripts/restart.sh
```

详见：[多货币对扩展指南](./multi_symbol_extension.md)

## 📝 快速参考

### 支持的品种

理论上任何MetaTrader 5支持的品种都可以：

**主流货币对**:
- EURUSD（欧元/美元）✅ 推荐
- GBPUSD（英镑/美元）
- USDJPY（美元/日元）
- AUDUSD（澳元/美元）
- USDCHF（美元/瑞郎）
- USDCAD（美元/加元）

**商品**:
- XAUUSD（黄金）
- XAGUSD（白银）
- USOIL（原油）

**加密货币**（如果经纪商支持）:
- BTCUSD（比特币）
- ETHUSD（以太坊）

### 品种推荐

| 用途 | 推荐品种 | 原因 |
|------|---------|------|
| 🥇 首选 | **EURUSD** | 流动性最好、点差最小、最稳定 |
| 🥈 扩展 | GBPUSD, USDJPY | 主流品种，数据充足 |
| 🥉 进阶 | AUDUSD, XAUUSD | 特殊特性，需要调整 |
| ⚠️ 谨慎 | BTCUSD等加密货币 | 波动巨大，风险极高 |

## 🔗 相关文档

- [多货币对扩展指南](./multi_symbol_extension.md) - 详细扩展方案
- [配置文件](../config/development.yaml) - 品种配置
- [评估配置指南](./config_evaluation_guide.md) - 完整配置说明

---

**当前版本**: V1.0  
**品种模式**: 单品种（EURUSD）  
**扩展就绪**: ✅ 随时可启用多品种
