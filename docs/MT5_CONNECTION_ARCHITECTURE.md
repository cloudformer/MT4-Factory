# MT5连接架构和依赖

## 完整架构图

```
┌─────────────────────────────────────────────────────────────────┐
│ 场景1: Windows本地开发                                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Windows宿主机                                                    │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                                                            │ │
│  │  1. MT5终端进程 (MetaTrader5.exe)                          │ │
│  │     └─ 登录: Demo账户 5049130509                           │ │
│  │     └─ 服务器: MetaQuotes-Demo                            │ │
│  │                                                            │ │
│  │  2. MT5 API Bridge (Python服务)                           │ │
│  │     └─ 监听: localhost:9090                                │ │
│  │     └─ 依赖: MetaTrader5 Python库                         │ │
│  │     └─ 连接MT5: 通过COM接口                                │ │
│  │                                                            │ │
│  │  ─────────────────────────────────────────────────────────  │ │
│  │                                                            │ │
│  │  3. Docker Desktop                                         │ │
│  │     └─ 容器: validator                                     │ │
│  │     └─ 容器: execution                                     │ │
│  │     └─ 通过 host.docker.internal:9090 访问API Bridge      │ │
│  │                                                            │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  连接流程:                                                        │
│  Validator容器 → host.docker.internal:9090 → MT5 API Bridge    │
│                  → COM接口 → MT5终端 → MetaQuotes服务器          │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ 场景2: Cloud生产环境（远程VPS）                                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Linux服务器 (Ubuntu/CentOS)                                     │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  Docker Compose                                            │ │
│  │  ├─ postgres                                               │ │
│  │  ├─ dashboard                                              │ │
│  │  ├─ validator   ────┐                                      │ │
│  │  └─ execution   ────┤                                      │ │
│  └─────────────────────┼─────────────────────────────────────┘ │
│                        │                                         │
│                        │ HTTP请求                                │
│                        │ 到 52.10.20.30:9090                     │
│                        ↓                                         │
│                                                                  │
│  Windows VPS (远程)                                              │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  IP: 52.10.20.30                                           │ │
│  │                                                            │ │
│  │  1. MT5终端进程 (MetaTrader5.exe)                          │ │
│  │     └─ 登录: Real账户 8012345678                           │ │
│  │     └─ 服务器: ICMarkets-Live                             │ │
│  │     └─ 7x24运行                                            │ │
│  │                                                            │ │
│  │  2. MT5 API Bridge                                         │ │
│  │     └─ 监听: 0.0.0.0:9090（对外开放）                      │ │
│  │     └─ 防火墙: 开放9090端口                                │ │
│  │                                                            │ │
│  │  3. 远程桌面 (mstsc)                                       │ │
│  │     └─ 用于管理和维护MT5                                   │ │
│  │     └─ 检查MT5运行状态                                     │ │
│  │                                                            │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  管理员通过mstsc远程连接VPS:                                      │
│  本地PC → mstsc → 52.10.20.30:3389 → Windows VPS桌面           │
└─────────────────────────────────────────────────────────────────┘
```

---

## 依赖清单

### 1. **Windows机器（宿主机或VPS）**

必须是Windows系统，因为：
- MT5终端仅支持Windows（.exe程序）
- MetaTrader5 Python库依赖Windows COM接口
- Linux无法直接运行MT5（除非用Wine，不推荐）

**推荐配置**：
- 系统: Windows 10/11 或 Windows Server 2019/2022
- CPU: 2核+
- 内存: 4GB+
- 网络: 稳定公网IP（Cloud环境）

---

### 2. **MT5终端进程 (MetaTrader5.exe)**

#### 下载和安装

```
官网下载: https://www.metatrader5.com/en/download
或从经纪商网站下载（ICMarkets、Pepperstone等）
```

#### 安装后需要

1. **登录MT5账户**
   - Demo账户：MetaQuotes提供
   - Real账户：从经纪商获取

2. **保持运行**
   - MT5终端必须一直运行
   - API Bridge通过COM接口连接MT5进程
   - 关闭MT5 = 断开连接

3. **自动登录配置**（生产环境）
   - 保存密码
   - Windows开机自启动
   - 断线自动重连

#### 验证MT5正常运行

```
任务管理器 → 查看进程:
  - terminal64.exe (或 terminal.exe)  ← MT5主进程
  - 右下角系统托盘有MT5图标
```

---

### 3. **MT5 API Bridge（中间件服务）**

#### 作用

```
Docker容器 (Linux) ─HTTP─→ API Bridge (Windows) ─COM─→ MT5终端
```

因为Docker容器是Linux环境，无法直接访问Windows的MT5进程，需要通过HTTP API中转。

#### 实现方式

**方案A: Python Flask服务（推荐）**

```python
# src/services/mt5_api_bridge/app.py
from flask import Flask, request, jsonify
import MetaTrader5 as mt5

app = Flask(__name__)

# 初始化MT5连接
mt5.initialize()

@app.route('/health', methods=['GET'])
def health():
    return {"status": "ok", "mt5_connected": mt5.terminal_info() is not None}

@app.route('/bars', methods=['GET'])
def get_bars():
    symbol = request.args.get('symbol')
    timeframe = request.args.get('timeframe')
    count = int(request.args.get('count', 100))
    
    # 从MT5获取K线数据
    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, count)
    return jsonify(rates.tolist())

@app.route('/order', methods=['POST'])
def place_order():
    data = request.json
    # 下单逻辑
    result = mt5.order_send(data)
    return jsonify(result._asdict())

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=9090)
```

#### 依赖

```bash
# Windows环境安装
pip install MetaTrader5
pip install flask

# requirements.txt
MetaTrader5==5.0.45
Flask==3.0.0
```

#### 启动方式

**本地开发（Windows宿主机）：**
```bash
# 在Windows PowerShell或CMD中
cd C:\path\to\MT4-Factory
python src/services/mt5_api_bridge/app.py

# 监听: 0.0.0.0:9090
```

**生产环境（Windows VPS）：**
```bash
# 作为Windows服务运行（nssm）
nssm install MT5-API-Bridge "C:\Python\python.exe" "C:\MT4-Factory\src\services\mt5_api_bridge\app.py"
nssm start MT5-API-Bridge
```

---

### 4. **MetaTrader5 Python库**

#### 安装

```bash
pip install MetaTrader5
```

#### 系统要求

- ✅ **仅Windows系统**
- ✅ MT5终端必须已安装
- ✅ 64位Python（推荐）

#### 功能

```python
import MetaTrader5 as mt5

# 初始化连接
mt5.initialize()

# 登录账户（可选，如果MT5已登录则不需要）
mt5.login(login=5049130509, password="xxx", server="MetaQuotes-Demo")

# 获取K线数据
rates = mt5.copy_rates_from_pos("EURUSD", mt5.TIMEFRAME_H1, 0, 100)

# 下单
request = {
    "action": mt5.TRADE_ACTION_DEAL,
    "symbol": "EURUSD",
    "volume": 0.1,
    "type": mt5.ORDER_TYPE_BUY,
    "price": mt5.symbol_info_tick("EURUSD").ask,
}
result = mt5.order_send(request)

# 关闭连接
mt5.shutdown()
```

---

### 5. **Docker Desktop（Windows本地开发）**

#### 安装

```
下载: https://www.docker.com/products/docker-desktop/
安装Docker Desktop for Windows
启用WSL 2（推荐）
```

#### 作用

运行业务容器（Validator、Execution等），容器通过`host.docker.internal`访问宿主机的MT5 API Bridge。

#### 网络配置

```yaml
# docker-compose.yml
services:
  validator:
    extra_hosts:
      - "host.docker.internal:host-gateway"  # 关键配置
```

Docker Desktop会自动将`host.docker.internal`解析为宿主机IP（通常是`192.168.65.2`或类似）。

---

### 6. **远程桌面连接 (mstsc) - Cloud环境**

#### 用途

管理远程Windows VPS：
- 登录MT5账户
- 启动/重启MT5终端
- 启动MT5 API Bridge服务
- 查看MT5交易状态
- 调试问题

#### 连接方式

```bash
# Windows本地
Win + R → 输入 mstsc → 输入VPS IP

# 或使用命令行
mstsc /v:52.10.20.30:3389
```

#### 登录信息

```
计算机: 52.10.20.30:3389
用户名: Administrator（或其他用户）
密码: VPS管理员密码
```

#### 连接后操作

1. 检查MT5是否运行（任务管理器）
2. 检查API Bridge是否运行（浏览器访问 `http://localhost:9090/health`）
3. 查看MT5交易日志
4. 重启服务（如果需要）

---

### 7. **防火墙配置（Cloud环境）**

#### Windows VPS防火墙

```powershell
# 开放MT5 API Bridge端口
New-NetFirewallRule -DisplayName "MT5 API Bridge" -Direction Inbound -LocalPort 9090 -Protocol TCP -Action Allow
```

#### 云服务商安全组（AWS/阿里云等）

```
入站规则:
  - 端口: 9090
  - 协议: TCP
  - 来源: 你的Linux服务器IP (52.10.20.10)
  - 说明: MT5 API Bridge

入站规则:
  - 端口: 3389
  - 协议: TCP  
  - 来源: 你的管理IP
  - 说明: 远程桌面
```

---

## 完整启动流程

### Windows本地开发环境

```bash
# 步骤1: 启动MT5终端
双击桌面MT5图标 → 登录Demo账户

# 步骤2: 启动MT5 API Bridge
cd C:\MT4-Factory
python src/services/mt5_api_bridge/app.py
# 输出: * Running on http://0.0.0.0:9090

# 步骤3: 验证API Bridge
浏览器访问: http://localhost:9090/health
# 输出: {"status": "ok", "mt5_connected": true}

# 步骤4: 启动Docker服务
cd C:\MT4-Factory
scripts\windows\start_all.bat

# 步骤5: 验证容器连接
docker-compose logs -f validator
# 应该看到: [INFO] Connected to MT5: demo_1 (host.docker.internal:9090)
```

### Cloud生产环境

```bash
# ========== Windows VPS (52.10.20.30) ==========

# 步骤1: 远程桌面连接
mstsc /v:52.10.20.30

# 步骤2: 启动MT5终端
启动MetaTrader5 → 登录Real账户 → 最小化到系统托盘

# 步骤3: 启动MT5 API Bridge（作为服务）
服务管理 → 启动 "MT5-API-Bridge"
# 或命令行: nssm start MT5-API-Bridge

# 步骤4: 验证API Bridge
浏览器: http://localhost:9090/health

# 步骤5: 配置防火墙
开放9090端口（入站规则）


# ========== Linux服务器 (52.10.20.10) ==========

# 步骤1: 配置环境变量
vi .env.production
# 添加MT5连接信息

# 步骤2: 启动Docker服务
bash scripts/cloud/start_all.sh

# 步骤3: 验证连接
docker-compose logs -f validator
# 应该看到: [INFO] Connected to MT5: demo_1 (52.10.20.30:9090)

# 步骤4: 测试API调用
curl http://localhost:8080/health
```

---

## 故障排查

### Q1: 容器连接不到MT5 API Bridge？

```bash
# 1. 验证API Bridge运行
# Windows宿主机执行:
curl http://localhost:9090/health

# 2. 验证容器网络
docker exec -it mt4-factory-validator ping host.docker.internal
docker exec -it mt4-factory-validator curl http://host.docker.internal:9090/health

# 3. 检查防火墙（Windows）
netsh advfirewall firewall show rule name="MT5 API Bridge"
```

### Q2: MetaTrader5库导入失败？

```python
# 错误: ModuleNotFoundError: No module named 'MetaTrader5'

# 解决:
pip install MetaTrader5

# 如果还是失败（非Windows系统）:
# MetaTrader5库仅支持Windows!
```

### Q3: MT5 API Bridge无法连接MT5终端？

```python
import MetaTrader5 as mt5

# 初始化失败
if not mt5.initialize():
    print("MT5 initialize failed")
    print(mt5.last_error())
    
# 常见原因:
# 1. MT5终端未运行 → 启动MT5
# 2. MT5终端未登录 → 登录账户
# 3. 权限问题 → 以管理员运行
```

### Q4: 远程VPS无法连接？

```bash
# 测试网络连通性
ping 52.10.20.30

# 测试端口
telnet 52.10.20.30 9090

# 检查防火墙规则（云服务商控制台）
# 检查Windows防火墙（mstsc连接VPS后）
```

---

## 最佳实践

### ✅ 推荐

1. **生产环境使用独立Windows VPS**
   - 7x24运行
   - 稳定公网IP
   - 充足内存（4GB+）

2. **MT5 API Bridge作为系统服务**
   ```bash
   # 使用nssm（Windows服务管理器）
   nssm install MT5-API-Bridge
   nssm start MT5-API-Bridge
   ```

3. **监控MT5连接状态**
   ```yaml
   # 定期健康检查
   healthcheck:
     test: ["CMD", "curl", "-f", "http://localhost:9090/health"]
     interval: 30s
   ```

4. **API Bridge添加认证**
   ```python
   # API密钥验证
   @app.before_request
   def verify_api_key():
       api_key = request.headers.get('X-API-Key')
       if api_key != os.getenv('MT5_API_KEY'):
           abort(401)
   ```

### ❌ 避免

1. ❌ Linux上运行MT5（不支持）
2. ❌ 容器内运行MT5（不推荐）
3. ❌ 公网暴露API Bridge无认证
4. ❌ 手动启动服务（应该自动化）

---

## 相关文档

- [MT5主机配置指南](../config/MT5_HOSTS_GUIDE.md)
- [Docker部署指南](./DOCKER_DEPLOYMENT.md)
- [MT5 API Bridge源码](../src/services/mt5_api_bridge/)
