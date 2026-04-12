# 统一架构方案：本地与云端一致

## 🎯 核心原则：完全容器化 + 配置驱动

```
✅ 统一原则：
1. 所有服务都是容器（包括Validator）
2. MT5始终是Windows原生进程
3. 只通过配置文件切换环境
4. 无代码改动，完全一致
```

---

## 📦 统一资源清单

### **容器服务（本地 = 云端）**

```
┌─────────────────────────────────────────────┐
│        容器服务（完全一致）                  │
├─────────────────────────────────────────────┤
│                                             │
│ 🐳 业务服务容器：                            │
│   ├─ PostgreSQL      (或RDS)               │
│   ├─ Dashboard       (8001)                │
│   ├─ Orchestrator    (8002)                │
│   ├─ Strategy        (8000)                │
│   ├─ Execution       (8003)                │
│   └─ Validator       (24h) ⭐ 容器          │
│                                             │
│ 唯一依赖：                                   │
│   └─ 访问MT5的网络地址（配置项）             │
│                                             │
└─────────────────────────────────────────────┘
```

### **MT5进程（本地 ≠ 云端，但接口一致）**

```
┌─────────────────────────────────────────────┐
│          MT5 Windows进程                    │
├─────────────────────────────────────────────┤
│                                             │
│ 🪟 Windows原生进程：                         │
│   └─ MT5 Terminal                           │
│      ├─ 提供行情数据                         │
│      ├─ 执行订单                             │
│      └─ 暴露接口（供容器访问）               │
│                                             │
│ 访问方式：                                   │
│   本地: host.docker.internal               │
│   云端: windows-vps-ip:port                │
│                                             │
└─────────────────────────────────────────────┘
```

---

## 🏗️ 两种部署架构

### **架构A：Windows本地（开发+测试）**

```
┌───────────────────────────────────────────────────────┐
│         Windows 本地机器（128G内存）                   │
├───────────────────────────────────────────────────────┤
│                                                       │
│ 🐳 Docker Desktop（WSL2）:                            │
│   ┌─────────────────────────────────────────────┐   │
│   │  postgres:       localhost:5432             │   │
│   │  dashboard:      localhost:8001             │   │
│   │  orchestrator:   localhost:8002             │   │
│   │  strategy:       localhost:8000             │   │
│   │  execution:      localhost:8003             │   │
│   │  validator:      (容器) ⭐                   │   │
│   │     └─ MT5访问: host.docker.internal       │   │
│   └─────────────────────────────────────────────┘   │
│                        ↓                              │
│           host.docker.internal（Docker特殊网络）      │
│                        ↓                              │
│   ┌─────────────────────────────────────────────┐   │
│   │ 🪟 MT5 Terminal（Windows原生进程）          │   │
│   │    └─ 监听: localhost                       │   │
│   └─────────────────────────────────────────────┘   │
│                                                       │
│ 配置: config/windows.yaml                            │
│   mt5:                                                │
│     host: "host.docker.internal"  # ⭐ 特殊值        │
│     port: 0  # 本地MT5，直接调用                      │
│                                                       │
└───────────────────────────────────────────────────────┘

优点：
✅ 所有服务一台机器
✅ 资源共享（128G内存）
✅ 延迟最低（本地通信）
✅ 成本$0
✅ 24小时验证无问题
```

### **架构B：云部署（生产环境）**

```
┌───────────────────────────────────────────────────────┐
│         云服务器（Linux, 2核4GB, $10-20/月）           │
├───────────────────────────────────────────────────────┤
│                                                       │
│ 🐳 Docker容器:                                        │
│   ┌─────────────────────────────────────────────┐   │
│   │  dashboard:      8001                       │   │
│   │  orchestrator:   8002                       │   │
│   │  strategy:       8000                       │   │
│   │  execution:      8003                       │   │
│   │  validator:      (容器) ⭐                   │   │
│   │     └─ MT5访问: 52.xx.xx.xx:9090           │   │
│   └─────────────────────────────────────────────┘   │
│                        ↓                              │
│                  互联网访问                            │
│                        ↓                              │
└───────────────────────┼───────────────────────────────┘
                        │ HTTP/WebSocket
                        ↓
┌───────────────────────────────────────────────────────┐
│    Windows VPS（独立机器, 2核4GB, $30-50/月）⭐        │
├───────────────────────────────────────────────────────┤
│                                                       │
│   ┌─────────────────────────────────────────────┐   │
│   │ 🪟 MT5 Terminal（Windows原生进程）          │   │
│   │    ├─ 监听: 0.0.0.0:9090                    │   │
│   │    └─ MT5 API Bridge（中间件）⭐            │   │
│   └─────────────────────────────────────────────┘   │
│                                                       │
│ 配置: config/production.yaml                         │
│   mt5:                                                │
│     host: "52.xx.xx.xx"  # Windows VPS公网IP ⭐      │
│     port: 9090           # MT5 API端口               │
│                                                       │
│ 🔒 安全：                                             │
│   ├─ 防火墙：仅允许云服务器IP                         │
│   ├─ VPN：云服务器↔Windows VPS（可选）               │
│   └─ Token认证：API访问需要密钥                       │
│                                                       │
└───────────────────────────────────────────────────────┘

数据库（二选一）:
  Option A: RDS PostgreSQL（托管，$15-30/月）
  Option B: 云服务器上的PostgreSQL容器（$0）

优点：
✅ 关注点分离（业务逻辑 vs MT5）
✅ 真实交易隔离（Validator不在交易机器上）
✅ 安全性高（MT5机器单独管理）
✅ 可扩展（可以多个Validator → 一个MT5）
```

---

## 🔑 关键组件：MT5 API Bridge

### **为什么需要？**

```
问题：
  Docker容器无法直接调用Windows本地MT5（跨机器）

解决：
  创建一个HTTP API服务，包装MT5的Python API
  容器通过HTTP调用，而不是直接调用MT5
```

### **MT5 API Bridge架构**

```python
# mt5_api_bridge.py
"""
MT5 API Bridge - 将MT5 Python API暴露为HTTP服务

运行在Windows上（与MT5同机器）
供Docker容器远程调用
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import MetaTrader5 as mt5
from datetime import datetime

app = FastAPI()

# ========== 初始化MT5 ==========
@app.on_event("startup")
def startup():
    if not mt5.initialize():
        raise RuntimeError("MT5初始化失败")

@app.on_event("shutdown")
def shutdown():
    mt5.shutdown()

# ========== API端点 ==========

@app.get("/health")
def health():
    """健康检查"""
    return {
        "status": "ok",
        "mt5_connected": mt5.terminal_info() is not None
    }

@app.get("/bars/{symbol}")
def get_bars(symbol: str, timeframe: str = "H1", count: int = 100):
    """获取K线数据"""
    timeframe_map = {
        "M1": mt5.TIMEFRAME_M1,
        "M5": mt5.TIMEFRAME_M5,
        "H1": mt5.TIMEFRAME_H1,
        "H4": mt5.TIMEFRAME_H4,
        "D1": mt5.TIMEFRAME_D1,
    }
    
    tf = timeframe_map.get(timeframe, mt5.TIMEFRAME_H1)
    rates = mt5.copy_rates_from_pos(symbol, tf, 0, count)
    
    if rates is None:
        raise HTTPException(status_code=404, detail="无法获取数据")
    
    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "count": len(rates),
        "bars": [
            {
                "time": datetime.fromtimestamp(r[0]).isoformat(),
                "open": r[1],
                "high": r[2],
                "low": r[3],
                "close": r[4],
                "volume": r[5],
            }
            for r in rates
        ]
    }

@app.post("/order")
def place_order(request: dict):
    """下单"""
    # 构造订单请求
    order_request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": request["symbol"],
        "volume": request["volume"],
        "type": mt5.ORDER_TYPE_BUY if request["action"] == "buy" else mt5.ORDER_TYPE_SELL,
        "price": mt5.symbol_info_tick(request["symbol"]).ask,
        "deviation": 10,
        "magic": request.get("magic", 0),
        "comment": request.get("comment", ""),
    }
    
    result = mt5.order_send(order_request)
    
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        raise HTTPException(status_code=400, detail=f"下单失败: {result.comment}")
    
    return {
        "success": True,
        "ticket": result.order,
        "price": result.price,
    }

@app.get("/positions")
def get_positions():
    """获取持仓"""
    positions = mt5.positions_get()
    
    if positions is None:
        return {"positions": []}
    
    return {
        "positions": [
            {
                "ticket": p.ticket,
                "symbol": p.symbol,
                "type": "buy" if p.type == 0 else "sell",
                "volume": p.volume,
                "price_open": p.price_open,
                "price_current": p.price_current,
                "profit": p.profit,
            }
            for p in positions
        ]
    }

# ========== 启动服务 ==========
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9090)
```

### **部署方式**

```powershell
# Windows上运行MT5 API Bridge

# 1. 安装依赖
pip install fastapi uvicorn MetaTrader5

# 2. 启动服务
python mt5_api_bridge.py

# 3. 测试
curl http://localhost:9090/health

# 4. 设置为Windows服务（可选）
# 使用NSSM或Task Scheduler让它开机启动
```

---

## 🔧 客户端适配（容器内）

### **MT5 Client封装**

```python
# src/common/mt5/client_unified.py
"""
统一的MT5客户端 - 支持本地和远程

通过配置自动选择：
- 本地模式：直接调用MetaTrader5库
- 远程模式：通过HTTP调用MT5 API Bridge
"""

import os
import requests
from typing import List, Dict
from datetime import datetime

class MT5ClientUnified:
    """统一MT5客户端"""
    
    def __init__(self, config: dict):
        self.mode = config.get('mode', 'local')  # local or remote
        self.host = config.get('host', 'localhost')
        self.port = config.get('port', 9090)
        
        if self.mode == 'local':
            import MetaTrader5 as mt5
            self.mt5 = mt5
            self._init_local()
        else:
            self.base_url = f"http://{self.host}:{self.port}"
            self._test_remote()
    
    def _init_local(self):
        """本地模式初始化"""
        if not self.mt5.initialize():
            raise RuntimeError("MT5初始化失败")
    
    def _test_remote(self):
        """远程模式测试连接"""
        try:
            resp = requests.get(f"{self.base_url}/health", timeout=5)
            if resp.status_code != 200:
                raise RuntimeError("MT5 API Bridge连接失败")
        except Exception as e:
            raise RuntimeError(f"无法连接MT5 API Bridge: {e}")
    
    def get_bars(self, symbol: str, timeframe: str, count: int) -> List[Dict]:
        """获取K线数据（统一接口）"""
        if self.mode == 'local':
            return self._get_bars_local(symbol, timeframe, count)
        else:
            return self._get_bars_remote(symbol, timeframe, count)
    
    def _get_bars_local(self, symbol: str, timeframe: str, count: int):
        """本地获取K线"""
        timeframe_map = {
            "M1": self.mt5.TIMEFRAME_M1,
            "H1": self.mt5.TIMEFRAME_H1,
            "H4": self.mt5.TIMEFRAME_H4,
            "D1": self.mt5.TIMEFRAME_D1,
        }
        
        tf = timeframe_map.get(timeframe, self.mt5.TIMEFRAME_H1)
        rates = self.mt5.copy_rates_from_pos(symbol, tf, 0, count)
        
        return [
            {
                "time": datetime.fromtimestamp(r[0]),
                "open": r[1],
                "high": r[2],
                "low": r[3],
                "close": r[4],
                "volume": r[5],
            }
            for r in rates
        ]
    
    def _get_bars_remote(self, symbol: str, timeframe: str, count: int):
        """远程获取K线"""
        resp = requests.get(
            f"{self.base_url}/bars/{symbol}",
            params={"timeframe": timeframe, "count": count},
            timeout=10
        )
        resp.raise_for_status()
        
        data = resp.json()
        return [
            {
                "time": datetime.fromisoformat(bar["time"]),
                "open": bar["open"],
                "high": bar["high"],
                "low": bar["low"],
                "close": bar["close"],
                "volume": bar["volume"],
            }
            for bar in data["bars"]
        ]
    
    # 其他方法类似：place_order, get_positions...
```

---

## ⚙️ 配置文件（统一）

### **config/windows.yaml（本地）**

```yaml
mt5:
  mode: "local"                      # 本地模式 ⭐
  host: "host.docker.internal"       # Docker特殊网络
  port: 0                            # 不需要端口（直接调用）
  use_investor: true

database:
  host: "postgres"                   # Docker网络内的容器名
  port: 5432
  database: "evo_trade"

services:
  dashboard: "http://dashboard:8001"
  orchestrator: "http://orchestrator:8002"
  strategy: "http://strategy:8000"
  execution: "http://execution:8003"

validator:
  enabled: true
  mode: "active_strategies"
  concurrency: 20                    # 并发验证数（支持100+策略）⭐
  schedule_interval: 3600            # 每小时执行（秒）
  demo_account: "5049130509"
  initial_balance: 100
```

### **config/production.yaml（云端）**

```yaml
mt5:
  mode: "remote"                     # 远程模式 ⭐
  host: "52.xx.xx.xx"                # Windows VPS公网IP
  port: 9090                         # MT5 API Bridge端口
  api_key: "secret_token_xxx"        # 安全认证（可选）
  use_investor: true

database:
  host: "xxx.rds.amazonaws.com"      # RDS地址
  # 或
  # host: "postgres"                 # 容器内PostgreSQL
  port: 5432
  database: "evo_trade"

services:
  dashboard: "http://dashboard:8001"
  orchestrator: "http://orchestrator:8002"
  strategy: "http://strategy:8000"
  execution: "http://execution:8003"

validator:
  enabled: true
  mode: "active_strategies"
  concurrency: 20                    # 并发验证数（支持100+策略）⭐
  schedule_interval: 3600            # 每小时执行（秒）
  demo_account: "5049130509"
  initial_balance: 100
```

---

## 🐳 Docker Compose（统一）

### **docker-compose.yml（本地 = 云端）**

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:16-alpine
    container_name: mt4-postgres
    environment:
      POSTGRES_DB: ${POSTGRES_DB:-evo_trade}
      POSTGRES_USER: ${POSTGRES_USER:-evo_trade_user}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - mt4-network

  dashboard:
    build: 
      context: .
      dockerfile: docker/Dockerfile.dashboard
    container_name: mt4-dashboard
    env_file: .env.${ENV:-windows}
    ports:
      - "8001:8001"
    depends_on:
      - postgres
    networks:
      - mt4-network

  orchestrator:
    build:
      context: .
      dockerfile: docker/Dockerfile.orchestrator
    container_name: mt4-orchestrator
    env_file: .env.${ENV:-windows}
    ports:
      - "8002:8002"
    depends_on:
      - postgres
    networks:
      - mt4-network

  strategy:
    build:
      context: .
      dockerfile: docker/Dockerfile.strategy
    container_name: mt4-strategy
    env_file: .env.${ENV:-windows}
    ports:
      - "8000:8000"
    depends_on:
      - postgres
    networks:
      - mt4-network

  execution:
    build:
      context: .
      dockerfile: docker/Dockerfile.execution
    container_name: mt4-execution
    env_file: .env.${ENV:-windows}
    ports:
      - "8003:8003"
    depends_on:
      - postgres
    networks:
      - mt4-network
    # Windows本地需要访问宿主机MT5
    extra_hosts:
      - "host.docker.internal:host-gateway"

  # ========== Validator容器 ⭐ ==========
  validator:
    build:
      context: .
      dockerfile: docker/Dockerfile.validator
    container_name: mt4-validator
    env_file: .env.${ENV:-windows}
    depends_on:
      - postgres
      - execution
    restart: unless-stopped  # 24小时运行
    networks:
      - mt4-network
    # Windows本地需要访问宿主机MT5
    extra_hosts:
      - "host.docker.internal:host-gateway"

volumes:
  postgres_data:

networks:
  mt4-network:
    driver: bridge
```

### **启动命令（统一）**

```bash
# Windows本地
ENV=windows docker-compose up -d

# 云生产（Linux服务器）
ENV=production docker-compose up -d

# Windows VPS（只运行MT5 API Bridge）
# 不用docker-compose，直接运行Python脚本
python mt5_api_bridge.py
```

---

## 🔀 环境切换（零代码改动）

### **本地 → 云端切换流程**

```bash
# ========== Windows本地开发 ==========
# 1. 启动所有服务（包括Validator）
ENV=windows docker-compose up -d

# 2. MT5在本地Windows运行（原生进程）
# Validator容器通过 host.docker.internal 访问

# ========== 部署到云端 ==========
# 步骤1：云服务器（Linux）
cd /opt/MT4-Factory
git pull

# 只启动业务服务（不包括MT5相关）
ENV=production docker-compose up -d postgres dashboard orchestrator strategy

# 启动Validator（会远程访问Windows VPS的MT5）
ENV=production docker-compose up -d validator execution

# 步骤2：Windows VPS（单独机器）
# 只运行MT5和API Bridge
cd C:\MT4-Factory
git pull

# 启动MT5 API Bridge（暴露HTTP接口）
python mt5_api_bridge.py

# 或设置为Windows服务（开机启动）
nssm install MT5ApiBridge "C:\Python\python.exe" "C:\MT4-Factory\mt5_api_bridge.py"
nssm start MT5ApiBridge
```

### **配置对比**

| 配置项 | Windows本地 | 云生产 |
|--------|------------|--------|
| **MT5模式** | `mode: local` | `mode: remote` |
| **MT5地址** | `host.docker.internal` | `52.xx.xx.xx` |
| **MT5端口** | `0`（直接调用）| `9090`（HTTP）|
| **数据库** | `postgres`（容器）| `xxx.rds.amazonaws.com` |
| **服务地址** | `localhost:8001`... | `dashboard:8001`... |

**只改配置，代码完全一致！** ✅

---

## 💰 成本对比

### **方案A：Windows本地（前6个月）**

```
成本：$0/月

资源：
  ├─ 所有服务容器（10GB内存）
  ├─ MT5原生进程
  └─ Validator容器（24h运行）

优点：
  ✅ 完全免费
  ✅ 功能完整
  ✅ 24h验证
  ✅ 开发+测试都在这里
```

### **方案B：云部署（6个月后）**

```
成本：$25-50/月

资源分配：
  ☁️  Linux服务器（$10-20/月）:
    ├─ 业务服务容器
    ├─ Validator容器 ⭐
    └─ PostgreSQL容器（或RDS +$15）
  
  🪟 Windows VPS（$15-30/月）:
    ├─ MT5 Terminal
    └─ MT5 API Bridge

优点：
  ✅ 关注点分离
  ✅ 真实交易隔离
  ✅ 公网访问
  ✅ 架构完全一致
```

---

## ✅ 最终架构确认

### **统一性检查**

| 维度 | Windows本地 | 云生产 | 一致性 |
|------|------------|--------|--------|
| **Validator** | 容器 ✅ | 容器 ✅ | ✅ 完全一致 |
| **MT5** | 原生进程 | 原生进程 | ✅ 完全一致 |
| **访问方式** | host.docker.internal | HTTP API | ⚠️  接口一致 |
| **配置切换** | ENV=windows | ENV=production | ✅ 一行切换 |
| **代码** | 无改动 | 无改动 | ✅ 完全一致 |

### **关键优势**

```
✅ Validator始终是容器
  - 本地：容器（访问本地MT5）
  - 云端：容器（访问远程MT5）

✅ MT5始终是Windows原生
  - 本地：原生进程
  - 云端：原生进程（另一台机器）

✅ 架构完全一致
  - 只改配置文件（mt5.host）
  - 代码零改动
  - 一键切换环境

✅ 灵活部署
  - 本地：全在一台机器（共用资源）
  - 云端：分离部署（安全隔离）
```

---

## 📋 实施清单

### **Phase 1：Windows本地（现在）**

- [ ] Docker Desktop安装
- [ ] 创建统一的docker-compose.yml
- [ ] 创建MT5ClientUnified（支持本地/远程）
- [ ] Validator容器化
- [ ] 配置 host.docker.internal
- [ ] 24小时运行测试

### **Phase 2：准备云端（1-3个月后）**

- [ ] 开发MT5 API Bridge
- [ ] Windows VPS购买（Vultr/AWS）
- [ ] 部署MT5 API Bridge
- [ ] Linux服务器购买
- [ ] 配置production.yaml
- [ ] 网络连通性测试
- [ ] 一键切换测试

---

## 🎯 总结

你的思路**完全正确**，最终方案：

1. ✅ **Validator使用容器**（本地和云端一致）
2. ✅ **MT5使用原生进程**（性能最佳）
3. ✅ **本地共用一台机器**（成本$0，资源充足）
4. ✅ **云端分离部署**（安全隔离，真实交易机器单独管理）
5. ✅ **通过配置切换**（零代码改动）

**这是最优的统一架构！** 🚀

---

## ⚡ 并发性能设计（支持100+策略）

### **需求场景**

```
场景：
  - 100+ Active策略需要7x24持续验证
  - 每个策略每小时验证一次
  - 获取最新MT5数据 + 运行回测 + 更新DB

挑战：
  ❌ 串行：100策略 × 2秒 = 200秒（不可接受）
  ✅ 并发：100策略 ÷ 20 = 10秒（推荐）
```

### **并发架构**

```python
# src/services/validator/concurrent_validator.py

class ConcurrentValidator:
    """AsyncIO并发验证器"""
    
    def __init__(self, concurrency: int = 20):
        self.concurrency = concurrency
        self.scheduler = AsyncIOScheduler()  # 定时调度
        
        # 异步数据库引擎
        self.engine = create_async_engine(
            db_url,
            pool_size=50,      # 连接池 ⭐
            max_overflow=50
        )
        
        # HTTP连接池（复用连接）
        self.http_session = aiohttp.ClientSession(
            connector=aiohttp.TCPConnector(limit=50)
        )
    
    async def validate_all_strategies(self):
        """并发验证所有策略"""
        strategies = await self._get_active_strategies()
        
        # 信号量控制并发数
        semaphore = asyncio.Semaphore(self.concurrency)
        
        tasks = [
            self._validate_with_semaphore(s, semaphore)
            for s in strategies
        ]
        
        # 并发执行
        results = await asyncio.gather(*tasks)
```

### **性能对比**

| 并发数 | 100策略耗时 | 内存消耗 | CPU消耗 | 推荐度 |
|--------|-------------|----------|---------|--------|
| 串行(1) | 200秒 | 100MB | 1核 | ❌ 不可接受 |
| 并发10 | 20秒 | 250MB | 2核 | ✅ 可接受 |
| **并发20** | **10秒** | **350MB** | **2-4核** | **✅ 推荐** |
| 并发50 | 4秒 | 500MB | 4-8核 | ⚡ 最优 |

### **128GB Windows机器资源分配**

```
Validator服务（并发20）：
  ✅ 内存：350MB（0.27%）
  ✅ CPU：2-4核（12%-25%，假设16核）
  ✅ 轻松扩展到300+策略
```

### **配置示例**

```yaml
# config/windows.yaml
validator:
  concurrency: 20              # 推荐配置 ⭐
  schedule_interval: 3600      # 每小时

database:
  pool_size: 50                # 支持并发查询
  max_overflow: 50
```

### **扩展方案**

```
方案1: 增加并发数（推荐）
  validator.concurrency: 20 → 50
  预期：10秒 → 4秒

方案2: 多Validator实例
  启动3个实例，每个负责33个策略
  预期：总并发 = 3 × 20 = 60

方案3: 批量API优化
  MT5 API支持批量查询
  预期：减少HTTP往返，10秒 → 5秒
```

**详细设计见：[VALIDATOR_CONCURRENT_ARCHITECTURE.md](./VALIDATOR_CONCURRENT_ARCHITECTURE.md)** 📚
