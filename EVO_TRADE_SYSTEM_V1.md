# Evo Trade System V1

**版本**: V1  
**日期**: 2026-04-10  
**状态**: ✅ 已完成

## 核心架构

### 四层架构模型（清晰分层）

```
┌─────────────────────────────────┐
│  Layer 1: Strategy 🎯           │  Port: 8001
│  策略层 - "想法"                 │
│  - AI 生成策略                   │
│  - 回测验证                      │
│  - 风控计算                      │
│  - 信号生成                      │
└─────────────────────────────────┘
           ↓
┌─────────────────────────────────┐
│  Layer 2: Orchestrator 🧠       │  Port: 8002
│  编排层 - "决策"                 │
│  - 策略注册表                    │
│  - 信号编排                      │
│  - 调度决策                      │
│  - 仓位管理                      │
│  - 资金分配                      │
└─────────────────────────────────┘
           ↓
┌─────────────────────────────────┐
│  Layer 3: Execution 📡          │  Port: 8003
│  执行层 - "执行"                 │
│  - 接收信号                      │
│  - MT5 对接                      │
│  - 订单执行                      │
│  - 持仓查询                      │
│  - 账户同步                      │
└─────────────────────────────────┘

┌─────────────────────────────────┐
│  Layer 4: Dashboard 📊          │  Port: 8004
│  API层 - "界面"                  │
│  - Web 可视化界面                │
│  - 数据展示                      │
│  - 操作控制                      │
│  - 实时监控                      │
└─────────────────────────────────┘
```

**架构原则**：
- **Strategy**: 专注策略逻辑，不碰MT5
- **Orchestrator**: 核心大脑，负责调度和决策
- **Execution**: 专门对接MT5，不含策略逻辑
- **Dashboard**: 统一入口，所有操作通过Web界面

## 已实现功能

### ✅ 分层架构
- **API层**: 路由、参数验证
- **Service层**: 业务逻辑
- **Repository层**: 数据访问

### ✅ 策略执行引擎
- **StrategyRunner**: 动态加载策略代码
- 真正执行策略的 `on_tick()` 方法
- 返回交易信号：'buy'/'sell'/None

### ✅ MT5 接口
- 自动环境检测（Windows: Real, macOS: Mock）
- K线数据获取
- 订单执行
- 持仓查询

### ✅ 数据库
- **SQLite**: 简单、无需安装
- 三张表：strategies, signals, trades
- 数据位置：`data/evo_trade.db`

### ✅ Web Dashboard
- **端口**: 8004
- **技术**: FastAPI + Jinja2 + TailwindCSS + Alpine.js
- **功能**:
  - 策略列表（含性能指标、代码查看）
  - 信号列表（实时状态）
  - 交易记录（盈亏统计）
  - 统计卡片（总数、盈亏）

## 工作流程

```
1. Strategy 生成策略代码
2. 保存到数据库（candidate状态）
3. Orchestrator 加载策略代码
4. 获取市场数据（MT5 K线）
5. 执行策略.on_tick(data)
6. 策略返回 'buy'/'sell'/None
7. Orchestrator 创建信号（调度决策）
8. Execution 执行订单（MT5对接）
9. 记录交易到数据库
10. Dashboard 展示所有数据
```

## 如何运行

```bash
# 1. 初始化数据库
python scripts/init_db.py

# 2. 启动服务（推荐）
./scripts/start_all_new.sh

# 或手动启动（4个终端）
python src/services/strategy/main.py      # 8001 - 策略层
python src/services/orchestrator/main.py  # 8002 - 编排层
python src/services/execution/main.py     # 8003 - 执行层
python src/services/dashboard/main.py     # 8004 - API层

# 3. 访问 Dashboard（所有操作都在这里）
浏览器打开: http://localhost:8004

# 点击按钮：
# - "生成策略" → 调用 Strategy 服务
# - "生成信号" → 调用 Orchestrator 服务
# - "执行" → 调用 Execution 服务

# 4. 或者直接测试 API
curl -X POST http://localhost:8001/strategies/generate -d '{"count": 2}'
curl -X POST http://localhost:8002/signals/generate -d '{"strategy_id": "STR_xxx"}'
```

## V1 限制

### 简化实现
- ❌ 未接入真实 AI（策略模板生成）
- ❌ 未实现真实回测引擎（使用模拟数据）
- ❌ 未实现 Evolution Engine（变异/淘汰）
- ❌ 未实现资金分配算法
- ❌ 未实现时间衰减

### 技术限制
- 单机部署
- SQLite（不支持高并发）
- 无自动信号监听（需手动触发）
- Dashboard 无实时刷新（需手动刷新）

## V2 规划

### 核心改进
- [ ] 接入 AI（OpenAI/Claude API）
- [ ] 真实回测引擎（Backtrader）
- [ ] Evolution Engine
  - [ ] 变异算法
  - [ ] 淘汰机制
  - [ ] 晋升流程
  - [ ] 时间衰减
- [ ] 资金分配算法
- [ ] 自动信号监听（后台循环）

### 技术改进
- [ ] 消息队列（RabbitMQ/Redis）
- [ ] Web Dashboard
- [ ] 监控告警
- [ ] 多账户支持
- [ ] Docker 容器化

---

**V1 完成时间**: 2026-04-10  
**V2 开始时间**: TBD
