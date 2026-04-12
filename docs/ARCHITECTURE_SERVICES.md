# MT4-Factory 服务架构

## 系统总览

系统由**7个核心组件**组成，职责明确、互不重叠：

```
┌─────────────────────────────────────────────────────────────────┐
│                         MT4-Factory 系统                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  Dashboard   │  │   Strategy   │  │ Orchestrator │          │
│  │   (UI界面)   │  │  (策略生成)   │  │  (策略协调)  │          │
│  └──────────────┘  └──────────────┘  └──────┬───────┘          │
│                                              │                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────▼───────┐          │
│  │  Validator   │  │  Execution   │  │   Database   │          │
│  │ (策略验证)   │  │ (交易执行)   │  │  (数据存储)  │          │
│  └──────┬───────┘  └──────┬───────┘  └──────────────┘          │
│         │                 │                                      │
│         │ MT5WorkerPool   │ MT5WorkerPool                        │
│         │                 │                                      │
└─────────┼─────────────────┼──────────────────────────────────────┘
          │                 │
          ▼                 ▼
   ┌──────────────┐  ┌──────────────┐
   │ Windows Demo │  │ Windows Real │  ← 第7个组件
   │  MT5 + API   │  │  MT5 + API   │
   └──────────────┘  └──────────────┘
        (1个或多个)      (1个或多个Pool)
```

---

## 服务端口分配

```
Port 5000  - Dashboard Service (前端 + API)
Port 8001  - Strategy Service (策略生成)
Port 8002  - Orchestrator Service (策略协调)
Port 8003  - Execution Service (交易执行)
Port 8004  - Validator Service (策略验证)
Port 5432  - Database (PostgreSQL)
Port 9090+ - Windows MT5 API Bridge
```

---

## 1. Dashboard Service (端口5000)

**职责：**
- 提供Web UI界面
- 展示策略、信号、交易数据
- 用户交互入口

**技术栈：**
- FastAPI + Jinja2
- AlpineJS + TailwindCSS
- 端口：5000

**部署位置：**
- Mac：本地Python进程
- Windows/Cloud：Docker容器

**API端点：**
```
/                              前端HTML页面
/api/stats                     统计数据API
/api/strategies                策略数据API  
/api/signals                   信号数据API
/api/trades                    交易数据API
/api/actions/*                 操作API
/api/registration/*            策略注册API
```

**启动方式：**
```bash
uvicorn src.services.dashboard.api.app:app --host 0.0.0.0 --port 5000
```

---

## 2. Strategy Service (端口8001)

**职责：**
- 生成交易策略
- 策略参数配置
- 策略代码管理

**技术栈：**
- FastAPI
- Python策略生成器
- 端口：8001

**部署位置：**
- Windows/Cloud：Docker容器

**API端点：**
```
/strategies                    策略管理
/signals                       信号生成
/backtest                      回测接口
```

**启动方式：**
```bash
uvicorn src.services.strategy.api.app:app --host 0.0.0.0 --port 8001
```

---

## 3. Orchestrator Service (端口8002)

**职责：**
- 处理Strategy和Execution之间的协调
- 信号评估和过滤
- 账户分配和风控
- **通过Execution服务API下单（不直接连MT5）**

**技术栈：**
- FastAPI
- SQLAlchemy
- 端口：8002

**部署位置：**
- Windows/Cloud：Docker容器

**关键设计：**
- ❌ 不直接连接MT5
- ✅ 通过调用Execution服务的HTTP API来执行交易

**API端点：**
```
/signals                       信号管理
/registration/*                策略注册
/account/*                     账户管理
/accounts-db/*                 账户数据库
/portfolio/*                   组合管理
/risk/*                        风险管理
/evaluation/*                  信号评估
```

**启动方式：**
```bash
uvicorn src.services.orchestrator.api.app:app --host 0.0.0.0 --port 8002
```

---

## 4. Execution Service (端口8003)

**职责：**
- 真实账户交易执行
- 风险控制
- 仓位管理
- **内置MT5WorkerPool，管理多个Real Windows机器**

**技术栈：**
- FastAPI
- MT5WorkerPool（管理多台Windows MT5）
- 端口：8003

**部署位置：**
- Windows/Cloud：Docker容器

**MT5连接方式：**
```python
# src/services/execution/execution_service.py

class ExecutionService:
    def __init__(self):
        # 直接初始化MT5WorkerPool，管理多个Real Windows
        self.mt5_pool = MT5WorkerPool.from_config()
        
        # Pool自动从config读取所有enabled的real_worker
        # 支持负载均衡、标签路由、健康检查
        
    def place_order(self, symbol, action, volume, **kwargs):
        # 自动选择最优Worker下单
        result = self.mt5_pool.place_order(
            symbol=symbol,
            action=action,
            volume=volume,
            tags=["real"]  # 只路由到real workers
        )
        return result
```

**配置示例（config/cloud.yaml）：**
```yaml
execution:
  enabled: true

mt5_hosts:
  real_worker_icm_1:
    enabled: true
    host: "52.10.20.101"
    port: 9090
    tags: ["real", "icmarkets", "primary"]
    weight: 2
    
  real_worker_icm_2:
    enabled: true
    host: "52.10.20.102"
    port: 9090
    tags: ["real", "icmarkets", "backup"]
    weight: 1
```

**API端点：**
```
/execute                       执行订单
/positions                     持仓查询
/orders                        订单查询
```

**启动方式：**
```bash
uvicorn src.services.execution.api.app:app --host 0.0.0.0 --port 8003
```

---

## 5. Validator Service (端口8004)

**职责：**
- 模拟数据跑分（阶段1）
- 历史数据回测（阶段2）
- 实时测试跑分（阶段3）- **连接Demo Windows MT5实时跑分**
- **内置MT5WorkerPool，管理1个或多个Demo Windows机器**

**技术栈：**
- Python异步验证
- MT5WorkerPool（管理Demo Windows）
- 端口：8004

**部署位置：**
- Windows/Cloud：Docker容器

**MT5连接方式：**
```python
# src/services/validator/validator_service.py

class ValidatorService:
    def __init__(self):
        # 直接初始化MT5WorkerPool，管理Demo Windows
        self.mt5_pool = MT5WorkerPool.from_config()
        
        # Pool自动从config读取所有enabled的demo_worker
        # 将来可扩展多个Demo Worker并发跑分
        
    def validate_strategy_realtime(self, strategy):
        # 从Demo Worker获取实时数据
        worker = list(self.mt5_pool.workers.values())[0]
        bars = worker.client.get_bars(
            symbol="EURUSD",
            timeframe="H1",
            count=100
        )
        
        # 执行回测
        result = self.backtester.run(strategy, bars)
        return result
```

**配置示例（config/windows.yaml）：**
```yaml
validator:
  enabled: true
  data_sources:
    - type: synthetic
      weight: 0.2
    - type: historical
      weight: 0.6
    - type: realtime
      weight: 0.2

mt5_hosts:
  demo_worker_1:
    enabled: true
    host: "host.docker.internal"
    port: 9090
    login: 5049130509
    password: "your_password"
    server: "MetaQuotes-Demo"
    tags: ["demo", "validation"]
    
  demo_worker_2:    # 将来扩展多个Demo Worker并发验证
    enabled: false
    host: "host.docker.internal"
    port: 9091
    tags: ["demo", "validation"]
```

**启动方式：**
```bash
python -m src.services.validator.main
```

---

## 6. Database (端口5432)

**职责：**
- 数据持久化
- 策略、信号、交易记录存储
- 历史数据管理

**技术栈：**
- Mac：SQLite
- Windows：PostgreSQL容器
- Cloud：PostgreSQL RDS

**端口：**
- PostgreSQL：5432

**部署位置：**
- Mac：本地SQLite文件
- Windows：Docker容器
- Cloud：RDS托管服务

**数据量分级：**
```yaml
database:
  # Phase 1: 基础数据（策略、信号、交易）
  phase_1:
    strategies: ~1000条
    signals: ~10万条/月
    trades: ~1万条/月
    
  # Phase 2: 历史K线数据（回测用）
  phase_2:
    historical_bars:
      symbols: 28个货币对
      timeframes: [M1, M5, M15, M30, H1, H4, D1]
      range: 2年
      total: ~5000万条
      
  # Phase 3: 实时行情快照（未来扩展）
  phase_3:
    realtime_ticks: 按需存储
```

---

## 7. Windows MT5主机（Worker）

**职责：**
- 运行MT5终端
- 运行API Bridge（HTTP服务，端口9090）
- 提供MT5数据和交易能力

**组件：**
- Windows OS
- MetaTrader 5终端
- Python + MetaTrader5库
- API Bridge HTTP服务

**部署形式：**
- 物理Windows机器
- Windows VPS
- 数量：1台、多台、或Pool（配置驱动）

**启动方式：**
```bash
# 在Windows上执行
cd C:\path\to\MT4-Factory
scripts\windows_mt5_script\start_mt5_bridge.bat
```

**API Bridge端点：**
```
http://0.0.0.0:9090
  /health                      健康检查
  /login                       登录MT5
  /account                     账户信息
  /tick/{symbol}               实时报价
  /bars                        K线数据
  /order                       下单
  /positions                   持仓
  /position/{ticket}/close     平仓
```

## MT5连接架构

### Execution服务（Real账户）

```
┌─────────────────────────────────────┐
│ Execution服务 (Docker容器)           │
│ ├── 风险控制                         │
│ ├── 仓位管理                         │
│ └── MT5WorkerPool (内置)             │
│     ├── real_worker_icm_1            │
│     ├── real_worker_icm_2            │
│     └── real_worker_pep_1            │
└─────────────┬───────────────────────┘
              │ HTTP
              ▼
┌─────────────────────────────────────┐
│ Windows Real Machines                │
│ ├── 52.10.20.101:9090 (ICMarkets-1) │
│ ├── 52.10.20.102:9090 (ICMarkets-2) │
│ └── 52.10.20.103:9090 (Pepperstone) │
│     └── MT5终端 + API Bridge          │
└─────────────────────────────────────┘
```

### Validator服务（Demo账户）

```
┌─────────────────────────────────────┐
│ Validator服务 (Docker容器)           │
│ ├── 模拟数据跑分                     │
│ ├── 历史数据回测                     │
│ ├── 实时测试跑分                     │
│ └── MT5WorkerPool (内置)             │
│     ├── demo_worker_1                │
│     └── demo_worker_2 (可扩展)       │
└─────────────┬───────────────────────┘
              │ HTTP
              ▼
┌─────────────────────────────────────┐
│ Windows Demo Machines                │
│ ├── 192.168.1.101:9090 (Demo-1)     │
│ └── 192.168.1.102:9090 (Demo-2)     │
│     └── MT5终端 + API Bridge          │
└─────────────────────────────────────┘
```

---

## 关键设计决策

### 1. 统一使用MT5WorkerPool

**决策：Execution和Validator都使用MT5WorkerPool，直接在服务内初始化**

```python
# 两个服务代码一致
class ExecutionService:
    def __init__(self):
        self.mt5_pool = MT5WorkerPool.from_config()

class ValidatorService:
    def __init__(self):
        self.mt5_pool = MT5WorkerPool.from_config()
```

**理由：**
- ✅ 接口完全一致，代码简化
- ✅ Validator将来可扩展多个Demo Worker并发跑分
- ✅ 配置驱动，灵活扩展（通过config区分demo/real）
- ✅ 统一的负载均衡、健康检查、故障转移
- ✅ 连接代码稳定，不需要额外封装

### 2. 不需要单独的"MT5连接服务"

**决策：MT5连接逻辑内置在Execution和Validator服务内部**

**理由：**
- ✅ 简单清晰，减少服务数量
- ✅ 各服务职责明确
- ✅ 减少网络跳转延迟
- ✅ 避免单点故障

### 3. Windows机器就是Worker，不是独立服务

**决策：Windows机器只运行MT5+API Bridge，不运行业务服务**

**理由：**
- ✅ Windows职责单一：提供MT5能力
- ✅ 业务逻辑在Linux容器中，易于开发部署
- ✅ 通过HTTP解耦，Windows和容器独立演进

### 4. Orchestrator不直接连MT5

**决策：Orchestrator通过Execution服务API下单**

**理由：**
- ✅ 职责分离：Orchestrator负责协调，Execution负责执行
- ✅ 集中化风控：所有交易通过Execution统一管理
- ✅ 简化架构：避免多个服务都连MT5

---

## 服务通信

```
用户
  ↓ HTTP
Dashboard (Web UI)
  ↓ HTTP API
Orchestrator (协调器)
  ├─→ Strategy服务 (获取策略)
  ├─→ Execution服务 (执行交易)
  │     └─→ MT5WorkerPool
  │           └─→ Windows Real Machines
  └─→ Database (存储数据)

独立运行：
Validator (验证器)
  ├─→ Database (读取策略)
  └─→ MT5WorkerPool
        └─→ Windows Demo Machines
```

---

## 三环境部署

### Mac环境
```yaml
- Dashboard: ✅ 本地Python进程（端口5000）
- Database: ✅ SQLite文件
- 其他服务: ❌ 不运行
- 用途: UI测试、数据查看
```

**启动方式：**
```bash
# Mac上只启动Dashboard
cd /Users/frankzhang/repo-private/MT4-Factory
python -m src.services.dashboard.api.app
```

### Windows环境
```yaml
- 所有服务: ✅ Docker容器
- Database: ✅ PostgreSQL容器
- Windows MT5: ✅ 本机运行（host.docker.internal）
- 用途: 完整功能测试
```

**启动方式：**
```bash
# Windows上启动所有容器
docker-compose --profile dev up -d

# Windows上启动MT5 API Bridge
cd C:\path\to\MT4-Factory
scripts\windows_mt5_script\start_mt5_bridge.bat
```

### Cloud环境
```yaml
- 所有服务: ✅ Docker容器
- Database: ✅ PostgreSQL RDS
- Windows MT5: ✅ 远程VPS（多台Pool）
- 用途: 生产环境
```

**启动方式：**
```bash
# Cloud上启动生产容器
docker-compose --profile production up -d

# 远程Windows VPS上启动MT5 API Bridge
# （通过远程桌面连接到各台Windows VPS执行）
```

---

## 扩展性设计

### Validator扩展多个Demo Worker并发跑分

**当前：**
```yaml
mt5_hosts:
  demo_worker_1:
    enabled: true
```

**扩展后：**
```yaml
mt5_hosts:
  demo_worker_1:
    enabled: true
    tags: ["demo", "eurusd"]
  demo_worker_2:
    enabled: true
    tags: ["demo", "gbpusd"]
  demo_worker_3:
    enabled: true
    tags: ["demo", "usdjpy"]

validator:
  concurrency: 50  # 50个策略并发验证
```

**好处：**
- 多个Demo Worker并行验证不同品种
- 提高验证吞吐量
- 避免单点瓶颈

### Execution扩展更多Real Worker Pool

**当前：**
```yaml
mt5_hosts:
  real_worker_icm_1:
    enabled: true
  real_worker_icm_2:
    enabled: true
```

**扩展后：**
```yaml
mt5_hosts:
  # ICMarkets Pool
  real_worker_icm_1: {enabled: true, tags: ["real", "icmarkets", "primary"]}
  real_worker_icm_2: {enabled: true, tags: ["real", "icmarkets", "backup"]}
  
  # Pepperstone Pool
  real_worker_pep_1: {enabled: true, tags: ["real", "pepperstone"]}
  real_worker_pep_2: {enabled: true, tags: ["real", "pepperstone"]}
  
  # 地区Pool
  real_worker_asia_1: {enabled: true, tags: ["real", "asia", "low_latency"]}
  real_worker_us_1: {enabled: true, tags: ["real", "us"]}

worker_pool:
  routing_rules:
    - name: "亚洲时段优先"
      condition: {trading_session: "asia"}
      target: {tags: ["asia"]}
    - name: "EURUSD专用"
      condition: {symbol: "EURUSD"}
      target: {tags: ["icmarkets"]}
```

---

## 总结

**7个核心组件，职责明确：**
1. Dashboard - UI界面（端口5000）
2. Strategy - 策略生成（端口8001）
3. Orchestrator - 策略协调（端口8002，通过Execution API下单）
4. Execution - 交易执行（端口8003，内置MT5WorkerPool管理Real Workers）
5. Validator - 策略验证（端口8004，内置MT5WorkerPool管理Demo Workers）
6. Database - 数据存储（SQLite/PostgreSQL）
7. Windows MT5 - Worker节点（1台或多台Pool）

**关键设计：**
- ✅ Execution和Validator统一使用MT5WorkerPool
- ✅ MT5连接逻辑直接在服务内初始化，代码稳定不变
- ✅ 配置驱动区分demo/real，无需改代码
- ✅ Windows机器就是Worker，不运行业务服务

**架构优势：**
- 简单清晰，没有冗余服务
- 职责分离，易于维护
- 灵活扩展，支持多Worker并发
- 配置驱动，环境适配
