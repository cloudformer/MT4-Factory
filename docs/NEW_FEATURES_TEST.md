# 新功能测试指南

本文档说明如何测试最新完成的3个高优先级功能。

---

## 功能1：Execution服务增强

### 新增功能
✅ 风控管理 - 自动检查订单大小、持仓数量、每日亏损、最大回撤
✅ 错误重试 - 订单失败自动重试3次，间隔2秒
✅ 订单追踪 - 实时追踪活跃订单状态
✅ 自动平仓 - 支持手动/止损/止盈/风控平仓

### API端点

#### 1. 执行信号（增强版）
```bash
POST http://localhost:8003/api/execution/execute

{
  "signal_id": "signal_123",
  "account_id": "account_456"  # 可选，用于风控检查
}

响应：
{
  "success": true,
  "trade_id": "trade_789",
  "ticket": 12345678,
  "symbol": "EURUSD",
  "volume": 0.1,
  "open_price": 1.0850,
  "open_time": "2024-04-12T15:00:00Z",
  "message": "订单执行成功"
}
```

#### 2. 平仓订单
```bash
POST http://localhost:8003/api/execution/close

{
  "ticket": 12345678,
  "reason": "manual"  # manual, stop_loss, take_profit, risk
}

响应：
{
  "success": true,
  "ticket": 12345678,
  "symbol": "EURUSD",
  "close_price": 1.0865,
  "close_time": "2024-04-12T16:00:00Z",
  "profit": 15.0,
  "reason": "manual",
  "message": "平仓成功"
}
```

#### 3. 获取持仓
```bash
GET http://localhost:8003/api/execution/positions

响应：
{
  "total": 5,
  "positions": [
    {
      "ticket": 12345678,
      "symbol": "EURUSD",
      "direction": "buy",
      "volume": 0.1,
      "open_price": 1.0850,
      "open_time": "2024-04-12T15:00:00Z",
      "strategy_id": "strategy_123",
      "account_id": "account_456"
    }
  ]
}
```

#### 4. 同步持仓
```bash
POST http://localhost:8003/api/execution/sync

响应：
{
  "success": true,
  "message": "持仓同步完成"
}
```

#### 5. 获取风控配置
```bash
GET http://localhost:8003/api/execution/risk

响应：
{
  "max_order_size": 1.0,
  "max_daily_loss": 10000,
  "max_position_count": 10,
  "max_drawdown_percent": 20,
  "allowed_symbols": ["EURUSD", "GBPUSD", "USDJPY"],
  "current_positions": 5,
  "daily_stats": {...}
}
```

#### 6. 获取服务统计
```bash
GET http://localhost:8003/api/execution/stats

响应：
{
  "active_orders": 5,
  "risk_manager": {...},
  "mt5_connected": true
}
```

### 测试步骤

1. **启动Execution服务**
   ```bash
   # Windows
   scripts\windows\start_all.bat

   # Mac（仅测试，不执行真实交易）
   python -m src.services.execution.api.app
   ```

2. **测试风控检查**
   ```bash
   # 发送超过限制的订单（应被拒绝）
   curl -X POST http://localhost:8003/api/execution/execute \
     -H "Content-Type: application/json" \
     -d '{"signal_id": "test_signal", "account_id": "test_account"}'
   ```

3. **测试订单执行**
   - 创建一个测试信号
   - 调用execute端点
   - 检查是否创建了trade记录

4. **测试持仓追踪**
   - 执行几个订单
   - 调用 `/positions` 查看活跃订单
   - 调用 `/sync` 同步MT5状态

---

## 功能2：Validator多数据源

### 新增功能
✅ 支持3种数据源：Mock、数据库、实时MT5
✅ 按权重自动选择可用数据源
✅ 可指定首选数据源
✅ 数据源状态监控

### 数据源类型

| 类型 | 说明 | 使用场景 |
|------|------|----------|
| **Mock** | 生成随机K线 | 开发测试 |
| **Database** | 从historical_bars表读取 | 历史回测 |
| **Realtime** | 从MT5实时获取 | 实盘验证 |

### API端点

#### 1. 获取数据源信息
```bash
GET http://localhost:8080/api/data_sources

响应：
{
  "enabled_sources": [
    {
      "type": "mock",
      "weight": 0.2,
      "available": true
    },
    {
      "type": "database",
      "weight": 0.6,
      "available": true
    },
    {
      "type": "realtime",
      "weight": 0.2,
      "available": false
    }
  ],
  "available_count": 2
}
```

#### 2. 测试数据源
```bash
GET http://localhost:8080/api/data_sources/test?symbol=EURUSD&timeframe=H1&count=100

响应：
{
  "success": true,
  "symbol": "EURUSD",
  "timeframe": "H1",
  "requested_count": 100,
  "actual_count": 100,
  "first_bar": {
    "time": 1712916000,
    "open": 1.0850,
    "high": 1.0865,
    "low": 1.0845,
    "close": 1.0860,
    "tick_volume": 250
  },
  "last_bar": {...},
  "data_source": ["mock", "database"]
}
```

### 配置示例

在 `config/windows.yaml` 中配置：

```yaml
validator:
  data_sources:
    - type: "mock"
      weight: 0.2
      enabled: true

    - type: "database"
      weight: 0.6
      enabled: true

    - type: "realtime"
      weight: 0.2
      enabled: true
      mt5_host: "demo_1"
```

### 测试步骤

1. **启动Validator服务**
   ```bash
   # Windows
   docker-compose --profile dev up validator

   # Mac（使用Mock数据）
   python -m src.services.validator.concurrent_validator
   ```

2. **查看数据源状态**
   ```bash
   curl http://localhost:8080/api/data_sources
   ```

3. **测试不同数据源**
   ```bash
   # 测试EURUSD H1数据
   curl "http://localhost:8080/api/data_sources/test?symbol=EURUSD&timeframe=H1&count=500"
   
   # 测试GBPUSD D1数据
   curl "http://localhost:8080/api/data_sources/test?symbol=GBPUSD&timeframe=D1&count=1000"
   ```

4. **验证数据质量**
   - 检查返回的K线数量
   - 验证时间戳连续性
   - 检查OHLC价格合理性

---

## 功能3：Dashboard WebSocket实时推送

### 新增功能
✅ WebSocket实时连接
✅ 每2秒自动推送数据更新
✅ 自动重连机制（最多5次）
✅ 连接状态指示器
✅ 心跳保持连接

### WebSocket端点

```
ws://localhost:8001/ws
```

### 推送数据格式

```json
{
  "type": "update",
  "timestamp": "2024-04-12T15:00:00Z",
  "data": {
    "stats": {
      "total_strategies": 39,
      "active_strategies": 12,
      "candidate_strategies": 27,
      "total_signals": 156,
      "pending_signals": 5,
      "total_trades": 342,
      "open_trades": 8,
      "total_accounts": 3,
      "active_accounts": 2
    },
    "latest_strategies": [...],
    "latest_signals": [...],
    "latest_trades": [...]
  }
}
```

### UI变化

1. **头部状态指示器**
   - 🟢 绿点 + "实时" = WebSocket已连接
   - 🔴 红点 + "离线" = WebSocket断开

2. **自动数据更新**
   - 统计卡片实时更新
   - 策略列表自动刷新
   - 信号列表实时显示
   - 交易记录实时更新

3. **连接提示**
   - 连接成功：显示绿色Toast "实时推送已连接"
   - 连接失败：显示红色Toast "实时推送连接失败，请刷新页面"

### 测试步骤

1. **启动Dashboard服务**
   ```bash
   # Windows
   docker-compose --profile dev up dashboard

   # Mac
   python -m uvicorn src.services.dashboard.api.app:app --host 0.0.0.0 --port 8001
   ```

2. **打开浏览器**
   ```
   http://localhost:8001
   ```

3. **验证WebSocket连接**
   - 查看页面左上角状态指示器（应显示绿点 + "实时"）
   - 打开浏览器开发者工具 > Network > WS
   - 看到 `/ws` 连接状态为 `101 Switching Protocols`

4. **观察实时更新**
   - 统计数字每2秒更新一次
   - 创建新策略/信号/交易后，列表自动刷新
   - 不需要手动点击"刷新"按钮

5. **测试断线重连**
   - 停止Dashboard服务
   - 观察状态指示器变为红色 + "离线"
   - 重启Dashboard服务
   - 观察自动重连（最多5次尝试）

6. **测试心跳机制**
   - 保持页面打开30秒以上
   - 在开发者工具Console看到 "💓 心跳响应"

---

## 完整测试流程

### Windows环境（完整功能）

1. **启动所有服务**
   ```bash
   scripts\windows\start_all.bat
   ```

2. **验证服务状态**
   ```bash
   # Execution服务
   curl http://localhost:8003/health

   # Validator服务
   curl http://localhost:8080/health

   # Dashboard服务
   curl http://localhost:8001/health
   ```

3. **打开Dashboard**
   - 访问 http://localhost:8001
   - 查看WebSocket连接状态（左上角绿点）

4. **执行测试流程**
   ```
   a. 生成测试策略
   b. 创建测试信号
   c. 执行信号（Execution服务）
   d. 观察Dashboard实时更新
   e. 检查Validator数据源
   f. 测试风控拦截
   g. 测试订单平仓
   ```

### Mac环境（开发测试）

1. **启动Dashboard**
   ```bash
   python -m uvicorn src.services.dashboard.api.app:app --host 0.0.0.0 --port 8001
   ```

2. **启动Validator（可选）**
   ```bash
   python -m src.services.validator.concurrent_validator
   ```

3. **测试WebSocket和Mock数据**
   - WebSocket连接正常
   - 使用Mock数据源
   - UI实时更新正常

---

## 性能指标

### Execution服务
- 订单执行延迟：< 100ms（不含MT5网络延迟）
- 风控检查时间：< 10ms
- 重试间隔：2秒
- 持仓追踪：内存缓存，< 1ms

### Validator服务
- 数据源切换：< 50ms
- Mock数据生成：< 10ms（500根K线）
- 数据库查询：< 200ms（3000根K线）
- MT5实时获取：< 500ms（取决于网络）

### Dashboard WebSocket
- 推送间隔：2秒
- 数据查询：< 100ms
- 推送延迟：< 50ms
- 心跳间隔：30秒
- 重连延迟：指数退避，1s → 2s → 4s → 8s → 16s

---

## 常见问题

### Q1: WebSocket连接失败？
**A:** 检查Dashboard服务是否启动，端口8001是否被占用

### Q2: 风控检查总是拦截？
**A:** 检查 `config/windows.yaml` 中的 `execution.risk_limits` 配置

### Q3: Validator数据源不可用？
**A:** 
- Mock数据源始终可用
- Database需要historical_bars表有数据
- Realtime需要MT5连接成功

### Q4: Dashboard不实时更新？
**A:** 
- 检查WebSocket连接状态（左上角指示器）
- 查看浏览器Console是否有错误
- 确认后端推送循环正常运行

### Q5: Execution服务重试失败？
**A:** 
- 检查MT5连接状态
- 查看日志中的详细错误信息
- 确认信号数据格式正确

---

## 下一步改进

1. **Execution服务**
   - [ ] 添加订单修改功能（修改SL/TP）
   - [ ] 支持部分平仓
   - [ ] 增加更多风控规则（相关性检查）

2. **Validator服务**
   - [ ] 添加数据源优先级动态调整
   - [ ] 支持混合数据源（多源融合）
   - [ ] 增加数据质量检查

3. **Dashboard WebSocket**
   - [ ] 添加选择性订阅（只接收感兴趣的数据）
   - [ ] 支持历史数据回放
   - [ ] 增加性能图表可视化
