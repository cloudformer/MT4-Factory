# MT5连接测试流程

## 完整测试步骤

### 步骤1：启动MT5终端（手动）

```
1. 双击桌面MT5图标（或从开始菜单）
2. 文件 → 登录到交易账户
3. 输入：
   - 账号: 5049130509
   - 密码: your_password
   - 服务器: MetaQuotes-Demo
4. 点击"登录"
5. 确认右下角显示"已连接"
6. 最小化到系统托盘（不要关闭）
```

✅ 验证：任务管理器中看到 `terminal64.exe` 进程

---

### 步骤2：启动MT5 API Bridge

```bash
# 在项目根目录执行
scripts\windows_mt5_script\start_mt5_bridge.bat
```

**预期输出**：
```
========================================
  MT5 API Bridge 启动
========================================

[✓] Python已安装
Python 3.11.0

[✓] MetaTrader5库已安装

[✓] MT5终端已运行 (terminal64.exe)

========================================
  启动API Bridge服务
========================================

监听地址: http://0.0.0.0:9090
API文档: http://localhost:9090/docs

INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:9090
```

✅ 验证：浏览器访问 `http://localhost:9090/docs` 能看到API文档

---

### 步骤3：测试API连接

#### 3.1 健康检查

```bash
# PowerShell或CMD
curl http://localhost:9090/health
```

**预期输出**：
```json
{
  "status": "ok",
  "mt5_initialized": true,
  "terminal_info": {
    "version": 2650,
    "build": 2650,
    "name": "MetaQuotes-Demo",
    "company": "MetaQuotes Software Corp.",
    "connected": true
  },
  "account_info": {
    "login": 5049130509,
    "server": "MetaQuotes-Demo",
    "balance": 100000.0
  }
}
```

#### 3.2 获取账户信息

```bash
curl http://localhost:9090/account
```

**预期输出**：
```json
{
  "login": 5049130509,
  "server": "MetaQuotes-Demo",
  "balance": 100000.0,
  "equity": 100000.0,
  "margin": 0.0,
  "margin_free": 100000.0,
  "currency": "USD"
}
```

#### 3.3 获取K线数据

```bash
curl "http://localhost:9090/bars?symbol=EURUSD&timeframe=H1&count=10"
```

**预期输出**：
```json
[
  {
    "time": "2024-04-11 10:00:00",
    "open": 1.08456,
    "high": 1.08523,
    "low": 1.08412,
    "close": 1.08489,
    "volume": 1234
  },
  ...
]
```

---

### 步骤4：测试Docker容器访问

#### 4.1 启动业务容器

```bash
scripts\windows\start_all.bat
```

#### 4.2 容器内测试连接

```bash
# 测试网络连通性
docker exec -it mt4-factory-validator ping -c 3 host.docker.internal

# 测试API访问
docker exec -it mt4-factory-validator curl http://host.docker.internal:9090/health
```

**预期输出**：
```
PING host.docker.internal (192.168.65.2): 56 data bytes
64 bytes from 192.168.65.2: icmp_seq=0 ttl=64 time=0.123 ms

{"status":"ok","mt5_initialized":true,...}
```

#### 4.3 查看Validator日志

```bash
docker-compose logs -f validator
```

**预期输出**：
```
validator    | [INFO] Loading config: config/windows.yaml
validator    | [INFO] MT5 host: demo_1
validator    | [INFO] MT5 API Bridge: host.docker.internal:9090
validator    | [INFO] Connecting to MT5...
validator    | [INFO] ✓ Connected to MT5: MetaQuotes-Demo (5049130509)
validator    | [INFO] Account balance: $100000.00
validator    | [INFO] Validator service started
```

---

## 常见测试问题

### Q1: curl命令返回空或错误？

**可能原因**：
- API Bridge未启动
- 端口被占用
- MT5终端未运行

**排查**：
```bash
# 1. 检查MT5进程
tasklist | findstr terminal

# 2. 检查端口
netstat -ano | findstr :9090

# 3. 重新启动API Bridge
scripts\windows_mt5_script\restart_mt5_bridge.bat
```

### Q2: 健康检查显示 mt5_initialized: false？

**原因**：API Bridge连接MT5失败

**解决**：
```python
# 手动测试MT5库
python -c "import MetaTrader5 as mt5; print(mt5.initialize())"

# 如果返回False，检查：
# 1. MT5终端是否运行
# 2. MT5是否已登录账户
# 3. Python是64位（与MT5匹配）
```

### Q3: Docker容器ping不通host.docker.internal？

**原因**：Docker网络配置问题

**解决**：
```yaml
# 检查 docker-compose.yml
services:
  validator:
    extra_hosts:
      - "host.docker.internal:host-gateway"  # 必须配置
```

重启Docker Desktop，再试。

---

## 配置文件中的参数如何使用？

### 情况1：MT5终端已登录（常见）

```yaml
# config/windows.yaml
mt5_hosts:
  demo_1:
    host: "localhost"              # API Bridge地址
    port: 9090                     # API Bridge端口
    login: 5049130509              # 不会使用（MT5已登录）
    password: "your_password"      # 不会使用
    server: "MetaQuotes-Demo"      # 不会使用
    use_investor: true
```

**流程**：
```python
# Validator/Execution代码
import requests

# 直接访问API Bridge
response = requests.get("http://localhost:9090/account")
# API Bridge返回当前MT5终端登录的账户信息
```

### 情况2：API Bridge自动登录（可选）

如果你希望API Bridge启动时自动登录MT5：

```python
# src/services/mt5_api_bridge/app.py

@app.on_event("startup")
async def startup_event():
    mt5.initialize()
    
    # 从配置文件读取账户信息
    login = config.get("mt5_hosts.demo_1.login")
    password = config.get("mt5_hosts.demo_1.password")
    server = config.get("mt5_hosts.demo_1.server")
    
    # 自动登录
    if login and password:
        mt5.login(login=login, password=password, server=server)
```

但通常不需要这样做，因为MT5终端已经手动登录了。

---

## 验证配置是否生效

### 测试脚本

创建测试脚本：`scripts/windows_mt5_script/test_connection.py`

```python
import requests
import sys

# 测试API Bridge连接
API_BASE = "http://localhost:9090"

def test_health():
    """健康检查"""
    try:
        resp = requests.get(f"{API_BASE}/health", timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            print("✓ 健康检查通过")
            print(f"  MT5初始化: {data.get('mt5_initialized')}")
            print(f"  账户: {data.get('account_info', {}).get('login')}")
            print(f"  服务器: {data.get('terminal_info', {}).get('name')}")
            return True
        else:
            print(f"✗ 健康检查失败: HTTP {resp.status_code}")
            return False
    except Exception as e:
        print(f"✗ 连接失败: {e}")
        return False

def test_account():
    """账户信息"""
    try:
        resp = requests.get(f"{API_BASE}/account", timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            print("✓ 获取账户信息成功")
            print(f"  账号: {data.get('login')}")
            print(f"  余额: ${data.get('balance'):.2f}")
            print(f"  净值: ${data.get('equity'):.2f}")
            return True
        else:
            print(f"✗ 获取账户信息失败: HTTP {resp.status_code}")
            return False
    except Exception as e:
        print(f"✗ 请求失败: {e}")
        return False

def test_bars():
    """K线数据"""
    try:
        resp = requests.get(
            f"{API_BASE}/bars",
            params={"symbol": "EURUSD", "timeframe": "H1", "count": 5},
            timeout=5
        )
        if resp.status_code == 200:
            data = resp.json()
            print(f"✓ 获取K线数据成功 (获取{len(data)}条)")
            if data:
                print(f"  最新K线: {data[0].get('time')} - Close: {data[0].get('close')}")
            return True
        else:
            print(f"✗ 获取K线数据失败: HTTP {resp.status_code}")
            return False
    except Exception as e:
        print(f"✗ 请求失败: {e}")
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("  MT5 API Bridge 连接测试")
    print("=" * 50)
    print()
    
    results = []
    
    print("[1/3] 健康检查...")
    results.append(test_health())
    print()
    
    print("[2/3] 账户信息...")
    results.append(test_account())
    print()
    
    print("[3/3] K线数据...")
    results.append(test_bars())
    print()
    
    print("=" * 50)
    if all(results):
        print("✓ 所有测试通过！")
        sys.exit(0)
    else:
        print("✗ 部分测试失败")
        sys.exit(1)
```

运行测试：
```bash
python scripts/windows_mt5_script/test_connection.py
```

---

## 总结

### ✅ 你需要做的

1. **手动启动MT5终端并登录**（必须）
2. **运行 start_mt5_bridge.bat**（启动HTTP服务）
3. **配置文件指向API Bridge**（host: localhost, port: 9090）

### ❌ 配置文件不能做的

- **不能替代MT5终端**（MT5必须独立运行）
- **login/password通常不会使用**（MT5已登录）
- **不是直接连接MT5**（是连接API Bridge）

### 🔗 正确的理解

```
配置文件 → API Bridge (localhost:9090) → MT5终端 (COM接口) → 经纪商服务器
```

**配置中的 host/port 是 API Bridge 的地址，不是 MT5 的地址！**
