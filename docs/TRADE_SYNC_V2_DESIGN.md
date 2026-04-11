# V2交易同步设计 - 如何匹配系统操作的交易

## 🎯 V2场景

同步MT5平台的**全部交易**，但需要识别哪些是系统执行的。

```
MT5账户的所有交易（200条）
    ↓
同步到trades表
    ↓
包含：
  - 系统策略执行的：150条  ← 需要匹配出来
  - 用户手动下单的：30条
  - 其他EA/工具的：20条
```

---

## 🔍 核心问题

**如何判断一条MT5交易是系统执行的？**

---

## 💡 方案设计

### **方案1：通过订单备注（Comment）匹配** ⭐ 推荐

#### 实现逻辑

```python
# 1. 系统下单时写入标识
def execute_signal(signal: Signal):
    request = OrderRequest(
        symbol=signal.symbol,
        action=signal.direction.value,
        volume=signal.volume,
        comment=f"SYS_{signal.strategy_id}_{signal.id}"
        #       ↑ 系统标识   ↑ 策略ID      ↑ 信号ID
    )
    result = mt5_client.order_send(request)
    
    # 保存交易记录
    trade = Trade(
        ticket=result.ticket,
        strategy_id=signal.strategy_id,  # ✅ 已知策略ID
        signal_id=signal.id,
        ...
    )

# 2. 同步时根据comment匹配
def sync_trades_from_mt5(account_id: str):
    # 获取MT5所有交易
    mt5_deals = mt5_client.deals_get()
    
    for deal in mt5_deals:
        # 检查是否已存在
        existing = session.query(Trade).filter(
            Trade.ticket == deal.ticket
        ).first()
        
        if existing:
            continue  # 已同步过
        
        # 解析comment判断是否是系统交易
        comment = deal.comment or ""
        
        if comment.startswith("SYS_"):
            # 系统交易，解析策略ID和信号ID
            parts = comment.split("_")
            strategy_id = parts[1] if len(parts) > 1 else None
            signal_id = parts[2] if len(parts) > 2 else None
            
            trade = Trade(
                ticket=deal.ticket,
                account_id=account_id,
                strategy_id=strategy_id,  # ✅ 从comment解析
                signal_id=signal_id,
                ...
            )
        else:
            # 手动交易或其他
            trade = Trade(
                ticket=deal.ticket,
                account_id=account_id,
                strategy_id=None,  # ❌ 无策略ID
                signal_id=None,
                source="manual",  # 标记来源
                ...
            )
        
        session.add(trade)
```

#### Comment格式设计

```python
# 格式：SYS_{strategy_id}_{signal_id}
"SYS_STR_8a12e1ad_SIG_12345678"
 ↑    ↑              ↑
系统  策略ID         信号ID
```

#### 优点
- ✅ 简单可靠
- ✅ MT5原生支持comment字段
- ✅ 下单和同步都能识别
- ✅ 可追溯到具体信号

#### 缺点
- ⚠️ comment长度有限（可能<64字符）
- ⚠️ 如果手动修改comment会丢失标识

---

### **方案2：维护订单映射表**

#### 数据库设计

```python
class SystemOrderMapping(Base):
    """系统订单映射表"""
    __tablename__ = "system_order_mappings"
    
    ticket = Column(BigInteger, primary_key=True)  # MT5订单号
    signal_id = Column(String(32), nullable=False)
    strategy_id = Column(String(32), nullable=False)
    created_at = Column(DateTime, default=datetime.now)
```

#### 实现逻辑

```python
# 1. 系统下单时记录映射
def execute_signal(signal: Signal):
    result = mt5_client.order_send(...)
    
    # 记录映射
    mapping = SystemOrderMapping(
        ticket=result.ticket,
        signal_id=signal.id,
        strategy_id=signal.strategy_id
    )
    session.add(mapping)
    
    # 保存交易记录
    trade = Trade(
        ticket=result.ticket,
        strategy_id=signal.strategy_id,
        ...
    )

# 2. 同步时查询映射
def sync_trades_from_mt5(account_id: str):
    mt5_deals = mt5_client.deals_get()
    
    for deal in mt5_deals:
        # 查询映射表
        mapping = session.query(SystemOrderMapping).filter(
            SystemOrderMapping.ticket == deal.ticket
        ).first()
        
        if mapping:
            # 系统交易
            trade = Trade(
                ticket=deal.ticket,
                strategy_id=mapping.strategy_id,  # ✅ 从映射表获取
                signal_id=mapping.signal_id,
                source="system",
                ...
            )
        else:
            # 手动交易
            trade = Trade(
                ticket=deal.ticket,
                strategy_id=None,
                source="manual",
                ...
            )
```

#### 优点
- ✅ 数据独立管理
- ✅ 不依赖MT5 comment
- ✅ 可以存储更多元数据

#### 缺点
- ⚠️ 需要额外的表
- ⚠️ 需要维护数据一致性

---

### **方案3：通过magic number（EA模式）**

如果使用EA模式下单：

```python
def execute_signal(signal: Signal):
    # EA使用magic number标识
    magic = generate_magic_number(signal.strategy_id)
    #       例如：策略ID的hash值
    
    request = OrderRequest(
        symbol=signal.symbol,
        magic=magic,  # ← EA标识
        ...
    )

def sync_trades_from_mt5():
    for deal in mt5_deals:
        if deal.magic in SYSTEM_MAGIC_RANGE:
            # 系统交易
            strategy_id = decode_strategy_from_magic(deal.magic)
            trade = Trade(
                ticket=deal.ticket,
                strategy_id=strategy_id,
                ...
            )
        else:
            # 手动交易
            trade = Trade(
                ticket=deal.ticket,
                strategy_id=None,
                ...
            )
```

#### 优点
- ✅ MT5/EA标准做法
- ✅ magic number是整数，效率高

#### 缺点
- ⚠️ 只适用于EA模式
- ⚠️ magic number范围有限
- ⚠️ 难以编码复杂信息

---

## 📊 Trade模型扩展（V2）

### **添加source字段**

```python
class Trade(Base):
    __tablename__ = "trades"
    
    id = Column(String(32), primary_key=True)
    account_id = Column(String(32), ForeignKey('accounts.id'))
    signal_id = Column(String(32), ForeignKey('signals.id'), nullable=True)
    strategy_id = Column(String(32), ForeignKey('strategies.id'), nullable=True)  # V2允许为空
    
    # V2新增字段
    source = Column(String(16), default="system")  # system/manual/other
    comment = Column(String(128))  # MT5 comment
    magic = Column(BigInteger)     # EA magic number
    
    ticket = Column(BigInteger, nullable=False)
    symbol = Column(String(10), nullable=False)
    ...
```

### **source字段说明**

| 值 | 说明 | strategy_id | 用途 |
|----|------|-------------|------|
| **system** | 系统策略执行的交易 | ✅ 有 | 策略性能统计 |
| **manual** | 用户手动下单 | ❌ 无 | 账户监控 |
| **other** | 其他EA/工具 | ❌ 无 | 完整性记录 |

---

## 🎨 UI设计（V2）

### **筛选器更新**

```html
<label>交易来源</label>
<select x-model="tradeFilters.source">
    <option value="all">全部交易</option>
    <option value="system">系统交易</option>
    <option value="manual">手动交易</option>
    <option value="other">其他来源</option>
</select>

<!-- 当选择"系统交易"时，显示策略状态筛选 -->
<select x-show="tradeFilters.source === 'system'" x-model="tradeFilters.strategy_status">
    <option value="all">全部策略</option>
    <option value="active">激活策略</option>
    <option value="candidate">候选策略</option>
    <option value="archived">归档策略</option>
</select>
```

### **表格显示**

| Ticket | 来源 | 策略ID | 状态 | 品种 | 方向 | 盈亏 |
|--------|------|--------|------|------|------|------|
| 123456 | 系统 | STR_xxx | ACTIVE | EURUSD | BUY | +100 |
| 123457 | 手动 | - | - | GBPUSD | SELL | +50 |
| 123458 | 其他 | - | - | USDJPY | BUY | -20 |

---

## 🔄 数据同步流程（V2）

```
┌──────────────────────────────────────┐
│         MT5账户                       │
│  - 系统订单（有标识）                 │
│  - 手动订单（无标识）                 │
│  - 其他EA订单                        │
└──────────────┬───────────────────────┘
               │ deals_get()
               ↓
┌──────────────────────────────────────┐
│    同步服务                           │
│                                      │
│  for deal in mt5_deals:              │
│    if deal.comment.startswith("SYS_"):│
│      → 系统交易，解析策略ID           │
│    else:                             │
│      → 手动交易，无策略ID             │
└──────────────┬───────────────────────┘
               │
               ↓
┌──────────────────────────────────────┐
│        trades表                       │
│                                      │
│  系统交易: source=system, 有策略ID    │
│  手动交易: source=manual, 无策略ID    │
└──────────────────────────────────────┘
```

---

## 📋 实施步骤（V1→V2）

### **阶段1：准备（在V1基础上）**
1. Trade模型添加source字段
2. 修改下单逻辑，comment加入标识
3. 创建映射表（可选）

### **阶段2：实现同步**
1. 实现`sync_trades_from_mt5()`函数
2. 根据comment/magic判断来源
3. 填充source和strategy_id

### **阶段3：UI更新**
1. 添加"交易来源"筛选器
2. 支持查看手动交易
3. 统计分离显示

---

## ✅ 推荐方案

**方案1（Comment标识）+ 方案2（映射表）组合**

### **下单流程**
```python
def execute_signal(signal: Signal):
    # 1. 下单时设置comment
    request = OrderRequest(
        comment=f"SYS_{signal.strategy_id}_{signal.id}"
    )
    result = mt5_client.order_send(request)
    
    # 2. 记录映射（双重保险）
    mapping = SystemOrderMapping(
        ticket=result.ticket,
        signal_id=signal.id,
        strategy_id=signal.strategy_id
    )
    session.add(mapping)
```

### **同步流程**
```python
def sync_trades_from_mt5():
    for deal in mt5_deals:
        # 优先从映射表查询
        mapping = query_mapping(deal.ticket)
        
        if mapping:
            strategy_id = mapping.strategy_id
            source = "system"
        elif deal.comment.startswith("SYS_"):
            # 从comment解析（备用）
            strategy_id = parse_comment(deal.comment)
            source = "system"
        else:
            # 手动交易
            strategy_id = None
            source = "manual"
        
        trade = Trade(
            ticket=deal.ticket,
            strategy_id=strategy_id,
            source=source,
            ...
        )
```

---

## 🎯 总结

| 方案 | 可靠性 | 复杂度 | 推荐 |
|------|--------|--------|------|
| **Comment标识** | ⭐⭐⭐⭐ | 低 | ✅ |
| **映射表** | ⭐⭐⭐⭐⭐ | 中 | ✅ |
| **Magic Number** | ⭐⭐⭐ | 低 | ⚠️ EA模式 |
| **组合方案** | ⭐⭐⭐⭐⭐ | 中 | ✅ 最佳 |

**推荐：Comment + 映射表组合，既简单又可靠！**
