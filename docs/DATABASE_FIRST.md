# 数据库优先原则

## 核心原则

**所有数据读取必须从数据库查询，不允许使用Python随机生成的假数据。**

## 设计理念

### ✅ 正确的方式

1. **初始化阶段**：运行初始化脚本，往数据库插入假数据
   ```bash
   python scripts/mac/init_mock_data.py
   ```
   - 在SQLite中插入15个假策略、2个账户、10个信号、20个交易
   - 这些是真实存在于数据库中的记录

2. **读取阶段**：Dashboard API从数据库查询
   ```python
   @router.get("/strategies")
   def get_strategies(session: Session = Depends(get_db_session)):
       # ✅ 正确：从数据库查询
       strategies = session.query(Strategy).order_by(Strategy.created_at.desc()).all()
       return {"strategies": [s.to_dict() for s in strategies]}
   ```

3. **写入阶段**：新数据保存到数据库
   ```python
   # 生成新策略 → 插入数据库
   strategy = Strategy(id="STR_001", name="新策略", ...)
   session.add(strategy)
   session.commit()
   
   # 再次查询 → 策略总数+1
   total = session.query(Strategy).count()  # 16个
   ```

### ❌ 错误的方式

```python
@router.get("/strategies")
def get_strategies():
    # ❌ 错误：直接返回Python生成的随机数据
    strategies = []
    for i in range(15):
        strategies.append({
            "id": f"STR_{i}",
            "name": f"Strategy {i}",
            "sharpe_ratio": random.uniform(0.3, 1.5),  # 每次随机生成
            ...
        })
    return {"strategies": strategies}
```

**问题**：
- 每次请求都返回不同的随机数据
- 生成新策略后，总数不会增加（永远是15个）
- 数据不持久化，重启服务后丢失
- 无法真实测试增删改查功能

## 数据来源规则

### 从数据库读取（真实SQL查询）

| 数据类型 | API路由 | 数据库表 |
|---------|---------|----------|
| 策略列表 | `GET /api/strategies` | `strategies` |
| 策略详情 | `GET /api/strategies/{id}` | `strategies` |
| 信号列表 | `GET /api/signals` | `signals` |
| 交易列表 | `GET /api/trades` | `trades` |
| 账户列表 | `GET /api/accounts` | `accounts` |
| 统计数据 | `GET /api/stats` | 聚合查询多张表 |

### 操作数据库（真实SQL写入）

| 操作 | API路由 | SQL操作 |
|-----|---------|---------|
| 生成策略 | `POST /actions/generate-strategies` | `INSERT INTO strategies` |
| 激活策略 | `POST /registration/activate/{id}` | `UPDATE strategies SET status='active'` |
| 停用策略 | `POST /registration/deactivate/{id}` | `UPDATE strategies SET status='candidate'` |
| 删除策略 | `DELETE /registration/delete/{id}` | `DELETE FROM strategies` |

### 例外：MT5 Worker状态

**唯一允许不从数据库读取的数据：MT5 Worker连接状态**

原因：Mac环境无法连接真实Windows MT5机器

处理方式：
```python
@router.get("/mt5/workers")
async def get_mt5_workers():
    """获取MT5 Workers状态"""
    try:
        # 尝试调用真实的Execution服务
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{EXECUTION_URL}/mt5/workers")
            return response.json()
    except httpx.TimeoutException:
        # 连接超时 → 显示错误，不返回假数据
        return {"error": "连接超时", "workers": []}
    except httpx.ConnectError:
        # 服务未启动 → 显示错误
        return {"error": "Execution服务未启动", "workers": []}
```

**关键**：即使失败，也返回错误信息，不生成假数据。

## Mac环境架构

```
┌─────────────────────────────────────────────────────────────┐
│                      Mac开发环境                              │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │Dashboard │  │ Strategy │  │Execution │  │ Validator│   │
│  │  (8001)  │  │  (8000)  │  │  (8003)  │  │  (8004)  │   │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘   │
│       │             │               │             │          │
│       └─────────────┴───────────────┴─────────────┘          │
│                         ↓                                     │
│                ┌─────────────────┐                           │
│                │  SQLite数据库    │                           │
│                │ (data/evo.db)   │                           │
│                │                 │                           │
│                │ - strategies    │← 15个假策略（初始化）     │
│                │ - signals       │← 10个假信号               │
│                │ - trades        │← 20个假交易               │
│                │ - accounts      │← 2个假账户                │
│                └─────────────────┘                           │
│                                                               │
│  特点：                                                        │
│  ✅ 所有服务真实运行                                          │
│  ✅ 数据持久化在SQLite                                        │
│  ✅ 可以真实测试增删改查                                      │
│  ❌ 无法连接Windows MT5（超时/错误显示）                     │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

## 数据流示例

### 场景1：查看策略列表

```
用户浏览器
   ↓ GET /api/strategies
Dashboard API
   ↓ SELECT * FROM strategies
SQLite数据库
   ↓ 返回35条记录
Dashboard API
   ↓ JSON响应
用户浏览器显示35个策略
```

### 场景2：生成新策略

```
用户点击"生成策略"按钮
   ↓ POST /actions/generate-strategies
Dashboard API
   ↓ 转发请求到 Strategy服务
Strategy服务
   ↓ 生成策略代码
   ↓ INSERT INTO strategies VALUES (...)
SQLite数据库
   ↓ 保存成功
   ↓ 返回strategy_id
Strategy服务
   ↓ 返回成功响应
Dashboard刷新数据
   ↓ GET /api/strategies
   ↓ SELECT * FROM strategies
SQLite数据库
   ↓ 返回36条记录（新增1个）
用户看到36个策略
```

### 场景3：激活策略

```
用户点击"激活策略"按钮
   ↓ POST /registration/activate/STR_001
Dashboard API
   ↓ UPDATE strategies SET status='active' WHERE id='STR_001'
SQLite数据库
   ↓ 更新成功
Dashboard刷新数据
   ↓ GET /api/strategies
   ↓ SELECT * FROM strategies
SQLite数据库
   ↓ STR_001的status已变成'active'
用户看到策略状态已更新
```

## 初始化流程

### 首次启动Mac环境

```bash
# 1. 初始化数据库假数据
cd /Users/frankzhang/repo-private/MT4-Factory
source venv/bin/activate
export DEVICE=mac
python scripts/mac/init_mock_data.py

# 输出：
# ✓ 插入 15 个策略
# ✓ 插入 2 个账户
# ✓ 插入 10 个信号
# ✓ 插入 20 个交易

# 2. 启动所有服务
./scripts/mac/start_all_services.sh

# 3. 访问Dashboard
open http://localhost:8001
```

### 数据持久化

- ✅ 数据保存在 `data/evo_trade.db`
- ✅ 重启服务，数据不丢失
- ✅ 新生成的策略永久保存
- ✅ 可以用SQLite客户端直接查看

```bash
# 查看数据库内容
sqlite3 data/evo_trade.db
> SELECT COUNT(*) FROM strategies;
35
> SELECT id, name, status FROM strategies LIMIT 5;
```

## 代码检查清单

编写Dashboard API时，确保：

- [ ] 使用 `session.query()` 从数据库查询
- [ ] 使用 `session.add()` / `session.commit()` 保存数据
- [ ] 不使用 `random.randint()` / `random.uniform()` 生成数据
- [ ] 不使用 `MockDataGenerator.get_mock_xxx()` 直接返回
- [ ] 从 `src.common.models` 导入数据模型
- [ ] 使用 `Depends(get_db_session)` 获取数据库连接

## 总结

**数据库是唯一的真相源（Single Source of Truth）**

- 初始化：往数据库插入假数据
- 读取：从数据库查询
- 写入：保存到数据库
- 展示：显示数据库中的真实数据

**不允许在API层面动态生成随机数据！**
