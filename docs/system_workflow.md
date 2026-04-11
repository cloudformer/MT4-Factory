# 系统完整工作流程

## 📖 概述

本文档描述EvoTrade系统从策略生成到最终执行的完整工作流程。

## 🔄 完整流程图

```
┌─────────────────────────────────────────────────────────────┐
│  Phase 1: 策略生成（Strategy Generation）                    │
│  - 黑盒生成，算法不限                                          │
│  - 大量生成（批量）                                            │
│  - 不同算法（MA、RSI、MACD...）                               │
│  - 参数随机优化                                               │
└─────────────────┬───────────────────────────────────────────┘
                  ↓
         生成策略代码（Python）
         状态：CANDIDATE
                  ↓
┌─────────────────────────────────────────────────────────────┐
│  Phase 2: 策略评估（Strategy Evaluation）                    │
│  三种评估方式，加权平均                                         │
├─────────────────────────────────────────────────────────────┤
│  2.1 模拟数据评估（Synthetic）- 默认启用                       │
│      - 生成合成K线数据                                         │
│      - 快速回测                                               │
│      - 权重：20%（当全部启用时）                               │
├─────────────────────────────────────────────────────────────┤
│  2.2 历史数据评估（Historical）- 按需启用                      │
│      - 使用真实历史K线                                         │
│      - 最可靠的评估                                            │
│      - 权重：60%（当全部启用时）                               │
├─────────────────────────────────────────────────────────────┤
│  2.3 实时数据评估（Realtime）- 按需启用                        │
│      - 跟盘测试（纸面交易）                                     │
│      - 只测试已注册（激活）的策略                               │
│      - 权重：20%（当全部启用时）                               │
└─────────────────┬───────────────────────────────────────────┘
                  ↓
         计算22个性能指标
         生成推荐度分数（0-100）
         保存到performance字段
                  ↓
┌─────────────────────────────────────────────────────────────┐
│  Phase 3: 策略注册（Strategy Registration）                  │
│  Orchestrator Layer - StrategyRegistration Service           │
├─────────────────────────────────────────────────────────────┤
│  3.1 激活标准检查                                             │
│      - 推荐度分数 ≥ 65                                        │
│      - 核心4项指标至少通过3项                                  │
│      - 收益率、Sharpe、回撤、胜率                              │
│                                                              │
│  3.2 质量分数计算                                             │
│      - 6项指标加权平均                                         │
│      - 分数0-100                                             │
│                                                              │
│  3.3 策略生命周期管理                                          │
│      - CANDIDATE → ACTIVE → ARCHIVED                         │
│      - 只有ACTIVE策略才能被编排                                │
└─────────────────┬───────────────────────────────────────────┘
                  ↓
         激活策略进入编排池
         状态：ACTIVE
                  ↓
┌─────────────────────────────────────────────────────────────┐
│  Phase 4: 编排决策（Orchestration）                          │
│  Orchestrator Layer - 多模块协同                             │
├─────────────────────────────────────────────────────────────┤
│  4.1 账户管理（AccountManager）                               │
│      - 账户配置（风险类型、仓位限制）                           │
│      - 策略筛选（根据账户配置）                                 │
│                                                              │
│  4.2 资金分配（AllocationEngine）                             │
│      - 计算每个策略的资金分配比例                               │
│      - 等权重/按表现加权/风险平价                               │
│      - 调整信号手数                                            │
│                                                              │
│  4.3 风险管理（RiskManager）                                  │
│      - 检查总仓位限制                                          │
│      - 检查单策略限制                                          │
│      - 检查单日亏损                                            │
│      - 计算风险分数（0-10）                                    │
│                                                              │
│  4.4 信号评估（SignalEvaluator）                              │
│      - 集成以上所有模块                                        │
│      - 生成最终决策：APPROVED/ADJUSTED/REJECTED                │
│      - 记录完整决策链                                          │
└─────────────────┬───────────────────────────────────────────┘
                  ↓
         决策：APPROVED或ADJUSTED
                  ↓
┌─────────────────────────────────────────────────────────────┐
│  Phase 5: 执行风控（Execution Layer Risk Control）           │
│  Execution Service - 执行前最后检查                           │
├─────────────────────────────────────────────────────────────┤
│  5.1 行情过滤                                                 │
│      - 检查市场状态（开盘/休市）                               │
│      - 检查点差（是否异常）                                    │
│      - 检查流动性                                             │
│                                                              │
│  5.2 订单验证                                                 │
│      - 手数合法性                                             │
│      - 价格合法性                                             │
│      - 止损止盈设置                                            │
│                                                              │
│  5.3 最终执行                                                 │
│      - 调用MT5 API                                           │
│      - 下单到交易所                                            │
│      - 返回Ticket                                            │
└─────────────────┬───────────────────────────────────────────┘
                  ↓
         ✅ 订单成功执行
         记录到trades表
```

## 📊 各层级职责

### Layer 1: Strategy Service（策略服务）
**职责**：策略生成和评估
- ✅ 策略代码生成（黑盒）
- ✅ 三种评估方式（synthetic/historical/realtime）
- ✅ 22个性能指标计算
- ✅ 推荐度分数计算
- ✅ 不关心策略是否被使用

**输出**：
- Strategy对象（status=CANDIDATE）
- Performance字段（22个指标）
- Recommendation_summary（推荐度分数）

---

### Layer 2: Orchestrator Service（编排服务）⭐
**职责**：策略注册、资金分配、风险管理、信号决策

#### 2.1 StrategyRegistration（策略注册）
- ✅ 评估策略是否达到激活标准
- ✅ 管理策略生命周期（CANDIDATE → ACTIVE → ARCHIVED）
- ✅ **门卫作用**：只有ACTIVE策略才能被使用

#### 2.2 AccountManager（账户管理）
- ✅ 管理账户配置（单账户V1，多账户V2+）
- ✅ 账户级策略筛选

#### 2.3 AllocationEngine（资金分配）
- ✅ 计算每个策略的资金分配比例
- ✅ 等权重分配（V1）
- ✅ 调整信号手数

#### 2.4 RiskManager（风险管理）
- ✅ 检查仓位限制（总仓位、单策略）
- ✅ 检查单日亏损
- ✅ 计算风险分数

#### 2.5 SignalEvaluator（信号评估）
- ✅ 协调以上所有模块
- ✅ 生成最终决策
- ✅ 记录完整决策链

**输出**：
- SignalDecision对象
- Decision类型：APPROVED/ADJUSTED/REJECTED
- 调整后的手数
- 完整决策链（5步）

---

### Layer 3: Execution Service（执行服务）
**职责**：订单执行和行情风控

**执行前风控**：
- 市场状态检查
- 点差检查
- 流动性检查
- 订单合法性验证

**输出**：
- Trade对象（ticket, profit, status）
- 执行结果反馈给Orchestrator

---

## 🎯 关键设计原则

### 1. 策略是黑盒
- **Strategy Service可以使用任何算法生成策略**
- MA、RSI、MACD、机器学习、遗传算法...
- 大量生成（批量）
- 参数随机优化
- **不需要人工审核代码**

### 2. 多层评估保证质量
```
第一层：Strategy Evaluation（三种评估加权）
  ↓
第二层：Strategy Registration（激活标准）
  ↓
第三层：Orchestrator（配比、仓位、风险）
  ↓
第四层：Execution（行情过滤）
  ↓
最终执行
```

### 3. 只有优质策略被使用
```
生成100个策略
  ↓ 评估
80个达到基本标准（推荐度 > 60）
  ↓ 注册
20个达到激活标准（推荐度 ≥ 65，核心指标3/4）
  ↓ 编排
5个被分配资金（根据账户配置）
  ↓ 执行
实际使用的策略
```

### 4. 完整的决策追踪
每个信号都有完整的决策链：
```json
{
  "signal_id": "SIG_xxx",
  "decision": "adjusted",
  "steps": [
    {
      "step": 1,
      "module": "StrategyRegistration",
      "result": "策略已激活 (质量分数: 75.5)"
    },
    {
      "step": 2,
      "module": "AccountManager",
      "result": "账户配置有效"
    },
    {
      "step": 3,
      "module": "AllocationEngine",
      "result": "分配 10% (1000 USD)"
    },
    {
      "step": 4,
      "module": "RiskManager",
      "result": "风险检查通过 (风险分数: 3.2)"
    },
    {
      "step": 5,
      "module": "SignalEvaluator",
      "result": "adjusted"
    }
  ]
}
```

## 🔧 配置驱动

### Strategy Evaluation（策略评估配置）
```yaml
strategy_evaluation:
  enabled_evaluators:
    synthetic: true      # 模拟数据（默认）
    historical: false    # 历史数据（按需）
    realtime: false      # 实时数据（按需）
  
  weights:
    historical: 0.60     # 60%
    synthetic: 0.20      # 20%
    realtime: 0.20       # 20%
```

### Orchestrator（编排配置）
```yaml
orchestrator:
  # 激活标准
  activation:
    min_recommendation_score: 65
    min_total_return: 0.03
    min_sharpe_ratio: 0.50
    max_drawdown: 0.12
  
  # 资金管理
  portfolio:
    initial_balance: 10000.0
    max_total_exposure: 0.30
    max_strategy_allocation: 0.10
  
  # 风险限制
  risk:
    max_daily_loss: 0.05
    max_concurrent_trades: 10
```

## 📈 数据流

### 策略生成 → 评估
```
Strategy Service
  ├── generate_strategy()
  │   └── strategy_code (Python)
  │
  ├── evaluate_all()
  │   ├── synthetic_evaluation (default)
  │   ├── historical_evaluation (optional)
  │   └── realtime_evaluation (optional)
  │
  └── save_strategy()
      └── performance: {
            "backtested_symbol": "EURUSD",
            "sharpe_ratio": 0.52,
            "total_return": 0.0547,
            "recommendation_score": 71.3,
            ... (22 metrics total)
          }
```

### 评估 → 注册
```
Orchestrator - StrategyRegistration
  ├── batch_evaluate_candidates()
  │   └── 评估所有CANDIDATE策略
  │
  ├── evaluate_strategy_quality()
  │   ├── 检查6项指标
  │   ├── 计算质量分数
  │   └── qualified: true/false
  │
  └── activate_strategy()
      └── status: CANDIDATE → ACTIVE
```

### 注册 → 编排 → 执行
```
Signal生成
  ↓
Orchestrator - SignalEvaluator
  ├── Step 1: check_strategy_registration()
  ├── Step 2: check_account_config()
  ├── Step 3: calculate_allocation()
  ├── Step 4: check_risk()
  └── Step 5: generate_decision()
  ↓
Decision: {
  "approved": true,
  "adjusted_volume": 0.08,  # 从0.10调整到0.08
  "risk_score": 3.2
}
  ↓
Execution Service
  ├── 行情过滤
  ├── 订单验证
  └── MT5执行
  ↓
✅ 订单成功
```

## 🎉 总结

### 策略是黑盒 ✅
- 任何算法都可以
- 大量生成
- 评估系统保证质量

### 多层过滤保证安全 ✅
1. **评估层**：三种评估加权（synthetic/historical/realtime）
2. **注册层**：激活标准筛选（StrategyRegistration）
3. **编排层**：资金分配+风险管理（Orchestrator）
4. **执行层**：行情过滤（Execution）

### 完整追踪可审计 ✅
- 每个策略有22个性能指标
- 每个信号有完整决策链
- 每个决策有置信度和风险分数

### 配置驱动易调整 ✅
- 评估权重可调
- 激活标准可调
- 风险限制可调

---

**最终结果**：只有经过多层筛选和风险控制的优质策略，才会被实际使用！
