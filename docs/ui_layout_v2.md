# Dashboard UI 布局优化 V2

## 📊 改进概览

优化策略卡片布局，简化默认视图，便于 Orchestrator 进行策略配比。

## 🎯 设计原则

1. **简洁默认视图** - 只显示最关键信息
2. **详细Profile可展开** - 所有指标统一折叠
3. **避免信息重复** - 推荐度只在顶部显示一次
4. **便于配比决策** - Profile指标完整展示，方便Orchestrator

## 📐 新布局结构

### 默认显示（折叠状态）

```
┌─────────────────────────────────────────────────────────┐
│ MA_19x54                    candidate   aggressive_trend │
│ STR_18e93ee6                                             │
│                                          ✅ 推荐度       │
│                                          71.3分          │
│                                          ████████░░ 71%  │
├─────────────────────────────────────────────────────────┤
│ 📊 详细指标 (Profile)            ▶                       │
│ ✅ 策略适用性评估                 ▶                       │
│ 📄 查看策略代码                   ▶                       │
└─────────────────────────────────────────────────────────┘
```

**默认显示内容**:
- 策略名称 (MA_19x54)
- 策略ID (STR_18e93ee6)
- 状态标签 (candidate)
- 风险类型标签 (aggressive_trend)
- **右上角推荐度能量槽** (✅ 71.3分 + 进度条)

### 展开"📊 详细指标 (Profile)"

点击后显示 **所有性能指标**，分为四个部分：

#### 1. 核心指标
```
总收益      Sharpe     胜率       盈亏比     交易数
547.38%     0.52      40.5%      14.1       37
```

#### 2. 风险指标
```
风险评分    最大回撤    平均回撤    波动率     Sortino
3/10       4.3%      1.5%      19.7%     0.89
```

#### 3. 交易特征
```
交易频率        持仓时间    平均盈利    平均亏损    盈亏比
1.3/100笔      78h        $3928      $190       20.68
```

#### 4. 稳定性与适应性
```
稳定性    一致性    滑点敏感度    市场类型    连续胜/负
27%      81%      low         trend     3 / 4
```

**重要性**: 这些指标是 Orchestrator 进行策略配比的依据。

### 展开"✅ 策略适用性评估"

点击后显示 **适用性详情**：

```
高收益低回撤的优质策略，适合追求稳健高回报的投资者

✅ 适合：进取型, 专业型
💰 要求：最小$3,000，建议仓位10%
✅ 优势：收益极高, 回撤极低, 盈亏比极高
⚠️ 劣势：不够稳定
⚠️ 提示：收益波动较大
```

**注意**: 推荐度分数不在这里重复显示（已在右上角）

## 🔄 对比：旧版 vs 新版

| 特性 | 旧版布局 | 新版布局 | 改进 |
|------|---------|---------|------|
| **推荐度显示** | 两处（顶部+评估卡片） | 一处（右上角） | ✅ 避免重复 |
| **详细指标** | 4个独立折叠块 | 1个统一折叠块 | ✅ 简化结构 |
| **默认视图** | 显示部分指标 | 只显示关键信息 | ✅ 更简洁 |
| **Profile可见性** | 分散在各处 | 集中在一起 | ✅ 便于配比 |
| **适用性信息** | 混在指标中 | 独立折叠 | ✅ 更清晰 |

## 🎯 使用场景

### 场景1：快速浏览策略

**目标**: 从多个策略中快速筛选

**操作**: 
1. 看策略名称和ID
2. 看状态标签（candidate/active）
3. 看风险类型标签（aggressive_trend/conservative等）
4. **看右上角推荐度** (一眼看出71.3分)

**结果**: 无需展开任何内容，即可判断是否值得深入研究

### 场景2：Orchestrator 策略配比

**目标**: 根据不同策略特征进行组合配置

**需求**: 
- 稳健型组合：需要低波动、高稳定性的策略
- 风险型组合：可以容忍高波动、追求高收益
- 胜率导向：优先选择高胜率策略

**操作**:
1. 展开"📊 详细指标 (Profile)"
2. 查看**稳定性与适应性**部分
   - 稳定性27% → 波动大
   - 一致性81% → 比较稳定
   - 滑点敏感度low → 适合高频
   - 市场类型trend → 趋势策略
3. 查看**风险指标**
   - 最大回撤4.3% → 低回撤
   - 波动率19.7% → 中等波动
4. 查看**核心指标**
   - 胜率40.5% → 低胜率
   - 盈亏比14.1 → 超高盈亏比

**结论**: 
- ✅ 适合风险型组合（高收益+低回撤）
- ❌ 不适合稳健型组合（稳定性低27%）
- ❌ 不适合胜率导向（胜率仅40.5%）
- ✅ 适合趋势型组合（market_regime=trend）

### 场景3：了解策略适用性

**目标**: 判断策略是否适合自己的投资风格

**操作**:
1. 展开"✅ 策略适用性评估"
2. 查看"适合"字段 → 进取型, 专业型
3. 查看"要求"字段 → 最小$3,000，建议仓位10%
4. 查看"优势"和"劣势"
5. 查看"提示"了解风险

**结果**: 快速判断是否匹配自己的风险承受能力

## 🛠️ 技术实现

### 统一折叠块结构

```html
<details class="mb-3">
    <summary class="cursor-pointer text-blue-400 text-sm font-semibold">
        📊 详细指标 (Profile)
    </summary>
    <div class="mt-3 space-y-4">
        <!-- 核心指标 -->
        <div>
            <h4 class="text-xs text-blue-300 font-semibold mb-2">核心指标</h4>
            <div class="grid grid-cols-2 md:grid-cols-5 gap-3">
                <!-- 指标内容 -->
            </div>
        </div>
        
        <!-- 风险指标 -->
        <div>...</div>
        
        <!-- 交易特征 -->
        <div>...</div>
        
        <!-- 稳定性与适应性 -->
        <div>...</div>
    </div>
</details>
```

### 推荐度能量槽（右上角）

```html
<div class="flex flex-col items-end gap-2">
    <!-- Status Badges -->
    <div class="flex gap-2">
        <span>candidate</span>
        <span>aggressive_trend</span>
    </div>
    
    <!-- Energy Bar -->
    <div class="w-56">
        <div class="flex items-center justify-between mb-1.5">
            <span>✅ 推荐度</span>
            <span class="font-bold">71.3分</span>
        </div>
        <div class="bg-gray-900 rounded-full h-3">
            <div class="rounded-full bg-gradient-to-r from-blue-600 to-blue-400"
                 style="width: 71.3%">
                <!-- Glow effect -->
            </div>
        </div>
    </div>
</div>
```

## 📊 数据流

### Profile数据来源

所有Profile指标来自于 `strategy.performance` 对象：

```javascript
{
  // 核心指标
  "total_return": 5.4738,
  "sharpe_ratio": 0.52,
  "win_rate": 0.405,
  "profit_factor": 14.1,
  "total_trades": 37,
  
  // 风险指标
  "risk_score": 3,
  "max_drawdown": 0.043,
  "avg_drawdown": 0.015,
  "volatility": 0.197,
  "sortino_ratio": 0.89,
  
  // 交易特征
  "trade_frequency": 1.3,
  "avg_holding_time": 78,
  "avg_win": 3928,
  "avg_loss": 190,
  "avg_win_loss_ratio": 20.68,
  
  // 稳定性与适应性
  "stability_score": 0.27,
  "consistency_score": 0.81,
  "slippage_sensitivity": "low",
  "market_regime": "trend",
  "max_consecutive_wins": 3,
  "max_consecutive_losses": 4,
  
  // 推荐摘要
  "recommendation_summary": {
    "recommendation_score": 71.3,
    "recommendation_text": "推荐",
    "recommendation_emoji": "✅",
    "suitable_for": "进取型, 专业型",
    "account_requirement": "最小$3,000，建议仓位10%",
    "key_strengths": "收益极高, 回撤极低, 盈亏比极高",
    "key_weaknesses": "不够稳定",
    "key_warnings": "收益波动较大",
    "one_line_summary": "高收益低回撤的优质策略..."
  }
}
```

## 🎯 Orchestrator 配比示例

### 示例1：构建稳健型组合

**目标**: 低波动、高稳定性、控制回撤

**筛选标准**:
```python
stability_score > 0.60        # 稳定性 > 60%
max_drawdown < 0.08           # 最大回撤 < 8%
volatility < 0.15             # 波动率 < 15%
sharpe_ratio > 1.0            # Sharpe > 1.0
```

**当前策略匹配度**:
- ❌ stability_score = 0.27 (不满足)
- ✅ max_drawdown = 0.043 (满足)
- ❌ volatility = 0.197 (不满足)
- ❌ sharpe_ratio = 0.52 (不满足)

**结论**: 不适合稳健型组合

### 示例2：构建进取型组合

**目标**: 高收益、容忍波动、追求趋势

**筛选标准**:
```python
total_return > 0.30           # 总收益 > 30%
profit_factor > 3             # 盈亏比 > 3
market_regime == 'trend'      # 趋势策略
max_drawdown < 0.10           # 控制回撤 < 10%
```

**当前策略匹配度**:
- ✅ total_return = 5.47 (满足)
- ✅ profit_factor = 14.1 (满足)
- ✅ market_regime = 'trend' (满足)
- ✅ max_drawdown = 0.043 (满足)

**结论**: ✅ 完美匹配进取型组合

### 示例3：构建胜率导向组合

**目标**: 高胜率、稳定盈利、降低心理压力

**筛选标准**:
```python
win_rate > 0.55               # 胜率 > 55%
consistency_score > 0.70      # 一致性 > 70%
max_consecutive_losses < 5    # 连续亏损 < 5次
```

**当前策略匹配度**:
- ❌ win_rate = 0.405 (不满足)
- ✅ consistency_score = 0.81 (满足)
- ✅ max_consecutive_losses = 4 (满足)

**结论**: 不适合胜率导向组合（胜率过低）

## ✅ 优化效果

1. **信息密度降低** - 默认视图更简洁，聚焦关键信息
2. **推荐度突出** - 右上角能量槽一目了然
3. **Profile完整** - 所有指标集中展示，便于配比决策
4. **避免重复** - 推荐度分数只显示一次
5. **结构清晰** - 详细指标、适用性评估、策略代码三个独立折叠

## 🔗 相关文档

- [策略Profile指标体系](../ARCHITECTURE.md#策略-profile-指标体系)
- [策略适用性评估](./strategy_suitability_example.md)
- [Dashboard API](../src/services/dashboard/README.md)

---

**更新日期**: 2026-04-10  
**版本**: V2.0  
**设计目标**: 简化视图，强化Profile，便于Orchestrator配比
