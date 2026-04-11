# MT4 Trading Strategy Factory - 架构设计

## 架构原则

**本项目采用清晰分层、模块化、易维护的架构设计：**

- ✅ **清晰分层**: API层 → Service层 → Repository层，职责明确
- ✅ **分层架构**: 每个服务独立分层，代码结构清晰
- ✅ **模块化**: Common层共享，服务间解耦
- ✅ **易维护**: 单一职责，修改影响范围小
- ✅ **MySQL数据库**: 使用MySQL而非SQLite，满足生产级要求
- ✅ **配置管理**: YAML配置文件，灵活管理不同环境

## 概述

MT4策略工厂是一个自进化的量化交易系统，通过策略的自动生成、评估、变异和淘汰机制，实现策略池的持续优化。系统采用生物进化算法思想，结合机器学习和风险管理，构建一个可自我迭代的交易策略生态系统。

**技术栈**：
- **数据库**: MySQL 8.0（生产级，支持高并发）
- **后端**: Python 3.10+ + FastAPI
- **ORM**: SQLAlchemy 2.0
- **架构**: 微服务 + 分层架构

## 架构演进与优化

### 架构重构：从混合职责到清晰分层

**问题诊断**：
- 当前命名和职责"混在一起"，边界不够清晰
- **registry** 这个名字太弱，承担了策略管理、调度、决策、仓位控制等多重职责
- 后期维护困难，容易变成"上帝模块"

**优化方案：清晰的四层架构**

```
┌─────────────────────────────────────────────────────────────────┐
│  :one: Strategy Layer（策略层）- "想法"                          │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  strategy/                                               │   │
│  │  ├── base.py          # 策略基类                         │   │
│  │  ├── factory.py       # 策略工厂（生成策略）             │   │
│  │  ├── strategies/      # 具体策略实现                     │   │
│  │  │    ├── ma.py                                          │   │
│  │  │    ├── breakout.py                                    │   │
│  │  │    └── ai_model.py                                    │   │
│  │  └── risk/            # 风控计算                         │   │
│  │       ├── position.py                                    │   │
│  │       ├── stop_loss.py                                   │   │
│  │       └── exposure.py                                    │   │
│  └──────────────────────────────────────────────────────────┘   │
│  职责：                                                           │
│  - 生成 signal（buy/sell）                                       │
│  - 风控计算（能不能下单）                                        │
│  - :exclamation: 不直接碰 MT5                                   │
└─────────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────────┐
│  :two: Orchestrator（编排层）- "决策"                           │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  engine/                                                 │   │
│  │  ├── orchestrator.py       # 核心编排器                  │   │
│  │  ├── portfolio_manager.py  # 仓位管理                    │   │
│  │  └── strategy_registry.py  # 策略注册表（子模块）        │   │
│  └──────────────────────────────────────────────────────────┘   │
│  职责：                                                           │
│  - 注册策略（registry 降级为子模块）                             │
│  - 调度策略（决定用哪个策略）                                    │
│  - 决策：下多少仓位、是否允许交易                                │
│  - 管理 portfolio（仓位/资金分配）                               │
│  核心逻辑：                                                       │
│    signal = strategy.generate()                                  │
│    decision = portfolio_manager.evaluate(signal)                 │
│    if decision.approved:                                         │
│        executor.execute(decision)                                │
└─────────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────────┐
│  :three: Execution Layer（执行层）- "执行"                      │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  execution/                                              │   │
│  │  ├── mt5_client.py      # MT5 连接                       │   │
│  │  ├── order_manager.py   # 订单管理                       │   │
│  │  └── account_manager.py # 账户管理                       │   │
│  └──────────────────────────────────────────────────────────┘   │
│  职责：                                                           │
│  - 下单                                                           │
│  - 查询持仓                                                       │
│  - 同步账户状态                                                   │
│  - retry / error handling                                        │
│  :exclamation: 这一层不要有策略逻辑                              │
└─────────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────────┐
│  :four: API Layer（接口层）                                     │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  api/                                                    │   │
│  │  └── routes/                                             │   │
│  │       ├── trade.py                                       │   │
│  │       ├── strategy.py                                    │   │
│  │       └── account.py                                     │   │
│  └──────────────────────────────────────────────────────────┘   │
│  职责：                                                           │
│  - Dashboard                                                     │
│  - 控制开关                                                       │
│  - :exclamation: 不直接触发交易（最好走 queue）                 │
└─────────────────────────────────────────────────────────────────┘
```

### 原有概念的映射关系

| 原有概念 | 新架构 | 说明 |
|---------|--------|------|
| brainstrategy | ❌ 删除 | 太模糊，职责不清 |
| strategy | ✅ strategy | 保留，专注于策略逻辑 |
| factory | ✅ strategy.factory | 保留，负责策略生成 |
| registry | ⚠️ strategy_registry（子模块） | 降级，只负责注册，不再做调度 |
| registry（调度功能） | ✅ orchestrator | 核心引擎，负责调度和决策 |
| 前台 | ✅ execution | 执行层，专门对接 MT5 |

### 核心设计原则

**单一职责**：
- **Strategy**: "想法"（生成信号）
- **Orchestrator**: "决策"（要不要做、做多少）
- **Execution**: "执行"（去下单）

**优势**：
1. **清晰边界**：每一层只干一件事，职责明确
2. **易于测试**：各层可独立测试，降低复杂度
3. **可扩展性**：Strategy 插件化，易于添加新策略
4. **可维护性**：修改影响范围小，避免"上帝模块"
5. **团队协作**：不同层可由不同人维护

**Orchestrator 是"大脑"**：
- 不是 Strategy！
- 负责多策略融合
- 风控最终裁决
- 仓位控制
- 资金分配

## 系统架构图（当前实现 V1）

```
┌─────────────────────────────────────────────────────────────────┐
│                     MT4 Strategy Factory                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────────┐         ┌──────────────────┐              │
│  │  Strategy Core   │────────▶│ Execution Engine │              │
│  │  - Strategy      │         │  - Order Mgmt    │              │
│  │  - Policy        │         │  - Position Mgmt │              │
│  │  - Risk Mgmt     │         │  - MT4 Interface │              │
│  └────────┬─────────┘         └──────────────────┘              │
│           │                                                       │
│           ▼                                                       │
│  ┌──────────────────────────────────────────────────────┐       │
│  │            Portfolio Registry                         │       │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐           │       │
│  │  │ Active   │  │ Candidate│  │ Archived │           │       │
│  │  │Strategies│  │Strategies│  │Strategies│           │       │
│  │  │  └──────────┘  └──────────┘  └──────────┘           │       │
│  └──────────────────────────────────────────────────────┘       │
│           │                                                       │
│           ▼                                                       │
│  ┌──────────────────────────────────────────────────────┐       │
│  │         Evolution Engine                              │       │
│  │  - Mutation      - Allocation    - Decay             │       │
│  │  - Reward        - Auto Kill     - Out-of-Sample     │       │
│  │  - Promote       - Self Learning                     │       │
│  └────────┬─────────────────────────────────────────────┘       │
│           │                                                       │
│           ▼                                                       │
│  ┌──────────────────────────────────────────────────────┐       │
│  │         Data & Analytics Layer                        │       │
│  │  - Market Data   - Performance Metrics               │       │
│  │  - Trade History - Evaluation Engine                 │       │
│  │  - Reports       - Monitoring Dashboard              │       │
│  └──────────────────────────────────────────────────────┘       │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

## 策略 Profile 指标体系

### 完整指标列表

每个策略都会通过真实回测生成完整的 Profile，包含以下指标用于调度中心决策：

#### 📊 核心性能指标
```python
{
    "total_return": 0.0425,        # 总收益率 (4.25%)
    "sharpe_ratio": 0.42,          # Sharpe比率 (风险调整后收益)
    "sortino_ratio": 0.65,         # Sortino比率 (下行风险调整)
    "calmar_ratio": 0.34,          # Calmar比率 (收益/最大回撤)
    "profit_factor": 5.84,         # 盈亏比 (总盈利/总亏损)
    "win_rate": 0.34,              # 胜率 (34%)
    "avg_win": 292.5,              # 平均盈利 ($)
    "avg_loss": 50.0,              # 平均亏损 ($)
    "avg_win_loss_ratio": 5.85,   # 平均盈亏比
    "total_trades": 47             # 总交易数
}
```

#### ⚠️ 风险指标
```python
{
    "risk_type": "aggressive_trend",    # 风险类型
    "risk_score": 6.5,                  # 风险评分 (0-10)
    "risk_level": "high",               # 风险等级 (low/medium/high)
    "max_drawdown": 0.126,              # 最大回撤 (12.6%)
    "avg_drawdown": 0.045,              # 平均回撤 (4.5%)
    "volatility": 0.234,                # 年化波动率 (23.4%)
    "recovery_factor": 0.34             # 回撤恢复因子
}
```

**风险类型分类**：
- `aggressive_trend`: 激进趋势型 (高赔率低胜率)
- `conservative_scalp`: 保守剥头皮 (高胜率低赔率)
- `balanced_stable`: 平衡稳定型 (各项指标均衡)
- `high_risk`: 高风险型 (回撤大)
- `moderate`: 中等型

#### 📈 交易特征指标
```python
{
    "trade_frequency": 1.57,           # 交易频率 (每100根K线1.57笔)
    "avg_holding_time": 64.0,          # 平均持仓时间 (64小时)
    "max_consecutive_wins": 4,         # 最大连续盈利次数
    "max_consecutive_losses": 8        # 最大连续亏损次数
}
```

**交易频率分类**：
- `< 1`: 低频策略 (长线持仓)
- `1-5`: 中频策略 (波段交易)
- `> 5`: 高频策略 (日内交易)

#### 🎯 稳定性指标
```python
{
    "stability_score": 0.65,           # 稳定性评分 (0-1)
    "consistency_score": 0.48          # 一致性评分 (0-1)
}
```

**稳定性计算**：
- 基于交易收益的变异系数
- 越接近1越稳定

**一致性计算**：
- 胜率和盈亏比的均衡性
- 反映策略表现的可预测性

#### 🌐 市场适应性指标
```python
{
    "slippage_sensitivity": "medium",   # 滑点敏感度 (low/medium/high)
    "market_regime": "trend",           # 适应的市场类型 (trend/range)
    "backtest_bars": 3000              # 回测K线数
}
```

**滑点敏感度**：
- `low`: 低频+大盈利，对滑点不敏感
- `medium`: 中等频率，滑点影响中等
- `high`: 高频+小盈利，对滑点极敏感

**市场类型**：
- `trend`: 趋势市场 (Profit Factor > 2)
- `range`: 震荡市场 (Profit Factor < 2)

#### ✅ 策略适用性评估（Suitability Profile）

**最佳实践**：每个策略都包含详细的适用性评估，帮助用户快速判断策略是否适合自己。

```python
{
    "suitability": {
        # 适用投资者类型
        "investor_types": [
            "moderate",      # 稳健型
            "aggressive"     # 进取型
        ],
        
        # 推荐场景
        "recommended_for": [
            "high_return_seekers",        # 追求高收益者
            "low_drawdown_seekers",       # 追求低回撤者
            "strong_mental_endurance"     # 心理承受力强者
        ],
        "not_recommended_for": [
            "stability_seekers",          # 不适合追求稳定者
            "low_risk_tolerance"          # 不适合风险承受力低者
        ],
        
        # 账户要求
        "min_account_size": 5000,           # 最小账户：$5,000
        "suggested_position_size": 0.05,    # 建议仓位：5%
        
        # 适合的市场环境
        "suitable_market_conditions": [
            "strong_trend",              # 强趋势
            "low_volatility_ok"          # 低波动也可用
        ],
        
        # 优势
        "strengths": [
            "exceptional_returns",           # 收益率极高
            "excellent_drawdown_control",    # 回撤控制极佳
            "exceptional_profit_factor"      # 盈亏比极高
        ],
        
        # 劣势
        "weaknesses": [
            "inconsistent_performance",      # 表现不够稳定
            "high_consecutive_loss_risk"     # 连续亏损风险高
        ],
        
        # 注意事项
        "warnings": [
            "可能连续亏损5次，需要强大心理承受力",
            "收益波动较大，不适合追求稳定的投资者"
        ],
        
        # 评分（0-100）
        "scores": {
            "return": 82.5,        # 收益评分
            "risk": 75.0,          # 风险评分
            "stability": 26.0,     # 稳定性评分
            "overall": 65.8        # 综合评分
        },
        
        # 综合推荐
        "recommendation": "recommended",       # 推荐等级
        "recommendation_text": "推荐"          # 推荐文本
    }
}
```

**投资者类型分类**：
- `conservative`: 保守型 (低回撤 + 高Sharpe + 高稳定性)
- `moderate`: 稳健型 (中等回撤 + 中等Sharpe + 胜率>45%)
- `aggressive`: 进取型 (高收益 + 高盈亏比)
- `professional`: 专业型 (Sharpe>1.5 或 高盈亏比+低回撤)
- `general`: 通用型 (不符合以上任何类型)

**推荐等级**：
- `highly_recommended`: 强烈推荐 (综合评分 ≥ 80)
- `recommended`: 推荐 (综合评分 ≥ 65)
- `conditionally_recommended`: 条件推荐 (综合评分 ≥ 50)
- `not_recommended`: 不推荐 (综合评分 < 50)

**综合评分计算**：
```python
overall_score = (
    收益评分 × 40% +      # 收益权重
    风险评分 × 35% +      # 风险权重
    稳定性评分 × 25%      # 稳定性权重
)
```

---

### 指标在调度中心的应用

#### 1. **策略选择**
```python
# 根据当前市场状态选择策略
if current_market == "trending":
    # 选择 market_regime="trend" 的策略
    candidates = [s for s in strategies if s.market_regime == "trend"]
elif current_market == "ranging":
    # 选择高胜率低频的策略
    candidates = [s for s in strategies if s.win_rate > 0.55]
```

#### 2. **仓位分配**
```python
# 根据风险评分分配仓位
if strategy.risk_level == "low":
    position_size = 0.10  # 10%
elif strategy.risk_level == "medium":
    position_size = 0.05  # 5%
else:  # high
    position_size = 0.02  # 2%
```

#### 3. **执行优化**
```python
# 根据滑点敏感度调整订单类型
if strategy.slippage_sensitivity == "high":
    order_type = "LIMIT"  # 限价单
else:
    order_type = "MARKET"  # 市价单
```

#### 4. **风险控制**
```python
# 动态止损
if strategy.risk_score > 7:
    stop_loss = entry_price * (1 - 0.01)  # 1% 止损
elif strategy.risk_score > 4:
    stop_loss = entry_price * (1 - 0.02)  # 2% 止损
else:
    stop_loss = entry_price * (1 - 0.03)  # 3% 止损
```

#### 5. **策略淘汰**
```python
# 自动淘汰表现差的策略
if strategy.sharpe_ratio < 0.3 and strategy.max_drawdown > 0.15:
    archive_strategy(strategy)  # 归档
```

---

### 指标权重表（调度决策）

| 指标 | 权重 | 用途 |
|------|------|------|
| Sharpe Ratio | 25% | 风险调整收益，核心指标 |
| Max Drawdown | 20% | 风险控制，硬性约束 |
| Profit Factor | 15% | 盈利能力 |
| Win Rate | 10% | 稳定性参考 |
| Stability Score | 10% | 长期表现预测 |
| Trade Frequency | 10% | 成本控制 |
| Slippage Sensitivity | 5% | 执行风险 |
| Market Regime | 5% | 市场适配 |

---

## 核心模块

### 1. Strategy Core (策略核心)

#### 1.1 Strategy (策略逻辑)
- **信号生成**: 技术指标、价格模式、市场结构分析
- **入场规则**: 多空条件、过滤器、确认机制
- **出场规则**: 止盈、止损、追踪止损、时间退出
- **参数集**: 策略的可调参数（周期、阈值等）

#### 1.2 Policy (交易策略)
- **仓位策略**: 固定仓位、动态仓位、Kelly公式
- **品种选择**: 交易品种过滤和优先级
- **时间窗口**: 交易时段、会话过滤
- **市场状态**: 趋势/震荡识别、波动率过滤

#### 1.3 Risk Management (风险管理)
- **单笔风险**: 每笔交易的最大损失
- **总体风险**: 账户最大回撤限制
- **相关性控制**: 多策略相关性管理
- **杠杆管理**: 动态杠杆调整
- **极端事件**: 熔断机制、紧急平仓

#### 1.4 Execution (执行)
- **订单类型**: 市价、限价、止损、OCO
- **滑点控制**: 滑点预算、拒绝阈值
- **流动性管理**: 订单分拆、TWAP/VWAP
- **MT4对接**: EA接口、交易服务器通信

### 2. Portfolio Registry (策略注册表)

策略注册表管理所有策略的生命周期，分为三个主要状态：

#### 2.1 Active Strategies (活跃策略)
```json
{
  "strategy_id": "STR_001",
  "status": "active",
  "allocation": 0.15,
  "performance": {
    "sharpe_ratio": 2.3,
    "win_rate": 0.65,
    "profit_factor": 2.1,
    "max_drawdown": 0.08
  },
  "age_days": 45,
  "decay_factor": 0.95,
  "last_mutation": "2026-03-15"
}
```

#### 2.2 Candidate Strategies (候选策略)
- **来源**: 新创建、变异产生、外部导入
- **验证**: 样本外测试、模拟交易
- **晋升条件**: 达到性能阈值后晋升为Active

#### 2.3 Archived Strategies (归档策略)
- **淘汰原因**: 性能衰退、风险超标、自然衰减
- **保留价值**: 用于未来变异、学习参考
- **元数据**: 完整的生命周期数据和性能记录

### 3. Evolution Engine (进化引擎)

#### 3.1 Mutation (变异)
```python
mutation_types = {
    "parameter_tweak": "微调策略参数",
    "indicator_swap": "替换技术指标",
    "rule_modification": "修改入场/出场规则",
    "hybrid_creation": "组合多个策略基因",
    "random_exploration": "随机探索新参数空间"
}
```

**变异策略**:
- 高斯噪声: 参数值 ± N(0, σ)
- 离散突变: 完全替换某个组件
- 交叉遗传: 两个父策略基因重组
- 自适应变异率: 根据种群多样性调整

#### 3.2 Allocation (资金分配)
```
allocation_i = base_allocation * performance_score_i * (1 - decay_i) / Σ(all_active)
```

**分配因子**:
- **Performance Score**: Sharpe比率、收益率、稳定性
- **Decay Factor**: 时间衰减系数
- **Correlation Penalty**: 与其他策略的相关性惩罚
- **Capacity Limit**: 单策略最大资金占比

#### 3.3 Reward (奖励机制)
```python
reward = {
    "profit_reward": realized_pnl * 0.6,
    "risk_adjusted_reward": (return / volatility) * 0.3,
    "stability_bonus": (1 - drawdown) * 0.1,
    "diversification_bonus": (1 - correlation) * 0.05
}
```

#### 3.4 Auto Kill (自动淘汰)
**淘汰触发条件**:
- 回撤超过阈值 (如 -15%)
- Sharpe比率持续低于最低值 (如 < 0.5)
- 连续亏损次数 (如 > 10次)
- 时间衰减至最低分配 (如 < 1%)
- 样本外测试失败

#### 3.5 Promote (晋升机制)
**候选策略晋升流程**:
```
1. In-Sample Testing (样本内测试, 历史回测)
2. Out-of-Sample Testing (样本外测试, 未来数据验证)
3. Paper Trading (模拟交易, 30天)
4. Micro Allocation (小额实盘, 1-2%)
5. Full Promotion (正式晋升, 根据表现分配)
```

**晋升条件**:
- OOS Sharpe > 1.5
- OOS最大回撤 < 12%
- 与现有策略相关性 < 0.7
- 模拟交易通过压力测试

#### 3.6 Decay (时间衰减)
```python
# 指数衰减模型
decay_factor = exp(-λ * age_days)

# 性能加权衰减
adjusted_decay = decay_factor * (1 + performance_bonus)
```

**衰减原理**:
- 防止过拟合: 老策略可能过度适应历史数据
- 鼓励创新: 给新策略更多机会
- 自然淘汰: 表现差的策略自然衰减出局

#### 3.7 Out-of-Sample (OOS) Testing
```
├── Training Set (60%)    : 2020-01-01 to 2023-12-31
├── Validation Set (20%)  : 2024-01-01 to 2024-12-31
└── Test Set (20%)        : 2025-01-01 to 2025-12-31
```

**OOS验证流程**:
- Walk-Forward Analysis: 滚动窗口测试
- Cross-Validation: K折交叉验证
- Regime Testing: 不同市场状态测试
- Stress Testing: 极端行情模拟

### 4. Self-Learning System (自学习系统)

#### 4.1 Data Collection
- 实时市场数据
- 策略执行记录
- 性能指标时序
- 市场状态标签

#### 4.2 Feature Engineering
- 市场微观结构特征
- 策略表现特征
- 宏观环境特征
- 策略组合特征

#### 4.3 Learning Models
```python
learning_components = {
    "regime_classifier": "市场状态分类器 (趋势/震荡/高波动)",
    "strategy_selector": "策略选择器 (动态启用/禁用)",
    "parameter_optimizer": "参数优化器 (在线学习)",
    "risk_predictor": "风险预测器 (预测回撤概率)"
}
```

#### 4.4 Feedback Loop
```
Trade Execution → Performance Data → Learning Model → 
Strategy Adjustment → Trade Execution
```

### 5. Lifecycle Management (生命周期管理)

```
┌─────────────┐
│   Create    │  新策略创建/变异生成
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Backtest   │  历史数据回测
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ OOS Testing │  样本外验证
└──────┬──────┘
       │
       ▼
┌─────────────┐
│Paper Trading│  模拟交易30天
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Active    │  实盘交易 (持续监控)
└──────┬──────┘
       │
       ├─(Good)──▶ Reward & Maintain
       │
       └─(Bad)───▶ Degrade or Kill
                           │
                           ▼
                   ┌─────────────┐
                   │  Archive    │
                   └─────────────┘
```

### 6. Evaluation & Reporting (评估与报告)

#### 6.1 Performance Metrics
```python
metrics = {
    "returns": ["total_return", "annualized_return", "monthly_return"],
    "risk": ["sharpe_ratio", "sortino_ratio", "max_drawdown", "var_95"],
    "efficiency": ["profit_factor", "win_rate", "avg_win_loss_ratio"],
    "consistency": ["calmar_ratio", "stability_index", "tail_risk"]
}
```

#### 6.2 Attribution Analysis
- 策略层级贡献分析
- 品种层级贡献分析
- 时间区间贡献分析
- 风险因子归因

#### 6.3 Report Generation
**日报**:
- 当日PnL汇总
- 策略表现排名
- 风险指标监控
- 异常交易预警

**周报**:
- 策略池变化
- 新策略晋升/淘汰
- 资金分配调整
- 市场状态分析

**月报**:
- 完整性能评估
- 策略进化历史
- 风险报告
- 优化建议

#### 6.4 Monitoring Dashboard
- 实时PnL曲线
- 策略热力图
- 风险仪表盘
- 市场监控
- 交易日志

### 7. Data Architecture (数据架构)

#### 7.1 Market Data
```
market_data/
├── tick/           # Tick级别数据
├── minute/         # 分钟级别数据
├── daily/          # 日线数据
└── fundamental/    # 基本面数据
```

#### 7.2 Strategy Data
```
strategy_data/
├── definitions/    # 策略定义(代码/配置)
├── parameters/     # 参数历史版本
├── performance/    # 性能时序数据
└── trades/         # 交易记录
```

#### 7.3 System Data
```
system_data/
├── registry/       # 策略注册表
├── allocations/    # 资金分配历史
├── events/         # 系统事件日志
└── models/         # 学习模型存档
```

### 8. Risk Controls (风险控制)

#### 8.1 Pre-Trade Controls
- 订单合规检查
- 风险预算检查
- 仓位限制检查
- 策略状态检查

#### 8.2 Real-Time Monitoring
- 实时PnL监控
- 回撤实时跟踪
- 仓位暴露监控
- 异常交易检测

#### 8.3 Post-Trade Analysis
- 交易成本分析
- 滑点分析
- 执行质量评估
- 合规审计

### 9. 技术选型与架构决策 (Technology Decisions)

#### 9.1 核心问题：Python vs MQL5？

**背景**：系统需要 AI 生成策略、回测验证、打分评估，并且只使用 Python 开发。

**决策**：**90% Python + 10% MT5 终端**

#### 9.2 架构分层

```python
┌──────────────────────────────────────────┐
│  AI 策略生成 (Python)                     │
│  - GPT/Claude 生成策略代码                │
│  - LangChain/LlamaIndex                  │
│  - 输出：Python Strategy 类               │
└────────────┬─────────────────────────────┘
             ↓
┌──────────────────────────────────────────┐
│  回测引擎 (Python)                        │
│  - Backtrader / VectorBT                 │
│  - 历史数据测试                           │
│  - 输出：性能指标                         │
└────────────┬─────────────────────────────┘
             ↓
┌──────────────────────────────────────────┐
│  评分&验证 (Python)                       │
│  - 计算 Sharpe, Drawdown                 │
│  - OOS 测试                              │
│  - 决策：晋升 or 淘汰                     │
└────────────┬─────────────────────────────┘
             ↓
┌──────────────────────────────────────────┐
│  Evolution Engine (Python)               │
│  - 变异、淘汰、分配                       │
│  - 策略池管理                            │
└────────────┬─────────────────────────────┘
             ↓
┌──────────────────────────────────────────┐
│  实盘执行 (Python + MT5 库)               │
│  import MetaTrader5 as mt5               │
│  mt5.order_send(...)                     │
└──────────────────────────────────────────┘
```

#### 9.3 技术分工

##### ✅ 全部使用 Python：
- **AI 策略生成**
  - LLM 调用：OpenAI API / Anthropic Claude API
  - 框架：LangChain, LlamaIndex
  - 输出：Python 策略类定义

- **回测与评估**
  - 回测引擎：Backtrader / VectorBT
  - 性能指标：自定义 Python 计算
  - 数据处理：pandas, numpy

- **进化系统**
  - 变异算法：Python 实现
  - 淘汰/晋升逻辑：Python 实现
  - 资金分配：Python 实现

- **自学习系统**
  - 机器学习：scikit-learn, PyTorch
  - 特征工程：pandas, ta-lib
  - 模型训练与预测：Python

##### ⚠️ 使用 MT5 的地方：

**仅用于实盘下单**（通过 Python 库调用）：

```python
import MetaTrader5 as mt5

# 初始化连接到 MT5 终端
if not mt5.initialize():
    print("MT5 初始化失败")
    quit()

# 获取账户信息
account_info = mt5.account_info()
print(f"余额: {account_info.balance}")

# 下单（Python 代码）
symbol = "EURUSD"
lot = 0.1
point = mt5.symbol_info(symbol).point
price = mt5.symbol_info_tick(symbol).ask

# 构造订单请求
request = {
    "action": mt5.TRADE_ACTION_DEAL,
    "symbol": symbol,
    "volume": lot,
    "type": mt5.ORDER_TYPE_BUY,
    "price": price,
    "sl": price - 100 * point,  # 止损
    "tp": price + 200 * point,  # 止盈
    "deviation": 20,
    "magic": 234000,
    "comment": "python strategy",
    "type_time": mt5.ORDER_TIME_GTC,
    "type_filling": mt5.ORDER_FILLING_IOC,
}

# 发送订单
result = mt5.order_send(request)
if result.retcode != mt5.TRADE_RETCODE_DONE:
    print(f"订单失败: {result.comment}")
else:
    print(f"订单成功: Ticket={result.order}")

# 关闭连接
mt5.shutdown()
```

##### ❌ 不需要编写 MQL5 代码

**原因**：
- Python 已经可以通过 `MetaTrader5` 库完成所有操作
- AI 生成的策略直接是 Python 代码，无需转换
- 回测、评估、学习全在 Python 生态完成
- MT5 只作为"经纪商连接通道"

#### 9.4 工作流程

**开发/回测阶段**（纯 Python）：
```
AI 生成策略代码 → Backtrader 回测 → 性能评估 → 
策略打分 → Evolution Engine 变异/淘汰 → 选出优秀策略
```

**实盘交易阶段**（Python + MT5 终端）：
```
1. 启动 MT5 终端（连接经纪商账户）
2. 运行 Python 主程序
3. Python 通过 MetaTrader5 库下单
4. 实时监控、风控、日志全在 Python
```

#### 9.5 为什么不用 MQL5 EA？

| 需求 | MQL5 EA | Python | 结论 |
|------|---------|--------|------|
| AI 生成策略 | ❌ 无 LLM 库 | ✅ OpenAI/Anthropic | Python |
| 回测引擎 | ✅ 内置但不灵活 | ✅ Backtrader/VectorBT | Python |
| 机器学习 | ❌ 几乎无库 | ✅ sklearn/PyTorch | Python |
| Evolution 逻辑 | ❌ 复杂难实现 | ✅ 易实现 | Python |
| 变异算法 | ❌ 困难 | ✅ 简单 | Python |
| 数据分析 | ❌ 弱 | ✅ pandas/numpy | Python |
| 实盘下单 | ✅ 原生 | ✅ mt5 库 | 两者都行 |

**结论**：除了下单，所有功能 Python 都更优。而下单可以用 Python 的 `MetaTrader5` 库完成。

#### 9.6 MT5 平台选择

**MT5 vs MT4**：选择 **MT5**

**原因**（针对策略工厂）：
- ✅ 回测速度快 3-10 倍（多线程）
- ✅ Python 库支持完善（`MetaTrader5`）
- ✅ 优化器更强（遗传算法）
- ✅ 如果未来需要股票/期货，MT5 支持多资产
- ✅ 目标只是外汇货币对，MT5 完全胜任

#### 9.7 关键依赖库

```python
# 核心依赖
dependencies = {
    # MT5 连接
    "MetaTrader5": "^5.0.45",
    
    # 数据处理
    "pandas": "^2.0.0",
    "numpy": "^1.24.0",
    
    # 回测
    "backtrader": "^1.9.78",
    "vectorbt": "^0.26.0",
    
    # 技术指标
    "ta-lib": "^0.4.28",
    "pandas-ta": "^0.3.14",
    
    # 机器学习
    "scikit-learn": "^1.3.0",
    "torch": "^2.0.0",
    
    # AI/LLM
    "openai": "^1.0.0",
    "anthropic": "^0.18.0",
    "langchain": "^0.1.0",
    
    # 数据库
    "sqlalchemy": "^2.0.0",
    "psycopg2": "^2.9.0",
    "redis": "^5.0.0",
    
    # API
    "fastapi": "^0.110.0",
    "uvicorn": "^0.27.0",
    
    # 可视化
    "matplotlib": "^3.8.0",
    "plotly": "^5.18.0",
}
```

#### 9.8 部署架构

```
┌─────────────────────────────────────────┐
│  VPS / Cloud Server (24/7)              │
│  ┌─────────────────────────────────┐   │
│  │  MT5 Terminal (Windows)         │   │
│  │  - 连接经纪商                    │   │
│  │  - 接收 Python 指令              │   │
│  └─────────────────────────────────┘   │
│                                          │
│  ┌─────────────────────────────────┐   │
│  │  Python Main Process            │   │
│  │  - Strategy Factory Core        │   │
│  │  - Evolution Engine             │   │
│  │  - Risk Management              │   │
│  │  - 通过 mt5 库下单               │   │
│  └─────────────────────────────────┘   │
│                                          │
│  ┌─────────────────────────────────┐   │
│  │  PostgreSQL + Redis             │   │
│  │  - 策略数据                      │   │
│  │  - 交易记录                      │   │
│  │  - 实时状态                      │   │
│  └─────────────────────────────────┘   │
└─────────────────────────────────────────┘
```

**部署要求**：
- **OS**: Windows (MT5 需要)，或 Windows VPS
- **Python**: 3.10+
- **内存**: 最少 8GB（推荐 16GB）
- **网络**: 稳定低延迟连接到经纪商服务器

### 10. Technology Stack (技术栈)

```python
tech_stack = {
    # 核心平台
    "platform": "MT5 (MetaTrader 5)",
    "language": "Python 3.10+",
    
    # 执行层
    "execution": "MetaTrader5 Python Library",
    
    # 策略引擎
    "strategy_engine": "Python (Custom Framework)",
    "ai_generation": "OpenAI API / Anthropic Claude API + LangChain",
    
    # 回测与评估
    "backtesting": "Backtrader / VectorBT",
    "indicators": "ta-lib, pandas-ta",
    
    # 进化系统
    "evolution": "Python (Custom Genetic Algorithm)",
    
    # 机器学习
    "ml_framework": "scikit-learn, PyTorch",
    "feature_engineering": "pandas, numpy",
    
    # 数据存储
    "database": "PostgreSQL (Trades, Performance) + TimescaleDB (Time Series)",
    "cache": "Redis (Real-time State, Strategy Registry)",
    "message_queue": "RabbitMQ (Event Streaming) [可选]",
    
    # 监控与可视化
    "monitoring": "Grafana + Prometheus",
    "visualization": "Plotly, Matplotlib",
    
    # API 服务
    "api": "FastAPI + Uvicorn",
    "async": "asyncio, aiohttp",
    
    # 开发工具
    "testing": "pytest",
    "linting": "ruff, mypy",
    "version_control": "git",
}
```

### 10. Implementation Roadmap (实施路线图)

**Phase 1: Foundation (基础架构)**
- [ ] 数据管道搭建
- [ ] MT4执行引擎
- [ ] 策略框架设计
- [ ] 基础风险管理

**Phase 2: Core System (核心系统)**
- [ ] Portfolio Registry实现
- [ ] 性能评估引擎
- [ ] 报告系统
- [ ] 监控Dashboard

**Phase 3: Evolution (进化系统)**
- [ ] 变异引擎
- [ ] 淘汰/晋升机制
- [ ] 资金分配算法
- [ ] 时间衰减模型

**Phase 4: Intelligence (智能系统)**
- [ ] 自学习模型
- [ ] 市场状态分类
- [ ] 参数自优化
- [ ] 策略自动生成

**Phase 5: Production (生产化)**
- [ ] 高可用架构
- [ ] 灾备方案
- [ ] 性能优化
- [ ] 完整测试覆盖

## 配置示例

### Strategy Configuration
```yaml
strategy:
  id: STR_MA_CROSS_001
  name: "MA Crossover with Volume Filter"
  type: trend_following
  
  parameters:
    fast_period: 10
    slow_period: 30
    volume_threshold: 1.5
    
  entry_rules:
    - type: ma_cross
      direction: long
      confirmation: volume_spike
      
  exit_rules:
    - type: take_profit
      value: 2.0  # Risk-Reward Ratio
    - type: stop_loss
      value: 1.0
    - type: trailing_stop
      activation: 1.5
      distance: 0.5
      
  risk:
    max_position_pct: 0.02  # 2% per trade
    max_daily_loss: 0.05     # 5% daily limit
    
  execution:
    symbols: ["EURUSD", "GBPUSD"]
    timeframe: "H1"
    trading_hours: "08:00-20:00"
```

### Evolution Configuration
```yaml
evolution:
  mutation:
    rate: 0.15
    types:
      - parameter_tweak: 0.5
      - indicator_swap: 0.2
      - rule_modification: 0.2
      - hybrid_creation: 0.1
      
  selection:
    method: tournament
    elite_ratio: 0.1
    
  decay:
    lambda: 0.001  # daily decay rate
    min_allocation: 0.01
    
  promotion:
    oos_min_sharpe: 1.5
    oos_max_dd: 0.12
    paper_trading_days: 30
    min_correlation_threshold: 0.7
```

## 关键设计原则

1. **防过拟合**: 严格的OOS测试，时间衰减机制
2. **多样性**: 鼓励策略差异化，相关性惩罚
3. **自适应**: 根据市场状态动态调整策略池
4. **风险优先**: 风险控制始终是第一优先级
5. **可解释性**: 策略逻辑清晰，决策可追溯
6. **容错性**: 单个策略失败不影响系统整体
7. **可扩展**: 模块化设计，易于添加新策略类型

## 附录

### A. 术语表
- **Sharpe Ratio**: 风险调整后收益 = (收益率 - 无风险利率) / 波动率
- **Max Drawdown**: 从峰值到谷底的最大回撤百分比
- **Profit Factor**: 总盈利 / 总亏损
- **Kelly Criterion**: 最优仓位计算公式
- **Walk-Forward**: 滚动时间窗口的回测方法

### B. 参考资料
- 《Quantitative Trading》- Ernest Chan
- 《Advances in Financial Machine Learning》- Marcos López de Prado
- 《Evidence-Based Technical Analysis》- David Aronson

---

**版本**: 1.0  
**最后更新**: 2026-04-09  
**维护者**: Frank Zhang
