# 交易记录与策略状态说明

## 🎯 核心业务逻辑

### **重要原则**

> **只有 ACTIVE 状态的策略才能产生交易！**

---

## 📊 策略状态与交易关系

### 策略的三种状态

| 状态 | 说明 | 能否交易 |
|------|------|---------|
| **CANDIDATE** | 候选策略（待激活） | ❌ 不能 |
| **ACTIVE** | 激活策略（正在运行） | ✅ 能 |
| **ARCHIVED** | 归档策略（已停用） | ❌ 不能 |

---

## 🔄 策略状态变化流程

```
策略注册
    ↓
CANDIDATE（候选）
    ↓
[人工评估/自动评估]
    ↓
✅ 激活操作
    ↓
ACTIVE（激活）━━━━┓
    ↓              ┃
开始产生交易      ┃ 
    ↓              ┃
[交易中...]       ┃
    ↓              ┃
⏸️ 停用操作       ┃
    ↓              ┃
ARCHIVED（归档）   ┃
                   ┃
    ┌──────────────┘
    ↓
🔄 恢复操作
    ↓
ACTIVE（重新激活）
```

---

## 💡 交易记录的"注册状态"列

### 显示逻辑

交易记录表格中的"注册状态"列显示的是**策略当前的状态**，而不是交易发生时的状态。

### 示例场景

#### 场景1：策略一直保持ACTIVE
```
时间线：
  2026-03-15: 策略STR_xxx 被激活（CANDIDATE → ACTIVE）
  2026-03-20: 产生交易 #1001（策略状态：ACTIVE）
  2026-03-25: 产生交易 #1002（策略状态：ACTIVE）
  2026-04-11: 查看交易记录

交易记录显示：
  Ticket  | 策略ID      | 注册状态  | ...
  --------|-------------|----------|-----
  #1001   | STR_xxx     | ACTIVE   | ...  ✅ 当前仍然ACTIVE
  #1002   | STR_xxx     | ACTIVE   | ...  ✅ 当前仍然ACTIVE
```

#### 场景2：策略后来被停用
```
时间线：
  2026-03-15: 策略STR_xxx 被激活（CANDIDATE → ACTIVE）
  2026-03-20: 产生交易 #1001（策略状态：ACTIVE）
  2026-03-25: 产生交易 #1002（策略状态：ACTIVE）
  2026-03-30: 策略被停用（ACTIVE → ARCHIVED）
  2026-04-11: 查看交易记录

交易记录显示：
  Ticket  | 策略ID      | 注册状态    | ...
  --------|-------------|------------|-----
  #1001   | STR_xxx     | ARCHIVED   | ...  ⚠️ 显示当前状态（已归档）
  #1002   | STR_xxx     | ARCHIVED   | ...  ⚠️ 显示当前状态（已归档）

说明：
  - 交易发生时，策略一定是ACTIVE的（否则不会产生交易）
  - 但"注册状态"列显示的是策略的当前状态
  - 策略后来被停用了，所以显示ARCHIVED
```

#### 场景3：手动交易（无策略）
```
时间线：
  2026-03-20: 用户手动下单（无策略ID）
  2026-04-11: 查看交易记录

交易记录显示：
  Ticket  | 策略ID      | 注册状态  | ...
  --------|-------------|----------|-----
  #2001   | (空)        | -        | ...  ✅ 手动交易，无策略
```

---

## 🔍 为什么CANDIDATE策略不会出现在交易记录中？

### 原因

1. **CANDIDATE是候选状态**
   - 策略刚注册，还在评估中
   - 尚未通过激活标准
   - 系统不会执行候选策略

2. **必须手动/自动激活**
   - 通过Dashboard点击"✅ 激活策略"
   - 或通过API: `POST /api/registration/activate/{strategy_id}`
   - 激活后状态变为ACTIVE

3. **只有ACTIVE才会被执行**
   - Orchestrator服务只调度ACTIVE策略
   - Execution服务只执行ACTIVE策略的信号
   - 信号生成API检查状态：`if strategy.status != ACTIVE: raise Error`

---

## ⚠️ 如果看到CANDIDATE策略的交易 = BUG！

如果交易记录中出现策略状态为CANDIDATE的交易，说明系统存在严重BUG：

### 可能的问题

1. **状态检查缺失**
   - 信号生成时未检查策略状态
   - 策略调度时未过滤CANDIDATE

2. **数据不一致**
   - 策略在交易后被错误地改回CANDIDATE
   - 数据库状态异常

3. **测试数据问题**
   - 手动插入的测试数据未遵守规则

---

## 🧪 假数据生成逻辑

### 正确的生成方式

```python
# ✅ 正确：只使用ACTIVE策略
active_strategies = session.query(Strategy).filter(
    Strategy.status == StrategyStatus.ACTIVE
).all()

for i in range(30):
    if random.random() < 0.7:
        # 从ACTIVE策略中随机选择
        strategy_id = random.choice(active_strategies).id
    else:
        # 手动交易（无策略）
        strategy_id = None
    
    trade = Trade(
        strategy_id=strategy_id,
        ...
    )
```

### 错误的生成方式

```python
# ❌ 错误：使用所有策略（包括CANDIDATE）
all_strategies = session.query(Strategy).all()  # 包含CANDIDATE！

for i in range(30):
    # 可能选到CANDIDATE策略 → 违反业务逻辑！
    strategy_id = random.choice(all_strategies).id
    trade = Trade(strategy_id=strategy_id, ...)
```

---

## 📋 验证清单

### 开发时检查

- [ ] 交易记录中所有有策略ID的交易，策略状态应该是ACTIVE或ARCHIVED
- [ ] 不应出现CANDIDATE状态的交易
- [ ] 手动交易（strategy_id为NULL）的"注册状态"显示为"-"或空

### 测试数据生成

- [ ] 先激活策略：`UPDATE strategies SET status = 'ACTIVE' WHERE ...`
- [ ] 确认有ACTIVE策略：`SELECT COUNT(*) FROM strategies WHERE status = 'ACTIVE'`
- [ ] 生成交易数据（只使用ACTIVE策略）
- [ ] 验证：`SELECT t.*, s.status FROM trades t LEFT JOIN strategies s ON t.strategy_id = s.id`

---

## 🎯 总结

| 关键点 | 说明 |
|--------|------|
| **交易时状态** | 交易产生时，策略一定是ACTIVE |
| **显示的状态** | UI显示的是策略的**当前状态** |
| **CANDIDATE** | 候选策略，**不会产生交易** |
| **ACTIVE** | 激活策略，**能产生交易** |
| **ARCHIVED** | 归档策略，**不再产生交易**（但可能有历史交易） |
| **手动交易** | strategy_id为NULL，注册状态显示"-" |

---

## 🔗 相关代码位置

- **策略状态检查**: `src/services/orchestrator/api/routes/signal.py:39-40`
- **交易记录API**: `src/services/dashboard/api/routes/data.py:100-118`
- **假数据生成**: `scripts/generate_fake_trades.py`
- **策略模型**: `src/common/models/strategy.py`
- **交易模型**: `src/common/models/trade.py`

---

**核心原则：只有ACTIVE策略才能产生交易！** ✅
