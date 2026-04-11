# 策略适用性评估 - 完整示例

## 示例：MA_12x60 策略

### 📊 基础性能指标
```json
{
  "name": "MA_12x60",
  "status": "candidate",
  "total_return": 2.0732,        // 207.32% 收益
  "sharpe_ratio": 0.42,
  "win_rate": 0.50,              // 50% 胜率
  "profit_factor": 12.8,         // 12.8 盈亏比
  "max_drawdown": 0.048,         // 4.8% 最大回撤
  "volatility": 0.146,           // 14.6% 年化波动率
  "stability_score": 0.26,       // 26% 稳定性
  "risk_type": "moderate",
  "risk_level": "low",
  "risk_score": 2.5
}
```

---

## ✅ 策略适用性评估（完整字段）

### 1. 综合评分

```json
{
  "scores": {
    "return": 82.5,        // 收益评分（基于207%收益）
    "risk": 75.0,          // 风险评分（基于风险评分2.5/10）
    "stability": 26.0,     // 稳定性评分
    "overall": 65.8        // 综合评分 = return×40% + risk×35% + stability×25%
  },
  "recommendation": "recommended",
  "recommendation_text": "推荐"
}
```

**评分解读**：
- **收益评分 82.5**：收益率极高（207%）
- **风险评分 75.0**：风险可控（风险评分仅2.5/10）
- **稳定性评分 26.0**：稳定性较低（波动大）
- **综合评分 65.8**：整体推荐使用

---

### 2. 适用投资者类型

```json
{
  "investor_types": [
    "moderate",      // 稳健型：回撤<12% + Sharpe>0.6 + 胜率>45% ✅
    "aggressive",    // 进取型：收益>15% + 盈亏比>3 ✅
    "professional"   // 专业型：盈亏比>5 + 回撤<10% ✅
  ]
}
```

**匹配逻辑**：
```python
if max_dd < 0.12 and sharpe > 0.6 and win_rate > 0.45:
    ✅ 稳健型

if total_return > 0.15 and profit_factor > 3:
    ✅ 进取型

if profit_factor > 5 and max_dd < 0.10:
    ✅ 专业型
```

**解读**：
- ✅ **稳健型**：回撤4.8%，控制得很好
- ✅ **进取型**：收益207%，盈亏比12.8
- ✅ **专业型**：盈亏比12.8且回撤4.8%，专业级表现
- ❌ **保守型**：Sharpe 0.42偏低，不符合

---

### 3. 推荐场景

```json
{
  "recommended_for": [
    "high_return_seekers",        // 追求高收益 ✅
    "low_drawdown_seekers",       // 追求低回撤 ✅
    "strong_mental_endurance"     // 心理承受力强 ✅
  ],
  "not_recommended_for": [
    "stability_seekers"           // 不适合追求稳定者 ❌
  ]
}
```

**推荐给**：
- ✅ **高收益追求者**：207%收益
- ✅ **低回撤追求者**：4.8%最大回撤
- ✅ **心理承受力强者**：可能连续亏损5次

**不推荐给**：
- ❌ **稳定性追求者**：稳定性26%，收益波动大

---

### 4. 账户要求

```json
{
  "min_account_size": 5000,          // 最小账户：$5,000
  "suggested_position_size": 0.05    // 建议仓位：5%
}
```

**计算逻辑**：
```python
# 根据风险等级确定
if risk_level == 'high':
    min_account = 10000
    position = 0.02  # 2%
elif risk_level == 'medium':
    min_account = 5000
    position = 0.05  # 5%
else:  # low ✅
    min_account = 3000
    position = 0.10  # 10%

# 但由于稳定性低，下调仓位
# 实际建议：5%
```

**实际应用**：
```
$5,000账户：
- 每笔风险：$5,000 × 5% = $250
- 平均亏损：$76
- 风险余量充足 ✅

$10,000账户：
- 每笔风险：$10,000 × 5% = $500
- 平均亏损：$76
- 更加安全 ✅✅
```

---

### 5. 适合的市场环境

```json
{
  "suitable_market_conditions": [
    "strong_trend",          // 强趋势 ✅
    "low_volatility_ok"      // 低波动也可用 ✅
  ]
}
```

**判断逻辑**：
```python
if profit_factor > 3:
    ✅ strong_trend  # 盈亏比12.8，明显适合趋势

if trade_freq < 2:
    ✅ low_volatility_ok  # 交易频率1.6，不依赖高波动
```

**使用建议**：
- ✅ **EURUSD 单边上涨/下跌**：最佳场景
- ✅ **GBPUSD 突破行情**：适合
- ⚠️ **震荡整理**：可能频繁止损

---

### 6. 策略优势

```json
{
  "strengths": [
    "exceptional_returns",           // 收益率极高 ✅
    "excellent_drawdown_control",    // 回撤控制极佳 ✅
    "exceptional_profit_factor"      // 盈亏比极高 ✅
  ]
}
```

**判断标准**：
```python
if total_return > 0.50:
    ✅ exceptional_returns  # 207% > 50%

if max_dd < 0.08:
    ✅ excellent_drawdown_control  # 4.8% < 8%

if profit_factor > 5:
    ✅ exceptional_profit_factor  # 12.8 > 5
```

---

### 7. 策略劣势

```json
{
  "weaknesses": [
    "inconsistent_performance",      // 表现不够稳定 ⚠️
    "high_consecutive_loss_risk"     // 连续亏损风险高 ⚠️
  ]
}
```

**判断标准**：
```python
if stability < 0.5:
    ⚠️ inconsistent_performance  # 26% < 50%

if max_consec_loss > 5:
    ⚠️ high_consecutive_loss_risk  # 5次连续亏损
```

---

### 8. 重要提示

```json
{
  "warnings": [
    "可能连续亏损5次，需要强大心理承受力",
    "收益波动较大，不适合追求稳定的投资者"
  ]
}
```

**触发条件**：
```python
if max_consec_loss > 5:
    ⚠️ "可能连续亏损{N}次，需要强大心理承受力"

if stability < 0.4:
    ⚠️ "收益波动较大，不适合追求稳定的投资者"

if trade_freq < 1:
    ⚠️ "交易频率低，需要耐心等待信号"

if max_dd > 0.15:
    ⚠️ "最大回撤{X}%，风险较高"
```

---

## 🎯 使用建议矩阵

| 场景 | 是否适合 | 理由 |
|------|----------|------|
| **追求高收益** | ✅✅✅ | 207%收益，极高 |
| **追求低回撤** | ✅✅✅ | 4.8%回撤，极低 |
| **追求稳定性** | ❌ | 26%稳定性，波动大 |
| **新手投资者** | ⚠️ | 需要承受连续亏损 |
| **经验投资者** | ✅✅ | 能理解策略逻辑 |
| **$3,000账户** | ⚠️ | 偏小，建议$5,000+ |
| **$5,000账户** | ✅ | 合适 |
| **$10,000+账户** | ✅✅ | 最佳 |
| **趋势市场** | ✅✅✅ | 最适合 |
| **震荡市场** | ❌ | 不适合 |
| **日内交易** | ❌ | 持仓60小时，非日内 |
| **波段交易** | ✅✅ | 完全匹配 |
| **长线投资** | ⚠️ | 频率偏高 |

---

## 📋 快速判断流程

### Step 1：看综合评分
```
≥ 80分 → 强烈推荐 ✅✅✅
≥ 65分 → 推荐 ✅✅        ← 你在这里（65.8分）
≥ 50分 → 条件推荐 ⚠️
< 50分 → 不推荐 ❌
```

### Step 2：看投资者类型
```
你是哪种投资者？
- 保守型 → ❌ 不在列表
- 稳健型 → ✅ 在列表
- 进取型 → ✅ 在列表
- 专业型 → ✅ 在列表
```

### Step 3：看账户规模
```
你的账户规模？
- < $5,000 → ⚠️ 偏小
- ≥ $5,000 → ✅ 合适
```

### Step 4：看优势是否匹配你的需求
```
你的需求          策略优势          匹配度
高收益   vs   exceptional_returns   ✅✅✅
低回撤   vs   excellent_drawdown    ✅✅✅
高稳定   vs   ❌ 稳定性26%          ❌
```

### Step 5：看劣势你能否接受
```
策略劣势                     你能接受吗？
不够稳定（26%）        →    可以 / 不可以
可能连续亏损5次        →    可以 / 不可以
```

---

## 💡 最终建议模板

### 如果你是**稳健型投资者**，账户**$5,000-$10,000**：

✅ **建议使用**

**配置**：
- 仓位：5%
- 止损：严格执行
- 市场：等待趋势明确

**预期**：
- 年化收益：50-100%（回测207%可能偏高）
- 最大回撤：5-8%
- 心理准备：连续5次小亏

**监控指标**：
- 实盘回撤超过10% → 停止使用
- 连续亏损超过7次 → 暂停观察
- 盈亏比低于5 → 检查策略是否失效

---

**这个完整的适用性评估，让策略选择从"盲选"变成"精准匹配"！** 🎯
