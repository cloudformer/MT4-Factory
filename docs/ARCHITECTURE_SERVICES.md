# 服务架构设计文档

## 服务端口分配（标准）

```
┌─────────────────────────────────────────────────────────────────┐
│                      MT4 Factory System                         │
└─────────────────────────────────────────────────────────────────┘

Port 8001 - Dashboard Service (前端 + API)
├── /                              前端HTML页面
├── /api/stats                     统计数据API
├── /api/strategies                策略数据API  
├── /api/signals                   信号数据API
├── /api/trades                    交易数据API
├── /api/actions/*                 操作API
└── /api/registration/*            策略注册API

Port 8002 - Orchestrator Service (纯API)
├── /signals                       信号管理
├── /registration/*                策略注册
├── /account/*                     账户管理
├── /accounts-db/*                 账户数据库
├── /portfolio/*                   组合管理
├── /risk/*                        风险管理
└── /evaluation/*                  信号评估

Port 8003 - Execution Service (纯API)
├── /execute                       执行订单
├── /positions                     持仓查询
└── /orders                        订单查询

Port 8000 - Strategy Service (纯API)
├── /strategies                    策略管理
├── /signals                       信号生成
└── /backtest                      回测接口
```

---

## 服务职责划分

### 1. Dashboard Service (8001)
**类型**: Web服务（前端 + API）
**职责**: 
- ✅ 提供Web界面（HTML/CSS/JS）
- ✅ 提供Dashboard数据聚合API
- ✅ 操作指令转发

**技术栈**:
- FastAPI (后端框架)
- Jinja2 (模板引擎)
- AlpineJS (前端交互)
- TailwindCSS (样式)

**启动方式**: 
```bash
uvicorn src.services.dashboard.api.app:app --host 0.0.0.0 --port 8001
```

---

### 2. Orchestrator Service (8002)
**类型**: 纯API服务（无前端）
**职责**: 
- ✅ 策略注册与管理
- ✅ 信号评估与调度
- ✅ 账户管理
- ✅ 风险控制
- ✅ 资金分配

**技术栈**:
- FastAPI (纯API)
- SQLAlchemy (数据库ORM)

**启动方式**: 
```bash
uvicorn src.services.orchestrator.api.app:app --host 0.0.0.0 --port 8002
```

---

### 3. Execution Service (8003)
**类型**: 纯API服务（无前端）
**职责**: 
- ✅ MT5订单执行
- ✅ 持仓管理
- ✅ 订单查询

**技术栈**:
- FastAPI (纯API)
- MetaTrader5 (Python包)

**启动方式**: 
```bash
uvicorn src.services.execution.api.app:app --host 0.0.0.0 --port 8003
```

---

### 4. Strategy Service (8000)
**类型**: 纯API服务（无前端）
**职责**: 
- ✅ 策略逻辑执行
- ✅ 信号生成
- ✅ 回测计算

**技术栈**:
- FastAPI (纯API)
- NumPy/Pandas (数据计算)

**启动方式**: 
```bash
uvicorn src.services.strategy.api.app:app --host 0.0.0.0 --port 8000
```

---

## 服务间通信

```
┌──────────────┐
│   Browser    │
└──────┬───────┘
       │ HTTP
       ↓
┌──────────────────────────────┐
│  Dashboard Service (8001)    │  ← 唯一的前端入口
│  - HTML页面                   │
│  - 聚合数据                   │
└──────┬───────────────────────┘
       │ HTTP Request
       ↓
   ┌───┴────┬──────────┬────────┐
   ↓        ↓          ↓        ↓
┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐
│8002 │ │8003 │ │8000 │ │其他 │  ← 纯API服务
│Orch │ │Exec │ │Stgy │ │...  │
└─────┘ └─────┘ └─────┘ └─────┘
```

---

## 为什么不前后端完全分离？

### ❌ 过度分离的问题
```
Frontend (8004) - 纯静态HTML
    ↓ 调用
Dashboard API (8001) - 纯数据接口
    ↓ 调用
Orchestrator (8002), Execution (8003)...
```

**缺点**:
1. **增加复杂度**: 多一层转发
2. **CORS问题**: 跨域配置复杂
3. **部署麻烦**: 需要Nginx等反向代理
4. **过度设计**: Dashboard不是大型SPA应用

### ✅ 当前方案优点
```
Dashboard (8001) - 前端 + API聚合层
    ↓ 调用
Orchestrator (8002), Execution (8003)...
```

**优点**:
1. **简洁清晰**: 对外只有一个UI入口
2. **易于维护**: 前端和API在一起便于调试
3. **性能更好**: 减少一层网络请求
4. **符合实际**: Dashboard本身就是展示层

---

## 删除的文件

### ❌ src/services/dashboard/main.py
**原因**: 
- 重复启动Dashboard服务
- 造成端口混乱
- 不符合专业架构

**替代方案**:
统一使用uvicorn启动：
```bash
uvicorn src.services.dashboard.api.app:app --port 8001
```

---

## 启动脚本优化

### 之前（混乱）
```bash
# 方式1
python src/services/dashboard/main.py    # 端口8004

# 方式2
uvicorn src.services.dashboard.api.app:app --port 8001
```

### 之后（统一）
```bash
# Dashboard (前端 + API)
uvicorn src.services.dashboard.api.app:app --port 8001

# Orchestrator (纯API)
uvicorn src.services.orchestrator.api.app:app --port 8002

# Execution (纯API)
uvicorn src.services.execution.api.app:app --port 8003

# Strategy (纯API)
uvicorn src.services.strategy.api.app:app --port 8000
```

---

## 架构原则

### 1. 单一职责原则（SRP）
- Dashboard: 展示层（前端 + 数据聚合）
- Orchestrator: 编排层（业务逻辑）
- Execution: 执行层（MT5交互）
- Strategy: 计算层（策略算法）

### 2. 接口隔离原则（ISP）
- 前端只和Dashboard API交互
- Dashboard API调用后端服务
- 后端服务之间互相隔离

### 3. 依赖倒置原则（DIP）
- 高层模块（Dashboard）不依赖低层模块（MT5）
- 通过API抽象层解耦

### 4. 开闭原则（OCP）
- 新增服务不影响现有服务
- 每个服务独立部署、独立扩展

---

## 部署建议

### 开发环境
```bash
# 一键启动所有服务
./scripts/start_all.sh
```

### 生产环境
```bash
# 使用Docker Compose
docker-compose up -d

# 或使用Supervisor管理进程
supervisord -c supervisord.conf
```

---

## 监控端点

每个服务都提供`/health`端点：

```bash
curl http://localhost:8001/health  # Dashboard
curl http://localhost:8002/health  # Orchestrator
curl http://localhost:8003/health  # Execution
curl http://localhost:8000/health  # Strategy
```

---

## 总结

✅ **清晰的职责划分**
- Dashboard (8001): 唯一的前端入口 + API聚合
- 其他服务: 纯API，无前端

✅ **专业的架构设计**
- 符合微服务原则
- 易于理解和维护
- 便于扩展和部署

✅ **避免重复**
- 删除main.py重复启动
- 统一使用uvicorn
- 端口规划清晰

✅ **人类友好**
- 一个端口访问UI（8001）
- 其他端口提供API（8000-8003）
- 文档清晰易读
