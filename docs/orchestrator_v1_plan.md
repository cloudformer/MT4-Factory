# Orchestrator V1 实现计划

## 🎯 目标

实现策略编排层核心功能，使系统能够：
1. **策略注册和激活管理**（StrategyRegistration）- 基础服务
2. **账户配置管理**（AccountManager）- 账户级策略组合
3. **资金分配计算**（AllocationEngine）- 纯算法层
4. **风险检查和策略执行**（RiskManager）- 策略和限制分离
5. **信号评估协调**（SignalEvaluator）- 集成所有模块

## 🏗️ 架构设计原则

### 协调者模式（Coordinator Pattern）
- **Orchestrator** = 协调者，调用其他模块，不执行具体业务逻辑
- 各模块职责单一，通过接口通信
- 支持独立测试和扩展

### 账户中心设计（Account-Centric）
- 每个账户 = 完整配置单元
- 配置包含：策略列表、资金分配、风险参数、长短线配比
- 支持多账户独立管理

### 策略生命周期管理
- **Candidate** → **Active** → **Archived**
- StrategyRegistration服务负责激活决策
- 只有Active状态的策略才能被编排使用

## 📊 核心模块

### 🔑 1. StrategyRegistration（策略注册服务）**【最优先】**

**职责**：
- 管理策略激活状态（只有激活的策略才能被编排）
- 作为所有编排调度决策的基础
- 策略质量评估和分数计算
- 策略生命周期管理

**为什么是基础服务**：
- Orchestrator的所有调度决策都基于此服务
- AllocationEngine只能从激活的策略中选择
- 策略质量评估为后续分配提供依据

**核心功能**：
```python
class StrategyRegistration:
    def get_active_strategies(symbol: str = None) -> List[Strategy]:
        """获取所有激活的策略（编排的基础）"""
        
    def evaluate_strategy_quality(strategy: Strategy) -> Dict:
        """评估策略质量，判断是否符合激活条件"""
        
    def activate_strategy(strategy_id: str, force: bool = False) -> Dict:
        """激活策略（进入编排池）"""
        
    def deactivate_strategy(strategy_id: str, reason: str = None) -> Dict:
        """停用策略（退出编排池）"""
        
    def get_strategy_score(strategy_id: str) -> float:
        """获取策略当前质量分数"""
        
    def batch_evaluate_candidates() -> Dict:
        """批量评估候选策略，自动激活符合条件的"""
```

**激活标准**（V1）：
```yaml
orchestrator:
  activation:
    min_recommendation_score: 65     # 推荐度≥65分
    min_total_return: 0.03           # 收益率≥3%
    min_sharpe_ratio: 0.50           # Sharpe≥0.5
    max_drawdown: 0.12               # 回撤≤12%
    min_win_rate: 0.35               # 胜率≥35%
    min_profit_factor: 1.5           # 盈亏比≥1.5
    
    # 激活条件：核心4项指标至少通过3个
```

**质量分数计算**：
- 综合6项指标加权平均
- 推荐度权重30%，收益率20%，其他各15%/10%
- 分数0-100，越高越好

**未来扩展**（V2+）：
- 实时分数系统：持续监控策略表现
- 自动降级：表现下降时自动停用
- A/B测试：同时测试多个参数版本

### 2. AccountManager（账户管理器）

**职责**：
- 管理账户配置（每个账户 = 完整配置单元）
- 维护账户级策略组合
- 提供账户信息查询

**为什么是账户中心**：
- 每个账户有独立的策略选择、资金分配、风险偏好
- 支持多账户：保守账户、激进账户等
- 配置集中管理，易于理解和维护

**核心数据结构**：
```python
class Account:
    """账户对象"""
    account_id: str                  # 账户ID
    name: str                        # 账户名称
    balance: float                   # 账户余额
    profile: AccountProfile          # 风险配置
    allocation_config: AllocationConfig  # 分配配置
    status: str                      # active/paused

class AccountProfile:
    """账户风险配置"""
    risk_type: str                   # balanced/aggressive/conservative
    max_total_exposure: float        # 总仓位上限
    max_strategy_allocation: float   # 单策略上限
    max_daily_loss: float           # 单日亏损上限
    # 长短线配比
    short_term_ratio: float         # 短线占比
    long_term_ratio: float          # 长线占比

class AllocationConfig:
    """资金分配配置"""
    mode: str                       # balanced/aggressive/conservative
    max_strategies: int             # 最多策略数
    target_symbols: List[str]       # 目标货币对
    strategy_filters: Dict          # 策略筛选条件
```

**核心功能**：
```python
class AccountManager:
    def get_account(account_id: str) -> Account:
        """获取账户配置"""
        
    def update_account_profile(account_id: str, profile: AccountProfile):
        """更新账户风险配置"""
        
    def get_account_strategies(account_id: str) -> List[Strategy]:
        """获取账户的策略列表（已激活的）"""
```

### 3. AllocationEngine（配比引擎）

**职责**：
- 纯算法层：只计算，不管理状态
- 根据账户配置和Profile筛选策略
- 计算资金分配比例
- 提供多种分配算法

**为什么是纯算法层**：
- 职责单一：只负责计算逻辑
- 无状态：不持有账户或策略数据
- 可测试：输入→输出，易于单元测试
- 可扩展：新增算法不影响其他模块

**配置模板**：
```python
PORTFOLIO_TEMPLATES = {
    "balanced": {
        "name": "平衡型组合",
        "filters": {
            "stability_score": ">0.50",      # 稳定性>50%
            "max_drawdown": "<0.10",         # 回撤<10%
            "sharpe_ratio": ">0.60"          # Sharpe>0.6
        },
        "max_strategies": 5,
        "allocation_method": "equal_weight"   # 等权重
    },
    
    "aggressive": {
        "name": "进取型组合",
        "filters": {
            "total_return": ">0.30",         # 收益>30%
            "profit_factor": ">3.0",         # 盈亏比>3
            "market_regime": "trend"         # 趋势策略
        },
        "max_strategies": 3,
        "allocation_method": "performance_weight"  # 按表现加权
    },
    
    "conservative": {
        "name": "保守型组合",
        "filters": {
            "max_drawdown": "<0.08",         # 回撤<8%
            "stability_score": ">0.60",      # 稳定性>60%
            "volatility": "<0.15",           # 波动率<15%
            "sharpe_ratio": ">1.0"           # Sharpe>1.0
        },
        "max_strategies": 4,
        "allocation_method": "risk_parity"   # 风险平价
    }
}
```

**核心算法**：
```python
class AllocationEngine:
    def select_strategies(template: str) -> List[Strategy]:
        """根据模板筛选策略"""
        
    def calculate_allocation(strategies: List[Strategy]) -> Dict[str, float]:
        """计算资金分配
        
        Returns:
            {"STR_xxx": 0.20, "STR_yyy": 0.15, ...}  # 策略ID -> 资金占比
        """
        
    def rebalance_portfolio():
        """重新平衡组合（定期执行）"""
```

### 4. RiskManager（风险管理器）

**职责**：
- 独立的风险检查和策略执行模块
- 检查全局和单策略风险限制
- 计算仓位占用和暴露度
- 策略合规性检查

**为什么独立出来**：
- 风险管理是关键功能，需要独立和透明
- 策略（Policy）和执行分离
- 支持复杂的风险计算逻辑
- 便于审计和回溯

**核心组件**：
```python
class PolicyChecker:
    """策略检查器"""
    def check_total_exposure(current: float, new: float) -> bool:
        """检查总仓位是否超限"""
        
    def check_strategy_limit(strategy_id: str, volume: float) -> bool:
        """检查单策略仓位是否超限"""
        
    def check_daily_loss(account_id: str) -> bool:
        """检查是否触及单日亏损限制"""

class RiskCalculator:
    """风险计算器"""
    def calculate_exposure(positions: List) -> float:
        """计算总仓位占用"""
        
    def calculate_strategy_risk(strategy: Strategy, volume: float) -> float:
        """计算单笔交易风险"""
        
    def calculate_correlation(strategies: List[Strategy]) -> float:
        """计算策略间相关性"""

class RiskManager:
    """风险管理器（协调）"""
    def __init__(self):
        self.policy_checker = PolicyChecker()
        self.risk_calculator = RiskCalculator()
    
    def evaluate_signal_risk(signal: Signal, account: Account) -> Dict:
        """综合风险评估"""
```

**风险检查流程**：
```
信号生成 → RiskManager评估：
  1. 检查总仓位限制
  2. 检查单策略限制
  3. 检查单日亏损
  4. 计算风险分数
  → approved/rejected + 调整后的volume
```

### 5. SignalEvaluator（信号评估器）

**职责**：
- 协调所有模块进行信号决策
- 整合各模块的评估结果
- 记录决策链和理由

**为什么是协调者**：
- 集成点：调用StrategyRegistration、AccountManager、AllocationEngine、RiskManager
- 不实现具体逻辑，只负责编排调用
- 提供统一的决策接口

**核心功能**：
```python
class SignalEvaluator:
    def evaluate_signal(signal: Signal, strategy: Strategy) -> Decision:
        """评估信号
        
        Returns:
            Decision(
                approved=True/False,
                volume=0.05,  # 调整后的仓位
                reason="风险检查通过",
                risk_score=2.5
            )
        """
        
    def check_risk_limits(signal: Signal) -> bool:
        """检查风险限制"""
        
    def adjust_volume(signal: Signal, strategy: Strategy) -> float:
        """根据资金分配调整仓位"""
```

## 🗂️ 文件结构

```
src/services/orchestrator/
├── service/
│   ├── orchestrator.py             # 现有：顶层协调器
│   ├── strategy_registration.py   # ✅ 已实现：策略注册服务
│   ├── account_manager.py          # 🆕 账户管理
│   ├── allocation_engine.py        # 🆕 配比引擎（纯算法）
│   ├── risk_manager.py             # 🆕 风险管理（独立模块）
│   └── signal_evaluator.py         # 🆕 信号评估（协调器）
├── repository/
│   ├── signal_repo.py              # 现有
│   └── strategy_repo.py            # ✅ 已实现：策略数据访问
└── api/
    └── routes/
        ├── signal.py               # 现有
        ├── registration.py         # 🆕 策略注册API
        ├── account.py              # 🆕 账户管理API
        └── portfolio.py            # 🆕 组合查询API
```

## 📝 实现步骤

### Phase 0: 基础服务（最优先）⭐

**目标**: 实现StrategyRegistration服务 - 编排的基石

```
✅ Step 0.1: StrategyRegistration服务
  - ✅ 创建strategy_registration.py
  - ✅ 实现ActivationCriteria评估逻辑
  - ✅ 实现激活/停用/归档功能
  - ✅ 实现质量分数计算
  - ✅ 批量评估候选策略

✅ Step 0.2: 配置和数据访问
  - ✅ 创建strategy_repo.py（Orchestrator专用）
  - ✅ 添加orchestrator.activation配置
  - ✅ 定义激活标准和阈值

⏳ Step 0.3: API接口
  - 🆕 GET /registration/active - 获取激活策略列表
  - 🆕 POST /registration/activate/{id} - 激活策略
  - 🆕 POST /registration/deactivate/{id} - 停用策略
  - 🆕 GET /registration/evaluate/{id} - 评估策略质量
  - 🆕 POST /registration/batch-evaluate - 批量评估候选策略
```

### Phase 1: 账户和分配（次优先）

**目标**: 建立账户中心管理和资金分配算法

```
⏳ Step 1.1: AccountManager
  - Account, AccountProfile, AllocationConfig数据结构
  - 账户配置管理
  - 账户策略查询

⏳ Step 1.2: AllocationEngine
  - 实现3种模板（balanced/aggressive/conservative）
  - 等权重分配算法
  - 根据Profile筛选策略

⏳ Step 1.3: 配置文件扩展
  - orchestrator.portfolio配置
  - orchestrator.allocation配置
```

### Phase 2: 风险管理

**目标**: 实现独立的风险检查模块

```
⏳ Step 2.1: RiskManager核心
  - PolicyChecker - 策略检查器
  - RiskCalculator - 风险计算器
  - 组合检查逻辑

⏳ Step 2.2: 风险计算
  - 总仓位占用计算
  - 单策略风险计算
  - 策略相关性计算（可选）

⏳ Step 2.3: 风险配置
  - orchestrator.risk配置
  - 风险阈值和限制
```

### Phase 3: 信号评估协调

**目标**: 集成所有模块进行信号决策

```
⏳ Step 3.1: SignalEvaluator协调器
  - 调用StrategyRegistration检查策略状态
  - 调用AccountManager获取账户配置
  - 调用AllocationEngine计算分配
  - 调用RiskManager检查风险
  
⏳ Step 3.2: 决策整合
  - 综合各模块结果
  - 生成最终决策（approve/reject/adjust）
  - 记录决策链和理由
```

### Phase 4: API和Dashboard集成

**目标**: 暴露Orchestrator功能给Dashboard

```
⏳ Step 4.1: Registration API
  - GET /registration/active - 激活策略列表
  - POST /registration/activate/{id} - 激活策略
  - POST /registration/deactivate/{id} - 停用策略
  - GET /registration/summary - 注册服务概览
  
⏳ Step 4.2: Account API
  - GET /account/{id} - 获取账户配置
  - PUT /account/{id}/profile - 更新账户配置
  - GET /account/{id}/strategies - 账户策略列表
  
⏳ Step 4.3: Portfolio API
  - GET /portfolio/status - 组合状态
  - GET /portfolio/allocation - 资金分配
  - POST /portfolio/rebalance - 重新平衡
  
⏳ Step 4.4: Dashboard UI
  - 策略激活/停用按钮
  - 激活标准可视化
  - 账户配置界面
  - 资金分配图表
```

## 🎯 V1 最小功能集

### 必须有（Phase 0-1）✅

1. **StrategyRegistration** - 编排基础 ⭐ 最优先
   - ✅ 策略激活/停用/归档
   - ✅ 质量评估和分数计算
   - ✅ 批量评估候选策略
   - ✅ 激活标准配置
   - ⏳ API接口

2. **AccountManager** - 账户管理
   - 账户配置管理（Account, AccountProfile, AllocationConfig）
   - 账户策略查询
   - 支持单账户（多账户V2）

3. **AllocationEngine** - 基础配比
   - 1个模板（balanced）
   - 简单等权重分配
   - 根据Profile筛选（3-5个关键指标）

4. **RiskManager** - 基础风险检查
   - 总仓位限制检查
   - 单策略限制检查
   - 基础风险计算

5. **SignalEvaluator** - 决策协调
   - 调用各模块进行评估
   - 整合结果生成决策
   - 记录决策链

### 可以后续做（V2+）⏸️
- 多种分配算法（风险平价、Kelly公式、按表现加权）
- 实时策略质量分数更新
- 策略自动降级/提升
- 策略相关性计算
- 动态再平衡
- 多账户独立管理
- 长短线配比
- 回测组合表现

## 📊 数据模型

### Portfolio配置
```yaml
# config/development.yaml
orchestrator:
  portfolio:
    initial_balance: 10000.0
    max_total_exposure: 0.30      # 30%总仓位
    max_strategy_allocation: 0.10  # 10%单策略上限
    
  allocation:
    mode: "balanced"               # balanced/aggressive/conservative
    max_strategies: 5              # 最多同时运行5个策略
    
  filters:
    min_recommendation_score: 65   # 最低推荐度65分
    min_sharpe_ratio: 0.50        # 最低Sharpe 0.5
    max_drawdown: 0.12            # 最大回撤12%
```

### Portfolio状态（内存/可选持久化）
```python
{
  "total_balance": 10000.0,
  "allocated": 3000.0,          # 已分配资金
  "available": 7000.0,          # 可用资金
  "total_exposure": 0.28,       # 当前总仓位28%
  
  "allocations": {
    "STR_xxx": {
      "allocation": 0.10,       # 分配比例10%
      "balance": 1000.0,        # 分配金额
      "current_exposure": 0.05, # 当前占用5%
      "active": true
    },
    "STR_yyy": {
      "allocation": 0.08,
      "balance": 800.0,
      "current_exposure": 0.03,
      "active": true
    }
  },
  
  "last_rebalance": "2026-04-10T18:00:00"
}
```

## 🔄 完整工作流程

### 1. 系统启动时
```
1. Orchestrator启动
2. StrategyRegistration初始化
   - 加载激活标准配置
   - 从数据库读取所有策略
   - 准备激活策略列表（Active状态）
   
3. AccountManager加载账户配置
   - 读取账户信息和风险配置
   - 关联账户和策略
   
4. AllocationEngine准备算法
   - 加载分配模板配置
   - 准备计算引擎
   
5. RiskManager加载风险限制
   - 读取风险阈值
   - 初始化检查器和计算器
```

### 2. 策略生成后（新增流程）
```
StrategyGenerator生成策略
          ↓
保存到数据库（状态=CANDIDATE）
          ↓
【可选】自动评估：
  StrategyRegistration.batch_evaluate_candidates()
    - 评估所有候选策略
    - 符合条件的自动激活 → Active
    - 不符合的保持 Candidate
          ↓
只有Active状态的策略才能被Orchestrator使用
```

### 3. 信号生成时（完整决策链）
```
Strategy生成信号
     ↓
【Step 1】StrategyRegistration检查
  - 该策略是否Active？
  - 质量分数是否达标？
  → 如果不是Active → 直接拒绝
     ↓
【Step 2】AccountManager查询
  - 获取账户配置
  - 该策略是否在账户策略列表中？
  - 账户是否处于暂停状态？
     ↓
【Step 3】AllocationEngine计算
  - 根据账户配置和策略Profile
  - 计算该策略应分配的资金比例
  - 调整信号的volume
     ↓
【Step 4】RiskManager检查
  - 检查总仓位限制
  - 检查单策略限制
  - 检查单日亏损
  - 计算风险分数
     ↓
【Step 5】SignalEvaluator综合决策
  - 整合以上所有检查结果
  - 生成最终决策：
    * APPROVED - 执行信号（可能调整volume）
    * REJECTED - 拒绝信号（记录原因）
    * ADJUSTED - 调整后执行
  - 记录完整决策链
     ↓
Execution执行（如果approved）
```

### 4. 定期任务
```
【每小时】StrategyRegistration监控（未来）
  - 更新策略质量分数
  - 检查Active策略是否仍符合标准
  - 自动降级表现下降的策略

【每天】账户和组合管理
  1. 检查风险限制是否触发
  2. 生成每日报告
  3. 发送通知

【每周】组合再平衡
  1. AllocationEngine重新计算分配
  2. 调整策略权重
  3. 更新账户配置
```

### 5. 手动操作
```
【Dashboard操作】
1. 查看策略列表 → StrategyRegistration.get_active_strategies()
2. 手动激活策略 → StrategyRegistration.activate_strategy(id)
3. 手动停用策略 → StrategyRegistration.deactivate_strategy(id, reason)
4. 查看质量分数 → StrategyRegistration.get_strategy_score(id)
5. 评估候选策略 → StrategyRegistration.evaluate_strategy_quality(strategy)

【配置调整】
1. 修改激活标准 → 更新config/development.yaml
2. 调整账户配置 → AccountManager.update_account_profile()
3. 修改风险限制 → 更新orchestrator.risk配置
```

## 🎨 Dashboard展示

### 新增页面：Portfolio管理

```
┌─────────────────────────────────────────────────────┐
│ Portfolio 状态                                      │
├─────────────────────────────────────────────────────┤
│ 总资金: $10,000    已分配: $3,000    可用: $7,000   │
│ 总仓位: 28% / 30%  [████████░░] 93%                │
├─────────────────────────────────────────────────────┤
│ 组合类型: 平衡型 ▼                                  │
│                                                     │
│ 策略分配：                                          │
│ MA_12x60  (10%)  $1,000  占用: 5%  [激活]          │
│ MA_19x54  (8%)   $800    占用: 3%  [激活]          │
│ MA_6x52   (7%)   $700    占用: 4%  [激活]          │
│                                                     │
│ [重新平衡组合] [修改配置]                           │
└─────────────────────────────────────────────────────┘
```

## 🚀 实现进度

### ✅ Phase 0 已完成 - StrategyRegistration（策略注册服务）

1. **核心服务**
   - ✅ `strategy_registration.py` - 策略生命周期管理
   - ✅ `strategy_repo.py` - 数据访问层
   - ✅ ActivationCriteria - 激活标准评估
   - ✅ 质量分数计算（6项指标加权）
   - ✅ 激活/停用/归档功能
   - ✅ 批量评估候选策略

2. **API接口**
   - ✅ `registration.py` - 8个REST API端点
   - ✅ 已集成到Orchestrator服务

3. **配置**
   - ✅ `orchestrator.activation` - 可配置激活标准

4. **文档**
   - ✅ `strategy_registration_guide.md` - 完整使用指南

### ✅ Phase 1 已完成 - AccountManager + AllocationEngine

1. **AccountManager**
   - ✅ `account_manager.py` - 账户配置管理
   - ✅ Account、AccountProfile、AllocationConfig数据结构
   - ✅ 策略筛选和账户查询
   - ✅ V1单账户支持

2. **AllocationEngine**
   - ✅ `allocation_engine.py` - 纯算法层
   - ✅ 等权重分配（V1实现）
   - ✅ 风险调整和验证
   - ✅ PortfolioBuilder组合构建器

3. **API接口**
   - ✅ `account.py` - 账户管理API
   - ✅ `portfolio.py` - 组合管理API

### ✅ Phase 2 已完成 - RiskManager

1. **核心组件**
   - ✅ `risk_manager.py` - 风险管理器
   - ✅ PolicyChecker - 策略检查器
   - ✅ RiskCalculator - 风险计算器
   - ✅ 仓位占用计算
   - ✅ 风险分数评估（0-10）

2. **API接口**
   - ✅ `risk.py` - 风险管理API
   - ✅ 风险概览和状态监控

### ✅ Phase 3 已完成 - SignalEvaluator

1. **核心功能**
   - ✅ `signal_evaluator.py` - 信号评估协调器
   - ✅ 完整决策链（5步）
   - ✅ 集成所有模块
   - ✅ SignalDecision决策对象
   - ✅ 批量评估支持

2. **API接口**
   - ✅ `evaluation.py` - 信号评估API
   - ✅ 单个/批量评估
   - ✅ 模块状态检查

### ✅ Phase 4 已完成 - API集成

1. **API路由**
   - ✅ `/registration/*` - 策略注册（8个端点）
   - ✅ `/account/*` - 账户管理（6个端点）
   - ✅ `/portfolio/*` - 组合管理（5个端点）
   - ✅ `/risk/*` - 风险管理（6个端点）
   - ✅ `/evaluation/*` - 信号评估（5个端点）

2. **Dashboard UI**
   - ✅ 信号列表显示注册状态
   - ✅ 交易记录显示注册状态
   - ✅ 策略状态颜色标识

---

## 📊 V1 完成总结

### 核心架构 ✅
```
SignalEvaluator（协调器）
    ↓
┌───────────────┬──────────────┬──────────────┬─────────────┐
│ Registration  │  Account     │  Allocation  │    Risk     │
│   策略注册     │  账户管理     │  资金分配     │   风险管理   │
└───────────────┴──────────────┴──────────────┴─────────────┘
```

### 决策链 ✅
```
信号生成
  ↓
Step 1: 策略是否激活？        (StrategyRegistration)
  ↓
Step 2: 账户配置有效？         (AccountManager)
  ↓
Step 3: 资金如何分配？         (AllocationEngine)
  ↓
Step 4: 风险是否可控？         (RiskManager)
  ↓
Step 5: 生成最终决策           (SignalEvaluator)
  ↓
APPROVED / ADJUSTED / REJECTED
```

### 文件清单 ✅
```
src/services/orchestrator/
├── service/
│   ├── strategy_registration.py   ✅ 策略注册
│   ├── account_manager.py          ✅ 账户管理
│   ├── allocation_engine.py        ✅ 资金分配
│   ├── risk_manager.py             ✅ 风险管理
│   └── signal_evaluator.py         ✅ 信号评估
├── repository/
│   └── strategy_repo.py            ✅ 数据访问
└── api/routes/
    ├── registration.py             ✅ 注册API
    ├── account.py                  ✅ 账户API
    ├── portfolio.py                ✅ 组合API
    ├── risk.py                     ✅ 风险API
    └── evaluation.py               ✅ 评估API

docs/
├── orchestrator_v1_plan.md         ✅ 架构设计
└── strategy_registration_guide.md  ✅ 使用指南

config/
└── development.yaml                ✅ Orchestrator配置
```

### API端点总计：30个 ✅

**Registration (8)**
- GET /registration/active
- GET /registration/candidates
- POST /registration/activate/{id}
- POST /registration/deactivate/{id}
- POST /registration/archive/{id}
- GET /registration/evaluate/{id}
- POST /registration/batch-evaluate
- GET /registration/summary

**Account (6)**
- GET /account/{id}
- GET /account/{id}/summary
- GET /account/{id}/strategies
- PUT /account/{id}/profile
- PUT /account/{id}/allocation
- GET /account/{id}/balance

**Portfolio (5)**
- GET /portfolio/status
- GET /portfolio/allocation
- POST /portfolio/rebalance
- GET /portfolio/history
- GET /portfolio/comparison

**Risk (6)**
- GET /risk/summary
- POST /risk/evaluate-signal
- GET /risk/limits
- GET /risk/status
- POST /risk/update-positions
- POST /risk/record-trade

**Evaluation (5)**
- POST /evaluation/evaluate-signal
- POST /evaluation/evaluate-batch
- GET /evaluation/decision-chain/{id}
- GET /evaluation/statistics
- POST /evaluation/dry-run
- GET /evaluation/modules-status

---

## 🎉 V1 已完成！

**架构优势**：
- ✅ 清晰的职责分离
- ✅ 账户中心设计
- ✅ 完整的决策链追踪
- ✅ 独立的风险管理
- ✅ 配置驱动，易扩展

**下一步（V2+）**：
- 实时策略质量分数更新
- 多账户独立管理
- 更多分配算法（风险平价、Kelly公式）
- 决策历史持久化
- 策略相关性计算
- 长短线配比
- 组合回测
