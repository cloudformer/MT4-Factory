# MT5统一客户端使用指南

## 🎯 核心设计理念

### **统一接口，自动切换**

```python
from src.common.mt5 import UnifiedMT5Client

# 同一套代码，根据连接参数自动选择：
# - Windows + localhost → 本地直连MetaTrader5库
# - 其他情况 → HTTP API远程调用

client = UnifiedMT5Client(
    host="...",   # 通过host自动判断模式
    port=9090,
    login=...,
    password=...,
    server=...
)
```

**判断逻辑**：
- `host="localhost"` 或 `"127.0.0.1"` + Windows系统 → **本地模式**
- 其他（IP地址、域名、`host.docker.internal`） → **远程HTTP API模式**

---

## 🏗️ 架构概览

### **三层架构**

```
┌─────────────────────────────────────────────────────────┐
│  应用层（Validator / Execution服务）                     │
│  - 使用统一的 UnifiedMT5Client                           │
│  - 不关心本地/远程，只关心业务逻辑                        │
└─────────────────────────────────────────────────────────┘
                        │
                        │ 统一接口
                        ↓
┌─────────────────────────────────────────────────────────┐
│  UnifiedMT5Client（自动判断）                            │
│  ├─ 本地模式：直接调用 MetaTrader5 库                    │
│  └─ 远程模式：HTTP请求 → MT5 API Bridge                 │
└─────────────────────────────────────────────────────────┘
                        │
                        │
        ┌───────────────┴───────────────┐
        │                               │
        ↓ 本地直连                       ↓ HTTP API
┌─────────────────┐          ┌─────────────────┐
│  MT5 Terminal   │          │  MT5 API Bridge │
│  (Windows原生)   │          │  (FastAPI服务)  │
│                 │          │  ↓              │
│                 │          │  MT5 Terminal   │
└─────────────────┘          └─────────────────┘
```

---

## 📦 核心组件

### **1. UnifiedMT5Client（统一客户端）**

**文件**：`src/common/mt5/unified_client.py`

**功能**：
- 统一的MT5接口实现
- 自动检测本地/远程模式
- 支持所有MT5操作（获取数据、下单、查询持仓等）

**使用示例**：

```python
from src.common.mt5 import UnifiedMT5Client

# 创建客户端
client = UnifiedMT5Client(
    host="host.docker.internal",  # 容器访问宿主机
    port=9090,
    login=5049130509,
    password="your_password",
    server="MetaQuotes-Demo",
    timeout=10
)

# 初始化连接
if client.initialize():
    # 获取K线数据（最常用）
    df = client.get_bars("EURUSD", "H1", 100)
    print(f"获取到 {len(df)} 根K线")
    
    # 获取实时报价
    tick = client.symbol_info_tick("EURUSD")
    print(f"EURUSD: Bid={tick.bid}, Ask={tick.ask}")
    
    # 获取账户信息
    account = client.account_info()
    print(f"余额: {account.balance} {account.currency}")
    
    # 关闭连接
    client.shutdown()
```

---

### **2. MT5 API Bridge（HTTP包装器）**

**文件**：`src/services/mt5_api_bridge/app.py`

**功能**：
- FastAPI服务，运行在Windows上
- 包装MetaTrader5库，提供HTTP接口
- 允许远程容器通过HTTP访问MT5

**启动方式**：

```bash
# Windows命令行
cd MT4-Factory
python -m src.services.mt5_api_bridge.app

# 或使用启动脚本
scripts\start_mt5_api_bridge.bat
```

**API端点**：

| 端点 | 方法 | 用途 | Validator | Execution |
|------|------|------|-----------|-----------|
| `/health` | GET | 健康检查 | ✅ | ✅ |
| `/bars/{symbol}` | GET | 获取K线 | ✅ 常用 | ✅ |
| `/tick/{symbol}` | GET | 获取报价 | ✅ | ✅ |
| `/account` | GET | 账户信息 | ✅ | ✅ |
| `/order` | POST | 下单 | ❌ | ✅ 仅Execution |
| `/positions` | GET | 查询持仓 | ✅ | ✅ |

**测试API**：

```bash
# 健康检查
curl http://localhost:9090/health

# 获取K线（Validator最常用）
curl "http://localhost:9090/bars/EURUSD?timeframe=H1&count=100"

# 获取报价
curl http://localhost:9090/tick/EURUSD
```

---

## 🚀 部署场景

### **场景1：Windows本地开发**

```
Windows开发机：
  ├─ MT5 Terminal（本机）
  ├─ Python服务（本机venv）
  └─ UnifiedMT5Client(host="localhost")  ← 本地直连

优势：最快速度，零网络延迟
用途：快速开发测试
```

**配置**：

```yaml
# config/development.yaml
mt5:
  host: "localhost"
  port: 0  # 本地模式不使用
  login: 5049130509
  password: "your_password"
  server: "MetaQuotes-Demo"
```

---

### **场景2：Windows + Docker容器**

```
Windows开发机：
  ├─ MT5 Terminal（宿主机）
  ├─ MT5 API Bridge（宿主机，端口9090）⭐
  └─ Docker Desktop
      └─ Validator容器
          └─ UnifiedMT5Client(host="host.docker.internal", port=9090)

优势：
  ✅ 容器化验证
  ✅ 真实MT5数据
  ✅ 环境一致性
```

**启动流程**：

```bash
# 步骤1：启动MT5 API Bridge（Windows宿主机）
scripts\start_mt5_api_bridge.bat

# 步骤2：启动PostgreSQL（容器）
docker-compose up -d postgres

# 步骤3：启动Validator（容器）
docker-compose up -d validator
```

**配置**：

```yaml
# config/windows.yaml
validator:
  enabled: true
  concurrency: 20  # 单实例并发数
  mt5:
    host: "host.docker.internal"  # ⭐ Docker特殊地址
    port: 9090
    login: 5049130509
    password: "your_password"
    server: "MetaQuotes-Demo"
```

---

### **场景3：云端生产环境**

```
Linux服务器（业务逻辑）：
  ├─ Validator容器（7×24运行）
  ├─ Execution容器
  ├─ 其他服务容器
  └─ UnifiedMT5Client(host="52.xx.xx.xx", port=9090)
      ↓ HTTP API
Windows VPS（MT5专用）：⭐
  ├─ MT5 Terminal
  └─ MT5 API Bridge（端口9090）

优势：
  ✅ 关注点分离
  ✅ Linux服务器便宜
  ✅ Windows VPS专注MT5
  ✅ 真实交易隔离
```

**配置**：

```yaml
# config/production.yaml
validator:
  enabled: true
  concurrency: 20
  mt5:
    host: "52.10.20.30"  # ⭐ Windows VPS公网IP
    port: 9090
    api_key: "prod_validator_key_xxx"  # ⭐ 安全认证
    timeout: 15
```

---

## ⚡ 并发扩展策略

### **方案1：单实例高并发（推荐）**

```yaml
# config/windows.yaml
validator:
  concurrency: 50  # 提高并发数

效果：
  - 100个策略验证时间：10秒 → 4秒
  - 资源消耗：350MB → 500MB（可接受）
```

### **方案2：多实例扩展（高负载）**

```bash
# 启动3个Validator实例
docker-compose up -d validator1 validator2 validator3

# 每个实例并发20 → 总并发60

效果：
  - 300个策略验证时间：~10秒
  - 总资源：1GB内存，4-6核CPU
```

**docker-compose.yml配置**：

```yaml
services:
  validator1:
    image: mt4-factory-validator
    environment:
      - INSTANCE_ID=1
      - VALIDATOR_CONCURRENCY=20
    # ... 其他配置

  validator2:
    image: mt4-factory-validator
    environment:
      - INSTANCE_ID=2
      - VALIDATOR_CONCURRENCY=20

  validator3:
    image: mt4-factory-validator
    environment:
      - INSTANCE_ID=3
      - VALIDATOR_CONCURRENCY=20
```

### **方案3：多MT5 Worker节点（未来扩展）**

```
架构：
  Linux服务器（多个Validator实例）
      ↓ 负载均衡
  ┌─────────┬─────────┬─────────┐
  │ MT5     │ MT5     │ MT5     │
  │ Worker1 │ Worker2 │ Worker3 │
  └─────────┴─────────┴─────────┘

每个Worker：
  - 独立Windows VPS
  - 独立MT5 Terminal
  - 独立MT5 API Bridge
  - 可以连接不同的MT5经纪商

优势：
  ✅ 水平扩展
  ✅ 高可用（单点故障不影响全局）
  ✅ 多经纪商支持
  ✅ 负载均衡

配置示例：
```yaml
mt5_workers:
  - host: "52.10.20.30"
    port: 9090
    broker: "ICMarkets"
    weight: 1
  
  - host: "52.10.20.40"
    port: 9090
    broker: "Pepperstone"
    weight: 1
  
  - host: "52.10.20.50"
    port: 9090
    broker: "XM"
    weight: 1
```

---

## 🔐 安全最佳实践

### **开发环境**

```yaml
mt5:
  host: "host.docker.internal"
  port: 9090
  api_key: "demo_key_12345"  # 简单密钥即可
```

### **生产环境**

```yaml
mt5:
  host: "52.10.20.30"
  port: 9090
  api_key: "prod_STRONG_PASSWORD_WITH_RANDOM_CHARS_xxx"  # ⭐ 强密钥
  timeout: 15

# Windows VPS防火墙规则
firewall:
  - 只允许Linux服务器IP访问
  - 拒绝所有其他来源
```

### **真实交易账户**

```yaml
execution:
  mt5:
    host: "52.10.20.40"  # ⭐ 独立专用VPS
    port: 9091           # ⭐ 不同端口
    api_key: "execution_SUPER_STRONG_KEY_xxx"  # ⭐ 超强密钥
    
  risk_limits:
    max_order_size: 0.1
    max_daily_loss: 1000
    allowed_symbols: ["EURUSD", "GBPUSD"]
```

---

## 📊 性能测试

### **本地模式性能**

```python
# 测试：获取K线速度
import time
from src.common.mt5 import UnifiedMT5Client

client = UnifiedMT5Client(host="localhost")
client.initialize()

start = time.time()
df = client.get_bars("EURUSD", "H1", 1000)
elapsed = time.time() - start

print(f"本地模式：获取1000根K线耗时 {elapsed:.3f}秒")
# 典型结果：0.050-0.100秒
```

### **远程模式性能**

```python
# 测试：远程API速度
client = UnifiedMT5Client(
    host="52.10.20.30",
    port=9090
)
client.initialize()

start = time.time()
df = client.get_bars("EURUSD", "H1", 1000)
elapsed = time.time() - start

print(f"远程模式：获取1000根K线耗时 {elapsed:.3f}秒")
# 典型结果：0.200-0.500秒（取决于网络）
```

### **并发验证性能**

```
单Validator实例（并发20）：
  - 100策略验证：~10秒
  - 内存：350MB
  - CPU：2-4核

3个Validator实例（总并发60）：
  - 300策略验证：~10秒
  - 内存：1GB
  - CPU：6-8核
```

---

## ✅ 快速开始

### **Step 1：安装依赖**

```bash
# Windows
pip install MetaTrader5 fastapi uvicorn requests pandas

# Mac/Linux（开发环境）
pip install requests pandas  # 不需要MetaTrader5
```

### **Step 2：Windows启动MT5 API Bridge**

```bash
# Windows命令行
cd MT4-Factory
scripts\start_mt5_api_bridge.bat
```

### **Step 3：测试连接**

```python
from src.common.mt5 import UnifiedMT5Client

# 测试远程连接
client = UnifiedMT5Client(
    host="localhost",  # 或 host.docker.internal（容器内）
    port=9090
)

if client.initialize():
    print("✅ 连接成功")
    
    # 获取数据
    df = client.get_bars("EURUSD", "H1", 10)
    print(df)
    
    client.shutdown()
else:
    print("❌ 连接失败")
```

### **Step 4：启动Validator（容器）**

```bash
# 启动PostgreSQL
docker-compose up -d postgres

# 启动Validator
docker-compose up -d validator

# 查看日志
docker-compose logs -f validator
```

---

## 🎯 总结

### **核心优势**

```
✅ 统一接口
   - 同一套代码，本地和远程通用
   - Validator和Execution共享同一客户端

✅ 自动判断
   - 根据连接参数自动选择模式
   - 无需显式指定local/remote

✅ 灵活部署
   - 开发：Windows本地直连
   - 调试：Windows + Docker容器
   - 生产：Linux服务器 + Windows VPS Worker

✅ 易于扩展
   - 单实例提高并发数（20 → 50）
   - 多实例水平扩展（3×20 = 60并发）
   - 多Worker节点（未来支持）
```

### **设计理念**

```
📦 基础设施层：
   - UnifiedMT5Client（统一客户端）
   - MT5 API Bridge（HTTP包装器）

🚀 应用层：
   - Validator服务（策略验证）
   - Execution服务（真实交易）
   - Strategy服务（策略生成）

🔗 连接方式：
   - 本地：直连MetaTrader5库
   - 远程：HTTP API → MT5 Worker

🌐 未来扩展：
   - MT5 Worker池（多个Windows VPS）
   - 负载均衡
   - 多经纪商支持
```

**架构已就绪，可以开始实施！** 🚀
