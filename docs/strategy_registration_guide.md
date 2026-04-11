# 策略注册服务指南 - StrategyRegistration

## 📖 概述

**StrategyRegistration**是Orchestrator的核心基础服务，负责：
- 管理策略激活状态（只有激活的策略才能被编排）
- 策略质量评估和分数计算
- 作为所有编排调度决策的基础

## 🎯 为什么需要这个服务

### 问题：不是所有策略都应该被使用
- 生成了100个策略，但只有20个表现好
- 策略表现会随时间下降
- 需要一个"门卫"机制，只允许优质策略进入编排池

### 解决方案：StrategyRegistration服务
```
生成策略 → 评估质量 → 激活（Active） → Orchestrator使用
                   ↓
                不符合标准
                   ↓
                保持候选（Candidate）
```

## 🏗️ 策略生命周期

```
┌─────────────┐
│  CANDIDATE  │  新生成的策略，待评估
└──────┬──────┘
       │ evaluate & activate
       ↓
┌─────────────┐
│   ACTIVE    │  通过评估，可以被编排使用
└──────┬──────┘
       │ deactivate / performance decline
       ↓
┌─────────────┐
│  CANDIDATE  │  停用但可重新激活
└──────┬──────┘
       │ archive
       ↓
┌─────────────┐
│  ARCHIVED   │  永久停用
└─────────────┘
```

## ✅ 激活标准（V1）

### 核心指标（4项，至少通过3项）
1. **推荐度分数** ≥ 65分（权重30%）
2. **收益率** ≥ 3%（权重20%）
3. **Sharpe比率** ≥ 0.5（权重15%）
4. **最大回撤** ≤ 12%（权重15%）

### 辅助指标
5. **胜率** ≥ 35%（权重10%）
6. **盈亏比** ≥ 1.5（权重10%）

### 配置位置
```yaml
# config/development.yaml
orchestrator:
  activation:
    min_recommendation_score: 65
    min_total_return: 0.03
    min_sharpe_ratio: 0.50
    max_drawdown: 0.12
    min_win_rate: 0.35
    min_profit_factor: 1.5
```

## 📊 质量分数计算

**公式**：加权平均
```
quality_score = Σ (指标值/阈值 × 100 × 权重)
```

**示例**：
```python
策略A:
- recommendation_score: 71 / 65 × 100 × 0.30 = 32.8
- total_return: 0.05 / 0.03 × 100 × 0.20 = 33.3
- sharpe_ratio: 0.6 / 0.5 × 100 × 0.15 = 18.0
- max_drawdown: 0.08 / 0.12 × 100 × 0.15 = 10.0
- win_rate: 0.4 / 0.35 × 100 × 0.10 = 11.4
- profit_factor: 2.0 / 1.5 × 100 × 0.10 = 13.3

总分 = 32.8 + 33.3 + 18.0 + 10.0 + 11.4 + 13.3 = 118.8
质量分数 = min(118.8, 100) = 100分 ✅ 优秀
```

## 🔧 API接口

### 1. 获取激活策略列表
```bash
GET /registration/active?symbol=EURUSD

Response:
[
  {
    "id": "STR_xxx",
    "name": "MA_12x60",
    "status": "active",
    "quality_score": 75.5,
    "backtested_symbol": "EURUSD"
  }
]
```

### 2. 获取候选策略列表
```bash
GET /registration/candidates

Response:
[
  {
    "id": "STR_yyy",
    "name": "MA_19x54",
    "status": "candidate",
    "quality_score": 58.2,
    "backtested_symbol": "EURUSD"
  }
]
```

### 3. 评估策略质量
```bash
GET /registration/evaluate/STR_xxx

Response:
{
  "qualified": true,
  "quality_score": 75.5,
  "stability_score": 0.52,
  "core_passed": 3,
  "core_required": 3,
  "reasons": [
    "✅ 推荐度达标 (71.00)",
    "✅ 收益率达标 (5.00%)",
    "✅ Sharpe比率达标 (0.60)",
    "✅ 最大回撤达标 (8.00%)"
  ],
  "backtested_symbol": "EURUSD"
}
```

### 4. 激活策略
```bash
POST /registration/activate/STR_xxx
{
  "force": false  # 是否强制激活（忽略质量检查）
}

Response:
{
  "success": true,
  "message": "策略激活成功",
  "strategy_id": "STR_xxx",
  "evaluation": {...}
}
```

### 5. 停用策略
```bash
POST /registration/deactivate/STR_xxx
{
  "reason": "表现下降"
}

Response:
{
  "success": true,
  "message": "策略已停用: 表现下降",
  "strategy_id": "STR_xxx"
}
```

### 6. 归档策略
```bash
POST /registration/archive/STR_xxx
{
  "reason": "参数过时"
}

Response:
{
  "success": true,
  "message": "策略已归档: 参数过时",
  "strategy_id": "STR_xxx"
}
```

### 7. 批量评估候选策略
```bash
POST /registration/batch-evaluate

Response:
{
  "evaluated": 10,
  "activated": 3,
  "results": [
    {
      "strategy_id": "STR_xxx",
      "strategy_name": "MA_12x60",
      "evaluation": {...},
      "activated": true
    },
    ...
  ],
  "timestamp": "2026-04-10T15:30:00"
}
```

### 8. 获取注册服务概览
```bash
GET /registration/summary

Response:
{
  "total": 50,
  "active": 12,
  "candidate": 35,
  "archived": 3,
  "activation_criteria": {
    "min_recommendation_score": 65,
    "min_total_return": 0.03,
    "min_sharpe_ratio": 0.50,
    "max_drawdown": 0.12,
    "min_win_rate": 0.35,
    "min_profit_factor": 1.5
  },
  "timestamp": "2026-04-10T15:30:00"
}
```

## 💻 代码使用示例

### 在Python代码中使用
```python
from src.services.orchestrator.service.strategy_registration import StrategyRegistration

# 初始化服务
registration = StrategyRegistration()

# 获取所有激活的策略
active_strategies = registration.get_active_strategies()
print(f"当前有 {len(active_strategies)} 个激活策略")

# 获取EURUSD的激活策略
eurusd_strategies = registration.get_active_strategies(symbol="EURUSD")

# 评估某个策略
strategy = repo.get_by_id("STR_xxx")
evaluation = registration.evaluate_strategy_quality(strategy)

if evaluation['qualified']:
    print(f"策略符合激活条件，质量分数: {evaluation['quality_score']}")
    # 激活策略
    result = registration.activate_strategy(strategy.id)
else:
    print(f"策略不符合激活条件:")
    for reason in evaluation['reasons']:
        print(f"  {reason}")

# 批量评估所有候选策略
result = registration.batch_evaluate_candidates()
print(f"评估了 {result['evaluated']} 个策略，激活了 {result['activated']} 个")
```

### 在Orchestrator中使用
```python
from src.services.orchestrator.service.strategy_registration import StrategyRegistration

class SignalOrchestrator:
    def __init__(self):
        self.registration = StrategyRegistration()
    
    def generate_signals(self):
        # 只从激活的策略中生成信号
        active_strategies = self.registration.get_active_strategies()
        
        for strategy in active_strategies:
            # 再次检查质量分数
            score = self.registration.get_strategy_score(strategy.id)
            if score >= 70:  # 只使用高质量策略
                signal = self._generate_signal(strategy)
                ...
```

## 🎯 使用场景

### 场景1：策略生成后自动评估
```python
# 在StrategyGenerator中
def generate_and_register(self):
    # 1. 生成策略
    strategy = self.generate_strategy()
    
    # 2. 保存到数据库（状态=CANDIDATE）
    repo.save(strategy)
    
    # 3. 自动评估和激活
    registration = StrategyRegistration()
    result = registration.batch_evaluate_candidates()
    
    print(f"新策略 {strategy.name}:")
    if strategy.status == 'active':
        print("✅ 自动激活，可以使用")
    else:
        print("⏸️ 候选状态，需要优化")
```

### 场景2：定期检查和降级
```python
# 定期任务（每天运行）
def daily_quality_check():
    registration = StrategyRegistration()
    
    # 检查所有激活策略
    active_strategies = registration.get_active_strategies()
    
    for strategy in active_strategies:
        evaluation = registration.evaluate_strategy_quality(strategy)
        
        # 如果不再符合标准，停用
        if not evaluation['qualified']:
            registration.deactivate_strategy(
                strategy.id,
                reason=f"质量下降至 {evaluation['quality_score']:.1f}分"
            )
            print(f"⚠️ 策略 {strategy.name} 已自动停用")
```

### 场景3：Dashboard手动操作
```python
# 用户在Dashboard点击"激活"按钮
async def activate_strategy_handler(strategy_id: str):
    registration = StrategyRegistration()
    
    # 先评估
    evaluation = registration.evaluate_strategy_quality(strategy)
    
    # 显示评估结果给用户
    show_evaluation_dialog(evaluation)
    
    # 用户确认后激活
    if user_confirmed:
        result = registration.activate_strategy(strategy_id)
        if result['success']:
            show_success_message("策略已激活")
        else:
            show_error_message(result['message'])
```

## 🔮 未来扩展（V2+）

### 实时质量分数
```python
# 持续监控策略实盘表现
class RealtimeScorer:
    def update_scores_continuously(self):
        """每小时更新一次质量分数"""
        for strategy in active_strategies:
            # 基于最近N笔交易重新计算分数
            new_score = calculate_realtime_score(strategy)
            
            # 如果分数下降超过阈值，自动降级
            if new_score < 60:
                registration.deactivate_strategy(strategy.id)
```

### 策略分组管理
```python
# 按类型管理策略
class StrategyGroups:
    def get_by_type(self, strategy_type: str):
        """获取指定类型的激活策略"""
        all_active = registration.get_active_strategies()
        return [s for s in all_active if s.type == strategy_type]
    
    # 趋势策略组
    trend_strategies = get_by_type("trend")
    
    # 震荡策略组
    range_strategies = get_by_type("range")
```

## 📋 检查清单

### 激活策略前
- [ ] 策略已完成回测
- [ ] performance字段包含22个指标
- [ ] 推荐度分数 ≥ 65
- [ ] 核心4项指标至少通过3项
- [ ] 回测品种明确（backtested_symbol）

### 定期维护
- [ ] 每天检查激活策略质量
- [ ] 每周评估候选策略
- [ ] 每月调整激活标准（如需要）
- [ ] 归档长期表现不佳的策略

## 🔗 相关文档

- [Orchestrator V1计划](./orchestrator_v1_plan.md) - 完整架构
- [配置文件](../config/development.yaml) - 激活标准配置
- [策略模型](../src/common/models/strategy.py) - 数据结构
- [API文档](http://localhost:8002/docs) - 完整API参考

---

**版本**: V1.0  
**状态**: ✅ 已实现  
**下一步**: 实现AccountManager和AllocationEngine
