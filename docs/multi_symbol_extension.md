# 多货币对扩展指南

## 📖 概述

当前系统使用**单货币对模式**（默认EURUSD），但架构已预留**多货币对扩展能力**。

**设计原则**: 先简单，后扩展 - Keep it simple, but extensible.

## 🎯 当前实现（V1.0）

### 单货币对模式

```yaml
# config/development.yaml
strategy_evaluation:
  parameters:
    symbol: "EURUSD"  # 默认品种
```

**数据结构**:
```json
{
  "id": "STR_xxx",
  "name": "MA_12x60",
  "performance": {
    "backtested_symbol": "EURUSD",  // 标记回测品种
    "sharpe_ratio": 0.52,
    "win_rate": 0.405,
    "total_return": 5.47,
    // ... 其他22个指标
  }
}
```

**工作流程**:
```
生成策略 → 在EURUSD上回测 → 保存性能指标 → 标记品种 → 实盘使用EURUSD
```

## 🔮 未来扩展（V2.0）

### 多货币对模式

#### 方案A：一个策略，多个Profile

**适用场景**: 同一策略在不同品种上回测对比

```yaml
# config/development.yaml
strategy_evaluation:
  parameters:
    symbols: ["EURUSD", "GBPUSD", "USDJPY"]  # 多品种
    
    symbol_configs:
      EURUSD:
        bars: 3000
        spread: 0.0002
      GBPUSD:
        bars: 3000
        spread: 0.0003
      USDJPY:
        bars: 3000
        spread: 0.0001
```

**数据结构**:
```json
{
  "id": "STR_xxx",
  "name": "MA_12x60",
  "performance": {
    "profiles": {
      "EURUSD": {
        "sharpe_ratio": 0.52,
        "win_rate": 0.405,
        "recommendation_score": 71.3
      },
      "GBPUSD": {
        "sharpe_ratio": 0.35,
        "win_rate": 0.38,
        "recommendation_score": 58.2
      },
      "USDJPY": {
        "sharpe_ratio": 0.61,
        "win_rate": 0.45,
        "recommendation_score": 76.8
      }
    },
    "default_symbol": "EURUSD",
    "best_symbol": "USDJPY"  // 自动推荐表现最好的品种
  }
}
```

**工作流程**:
```
生成策略 → 在3个品种上并行回测 → 保存各品种Profile → Orchestrator根据品种选择
```

#### 方案B：每个品种独立策略

**适用场景**: 不同品种需要不同参数

```python
# 同一个模板，生成多个品种优化的策略
MA_12x60_EURUSD  # 参数针对EURUSD优化
MA_15x50_GBPUSD  # 参数针对GBPUSD优化
MA_10x40_USDJPY  # 参数针对USDJPY优化
```

**数据结构**: 保持当前单品种结构不变

**工作流程**:
```
针对EURUSD生成并优化策略 → 保存
针对GBPUSD生成并优化策略 → 保存
针对USDJPY生成并优化策略 → 保存
```

## 🛠️ 实现指南

### Step 1: 配置扩展（已预留）

```yaml
# config/development.yaml

# 🟢 当前使用（默认）
strategy_evaluation:
  parameters:
    symbol: "EURUSD"

# 🔮 未来启用（取消注释）
# strategy_evaluation:
#   parameters:
#     symbols: ["EURUSD", "GBPUSD", "USDJPY"]
#     symbol_configs:
#       EURUSD:
#         bars: 3000
#         spread: 0.0002
#       GBPUSD:
#         bars: 3000
#         spread: 0.0003
```

### Step 2: 评估器扩展

```python
# src/services/strategy/evaluator/strategy_evaluator.py

def evaluate_all_symbols(self, strategy_code: str, 
                        symbols: List[str]) -> Dict:
    """
    在多个品种上评估策略（未来实现）
    
    Returns:
        {
          "profiles": {
            "EURUSD": {...},
            "GBPUSD": {...},
            "USDJPY": {...}
          }
        }
    """
    profiles = {}
    
    for symbol in symbols:
        print(f"📊 评估品种: {symbol}")
        result = self.evaluate_all(
            strategy_code, 
            symbol=symbol
        )
        profiles[symbol] = result['evaluations'].get('synthetic', {})
    
    return {
        'profiles': profiles,
        'default_symbol': symbols[0],
        'best_symbol': self._find_best_symbol(profiles)
    }

def _find_best_symbol(self, profiles: Dict) -> str:
    """找出表现最好的品种"""
    best_symbol = None
    best_score = 0
    
    for symbol, profile in profiles.items():
        score = profile.get('recommendation_summary', {}).get('recommendation_score', 0)
        if score > best_score:
            best_score = score
            best_symbol = symbol
    
    return best_symbol
```

### Step 3: Generator扩展

```python
# src/services/strategy/service/generator.py

def generate_strategies(self, count: int, template: str = "ma_crossover"):
    """生成策略（支持多货币对）"""
    
    config = get_evaluation_config()
    
    # 检测是单品种还是多品种模式
    if hasattr(config, 'symbols') and len(config.symbols) > 1:
        # 多品种模式
        return self._generate_multi_symbol(count, template, config.symbols)
    else:
        # 单品种模式（当前）
        return self._generate_single_symbol(count, template)

def _generate_multi_symbol(self, count: int, template: str, symbols: List[str]):
    """多品种模式生成（未来实现）"""
    for i in range(count):
        strategy_code = self._generate_code(...)
        
        # 在所有品种上评估
        evaluator = StrategyEvaluator()
        profiles = evaluator.evaluate_all_symbols(strategy_code, symbols)
        
        # 保存多品种Profile
        performance = {
            'profiles': profiles['profiles'],
            'default_symbol': profiles['default_symbol'],
            'best_symbol': profiles['best_symbol']
        }
        
        strategy = Strategy(..., performance=performance)
```

### Step 4: Dashboard扩展

```html
<!-- 多品种选择器 -->
<div x-show="strategy.performance?.profiles">
    <label class="text-xs text-gray-400">查看品种：</label>
    <select x-model="selectedSymbol" class="bg-gray-700 rounded px-2 py-1 text-sm">
        <template x-for="(profile, symbol) in strategy.performance?.profiles">
            <option :value="symbol" x-text="symbol"></option>
        </template>
    </select>
    
    <!-- 显示选中品种的指标 -->
    <div class="mt-2">
        <div class="text-sm">
            Sharpe: <span x-text="strategy.performance?.profiles?.[selectedSymbol]?.sharpe_ratio"></span>
        </div>
        <div class="text-sm">
            推荐度: <span x-text="strategy.performance?.profiles?.[selectedSymbol]?.recommendation_summary?.recommendation_score"></span>分
        </div>
    </div>
</div>
```

### Step 5: Orchestrator扩展

```python
# src/services/orchestrator/service/allocation.py

def allocate_strategies(self, strategies: List[Strategy]):
    """根据品种分配策略"""
    
    allocation = {
        'EURUSD': [],
        'GBPUSD': [],
        'USDJPY': []
    }
    
    for strategy in strategies:
        if 'profiles' in strategy.performance:
            # 多品种策略：选择表现最好的品种
            best_symbol = strategy.performance['best_symbol']
            allocation[best_symbol].append(strategy)
        else:
            # 单品种策略：使用标记的品种
            symbol = strategy.performance.get('backtested_symbol', 'EURUSD')
            allocation[symbol].append(strategy)
    
    return allocation
```

## 📊 品种特性配置

```python
# src/common/config/symbol_configs.py

SYMBOL_CHARACTERISTICS = {
    "EURUSD": {
        "name": "欧元/美元",
        "typical_spread": 0.0002,      # 2点差
        "volatility": "medium",
        "trend_strength": "medium",
        "trading_hours": "24h",
        "recommended_bars": 3000,
        "recommended_strategies": ["trend", "scalping"]
    },
    "GBPUSD": {
        "name": "英镑/美元",
        "typical_spread": 0.0003,
        "volatility": "high",
        "trend_strength": "strong",
        "trading_hours": "24h",
        "recommended_bars": 3000,
        "recommended_strategies": ["trend", "breakout"]
    },
    "USDJPY": {
        "name": "美元/日元",
        "typical_spread": 0.0001,
        "volatility": "medium",
        "trend_strength": "strong",
        "trading_hours": "asia_peak",
        "recommended_bars": 3000,
        "recommended_strategies": ["trend"]
    },
    "XAUUSD": {
        "name": "黄金",
        "typical_spread": 0.0050,
        "volatility": "very_high",
        "trend_strength": "medium",
        "trading_hours": "24h",
        "recommended_bars": 2000,
        "recommended_strategies": ["volatility"]
    }
}
```

## 🎯 迁移路径

### 阶段1：当前状态（已实现）✅

```
- 单品种模式（EURUSD）
- 标记 backtested_symbol
- Dashboard显示品种标签
- 配置预留多品种注释
```

### 阶段2：基础多品种支持

```python
# 启用配置
symbols: ["EURUSD", "GBPUSD"]

# 生成策略时在2个品种上回测
# 保存多个Profile到performance.profiles
```

### 阶段3：品种自动推荐

```python
# 自动找出表现最好的品种
best_symbol = analyze_profiles(profiles)

# Orchestrator自动分配
EURUSD: [策略A, 策略C]
GBPUSD: [策略B, 策略D]
```

### 阶段4：品种自适应优化

```python
# 根据品种特性自动调整策略参数
if symbol == "XAUUSD":
    # 黄金需要更大的止损
    stop_loss *= 2
```

## 📝 数据库兼容性

**当前结构**（V1.0）:
```sql
CREATE TABLE strategies (
    id VARCHAR(32) PRIMARY KEY,
    name VARCHAR(255),
    code TEXT,
    status ENUM('candidate', 'active', 'archived'),
    performance JSON,  -- {"backtested_symbol": "EURUSD", ...}
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

**未来结构**（V2.0 - 完全兼容）:
```sql
-- 表结构不变，只是JSON内容变化
performance JSON  -- {"profiles": {"EURUSD": {...}, ...}}
```

**向后兼容**:
```python
def get_symbol_performance(strategy: Strategy, symbol: str = None):
    """兼容单/多品种数据结构"""
    perf = strategy.performance
    
    # V2.0: 多品种
    if 'profiles' in perf:
        if symbol is None:
            symbol = perf.get('default_symbol', 'EURUSD')
        return perf['profiles'].get(symbol)
    
    # V1.0: 单品种（向后兼容）
    else:
        if symbol is None or symbol == perf.get('backtested_symbol'):
            return perf
        else:
            return None  # 请求的品种没有数据
```

## 🚀 快速启用多品种

**步骤**:

1. 编辑配置文件
```yaml
# config/development.yaml
# 取消注释
symbols: ["EURUSD", "GBPUSD"]
```

2. 实现 `evaluate_all_symbols()`
```python
# 在 strategy_evaluator.py 中添加
```

3. 修改 Generator
```python
# 检测配置，调用多品种评估
```

4. 重启服务
```bash
./scripts/restart.sh
```

## 💡 最佳实践建议

### 当前阶段（V1.0）

✅ **推荐做法**:
- 使用默认EURUSD
- 明确标记回测品种
- 在该品种上实盘

❌ **避免**:
- 在EURUSD上回测，然后在GBPUSD上实盘
- 忽略品种差异，盲目套用

### 扩展阶段（V2.0）

✅ **推荐做法**:
- 先在2-3个主流品种上测试（EURUSD, GBPUSD, USDJPY）
- 对比各品种表现
- Orchestrator根据品种分配策略

❌ **避免**:
- 一次性测试太多品种（增加复杂度）
- 忽略品种特性差异

## 🔗 相关文档

- [配置文件](../config/development.yaml) - 品种配置位置
- [策略模型](../src/common/models/strategy.py) - 数据结构
- [评估器](../src/services/strategy/evaluator/) - 扩展入口
- [配置指南](./config_evaluation_guide.md) - 配置说明

---

**当前版本**: V1.0 - 单品种模式  
**扩展状态**: 架构已预留，配置已注释，随时可启用  
**设计原则**: 先简单（单品种），后扩展（多品种）
