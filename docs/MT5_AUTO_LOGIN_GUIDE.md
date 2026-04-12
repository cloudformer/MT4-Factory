# MT5自动登录指南

## 架构说明

```
┌─────────────────────────────────────────────────────┐
│ Execution/Orchestrator (Linux容器)                  │
├─────────────────────────────────────────────────────┤
│                                                     │
│  1. 读取 config/windows.yaml                        │
│     mt5_hosts:                                      │
│       demo_1:                                       │
│         host: "host.docker.internal"                │
│         port: 9090                                  │
│         login: 5049130509          ← 读取这些      │
│         password: "your_password"  ← 读取这些      │
│         server: "MetaQuotes-Demo"  ← 读取这些      │
│                                                     │
│  2. 创建MT5Client                                   │
│     client = MT5Client.from_config("demo_1")       │
│                                                     │
│  3. 自动发送登录请求                                 │
│     POST http://host.docker.internal:9090/login    │
│     Body: {login, password, server}                │
│                                                     │
└─────────────────────────────────────────────────────┘
                        ↓ HTTP
┌─────────────────────────────────────────────────────┐
│ Windows MT5 API Bridge                              │
├─────────────────────────────────────────────────────┤
│                                                     │
│  4. 接收登录请求                                     │
│     POST /login                                     │
│                                                     │
│  5. 调用MT5库登录                                    │
│     mt5.login(                                      │
│       login=5049130509,                            │
│       password="your_password",                    │
│       server="MetaQuotes-Demo"                     │
│     )                                              │
│                                                     │
└─────────────────────────────────────────────────────┘
                        ↓ COM接口
┌─────────────────────────────────────────────────────┐
│ MT5终端进程 (MetaTrader5.exe)                       │
├─────────────────────────────────────────────────────┤
│                                                     │
│  6. 接收登录指令                                     │
│     使用账号密码连接做市商服务器                      │
│                                                     │
└─────────────────────────────────────────────────────┘
                        ↓ 网络
┌─────────────────────────────────────────────────────┐
│ 做市商服务器 (MetaQuotes-Demo / ICMarkets-Live)     │
└─────────────────────────────────────────────────────┘
```

---

## 前置条件

### Windows系统（必须）

1. **MT5终端已安装**
   - 下载：https://www.metatrader5.com/en/download
   - **不需要手动登录！** API Bridge会自动登录

2. **MT5终端正在运行**
   ```bash
   # 启动MT5（双击桌面图标）
   # 可以不登录账户，留在登录界面也可以
   ```

3. **MT5 API Bridge运行**
   ```bash
   scripts\windows_mt5_script\start_mt5_bridge.bat
   ```

---

## 配置文件

### config/windows.yaml

```yaml
mt5_hosts:
  # Demo账户配置
  demo_1:
    enabled: true
    host: "host.docker.internal"      # API Bridge地址
    port: 9090                         # API Bridge端口
    login: 5049130509                  # MT5账号 ← 自动登录使用
    password: "your_password_here"     # MT5密码 ← 自动登录使用
    server: "MetaQuotes-Demo"          # MT5服务器 ← 自动登录使用
    api_key: "demo_key_12345"          # API Bridge认证密钥（可选）
    timeout: 10
    use_investor: true                 # 只读模式

  # Real账户配置
  real_1:
    enabled: false                     # 默认禁用
    host: "host.docker.internal"
    port: 9091
    login: 8012345678
    password: "${MT5_REAL_PASSWORD}"   # 从环境变量读取（安全）
    server: "ICMarkets-Live"
    api_key: "${MT5_REAL_API_KEY}"
    timeout: 15
    use_investor: false

# Validator配置
validator:
  enabled: true
  mt5_host: "demo_1"                   # 使用demo_1配置

# Execution配置
execution:
  enabled: true
  mt5_host: "demo_1"                   # 使用demo_1配置（或改为real_1）
```

---

## 代码使用

### 方式1：在Execution服务中使用

```python
# src/services/execution/execution_service.py

from src.common.mt5_client import MT5Client
from src.common.config.settings import settings

class ExecutionService:
    def __init__(self):
        # 从配置读取mt5_host
        mt5_host_key = settings.get("execution", {}).get("mt5_host", "demo_1")

        # 创建MT5客户端（自动登录）
        self.mt5_client = MT5Client.from_config(
            mt5_host_key=mt5_host_key,
            auto_login=True  # 自动使用配置中的login/password/server登录
        )

        print(f"✓ MT5客户端已连接: {mt5_host_key}")

    def get_account_info(self):
        """获取账户信息"""
        account = self.mt5_client.get_account()
        return account

    def place_order(self, symbol: str, action: str, volume: float):
        """下单"""
        result = self.mt5_client.place_order(
            symbol=symbol,
            action=action,
            volume=volume
        )
        return result

    def get_market_data(self, symbol: str, timeframe: str = "H1", count: int = 100):
        """获取市场数据"""
        bars = self.mt5_client.get_bars(
            symbol=symbol,
            timeframe=timeframe,
            count=count
        )
        return bars


# 使用示例
if __name__ == "__main__":
    service = ExecutionService()

    # 获取账户信息
    account = service.get_account_info()
    print(f"账户: {account['login']}")
    print(f"余额: ${account['balance']:.2f}")

    # 获取市场数据
    bars = service.get_market_data("EURUSD", "H1", 10)
    print(f"获取到 {len(bars)} 条K线数据")

    # 下单（Demo账户）
    order = service.place_order("EURUSD", "buy", 0.1)
    print(f"订单: {order}")
```

### 方式2：在Validator服务中使用

```python
# src/services/validator/validator_service.py

from src.common.mt5_client import create_mt5_client
from src.common.config.settings import settings

class ValidatorService:
    def __init__(self):
        # 从配置读取mt5_host
        mt5_host_key = settings.get("validator", {}).get("mt5_host", "demo_1")

        # 创建客户端（自动登录）
        self.mt5_client = create_mt5_client(mt5_host_key, auto_login=True)

    def validate_strategy(self, strategy_code: str, symbol: str):
        """验证策略"""
        # 1. 获取历史数据
        bars = self.mt5_client.get_bars(symbol, "H1", 500)

        # 2. 运行策略回测
        # ... 策略验证逻辑 ...

        # 3. 返回结果
        return {
            "symbol": symbol,
            "bars_count": len(bars),
            "result": "success"
        }


# 使用示例
if __name__ == "__main__":
    service = ValidatorService()

    result = service.validate_strategy("strategy_code", "EURUSD")
    print(result)
```

### 方式3：简单脚本使用

```python
# scripts/test_mt5_connection.py

from src.common.mt5_client import create_mt5_client

# 创建客户端（自动登录）
client = create_mt5_client("demo_1", auto_login=True)

# 获取账户信息
account = client.get_account()
print(f"✓ 已连接MT5账户: {account['login']}")
print(f"  服务器: {account['server']}")
print(f"  余额: ${account['balance']:.2f}")
print(f"  净值: ${account['equity']:.2f}")

# 获取实时报价
tick = client.get_tick("EURUSD")
print(f"\n✓ EURUSD实时报价:")
print(f"  买价: {tick['bid']}")
print(f"  卖价: {tick['ask']}")

# 获取K线数据
bars = client.get_bars("EURUSD", "H1", 5)
print(f"\n✓ 获取到 {len(bars)} 条H1 K线:")
for bar in bars[:3]:
    print(f"  {bar['time']}: O={bar['open']:.5f} H={bar['high']:.5f} L={bar['low']:.5f} C={bar['close']:.5f}")
```

---

## 完整启动流程

### Windows系统

```bash
# 步骤1: 启动MT5终端（可以不登录）
双击MT5图标 → 留在登录界面即可（或最小化）

# 步骤2: 启动API Bridge
scripts\windows_mt5_script\start_mt5_bridge.bat
# 看到: ✅ MT5 API Bridge已启动

# 步骤3: 验证API Bridge
curl http://localhost:9090/health
# 看到: {"status":"healthy","mt5_connected":true}
```

### Linux容器

```bash
# 步骤1: 启动所有服务
docker-compose --profile dev up -d

# 步骤2: 查看Execution日志（观察自动登录）
docker-compose logs -f execution

# 预期输出:
# execution | INFO: MT5Client初始化: http://host.docker.internal:9090
# execution | INFO: 登录MT5: 5049130509@MetaQuotes-Demo
# execution | INFO: ✓ MT5登录成功: 5049130509
# execution | ✓ MT5客户端已连接: demo_1
```

---

## 自动登录工作原理

### 1. MT5Client初始化

```python
client = MT5Client.from_config("demo_1", auto_login=True)
```

内部执行：
```python
# 1. 读取配置
config = {
    "host": "host.docker.internal",
    "port": 9090,
    "login": 5049130509,
    "password": "your_password",
    "server": "MetaQuotes-Demo"
}

# 2. 创建客户端
client = MT5Client(
    host="host.docker.internal",
    port=9090,
    login=5049130509,
    password="your_password",
    server="MetaQuotes-Demo",
    auto_login=True  # ← 关键参数
)

# 3. 自动登录（如果auto_login=True）
client.login()  # 发送POST /login请求
```

### 2. API Bridge处理登录

```python
# src/services/mt5_api_bridge/app.py

@app.post("/login")
async def login(request: LoginRequest):
    # 调用MT5库登录
    success = mt5.login(
        login=request.login,
        password=request.password,
        server=request.server
    )

    if success:
        return {"success": True, "login": request.login}
    else:
        return {"success": False, "error": mt5.last_error()}
```

### 3. MT5终端连接做市商

```
MT5终端 → 使用login/password → 连接server → 做市商验证 → 登录成功
```

---

## 多环境配置

### Windows开发环境

```yaml
# config/windows.yaml
mt5_hosts:
  demo_1:
    host: "host.docker.internal"      # Docker访问宿主机
    login: 5049130509                  # Demo账户
    password: "demo_password"
    server: "MetaQuotes-Demo"

execution:
  mt5_host: "demo_1"                   # 使用Demo账户
```

### Cloud生产环境

```yaml
# config/cloud.yaml
mt5_hosts:
  demo_1:
    host: "52.10.20.30"                # 远程Windows VPS
    login: 5049130509
    password: "${MT5_DEMO_PASSWORD}"   # 环境变量
    server: "MetaQuotes-Demo"

  real_1:
    host: "52.10.20.40"                # 另一个VPS
    login: 8012345678
    password: "${MT5_REAL_PASSWORD}"   # 环境变量
    server: "ICMarkets-Live"

execution:
  mt5_host: "real_1"                   # 使用Real账户（生产）
```

---

## 安全最佳实践

### ✅ 推荐

1. **生产环境使用环境变量**
   ```yaml
   password: "${MT5_REAL_PASSWORD}"   # ✅ 安全
   ```

2. **启用API密钥认证**
   ```yaml
   api_key: "${MT5_API_KEY}"          # ✅ 防止未授权访问
   ```

3. **使用投资者密码（只读）**
   ```yaml
   use_investor: true                  # ✅ Validator使用
   ```

4. **分离Demo和Real配置**
   ```yaml
   mt5_hosts:
     demo_1:   # 开发测试
     real_1:   # 生产交易
   ```

### ❌ 避免

1. ❌ 硬编码真实账户密码
   ```yaml
   password: "my_real_password_123"   # ❌ 不安全
   ```

2. ❌ Execution使用Demo和Real相同配置
   ```yaml
   # 应该分开配置，明确区分
   ```

---

## 故障排查

### Q1: 自动登录失败？

**查看日志**：
```bash
docker-compose logs execution | grep "登录"

# 可能输出:
# ✗ MT5登录失败: Invalid account
```

**解决**：
1. 检查配置文件中的login/password/server是否正确
2. 手动测试登录：
   ```bash
   curl -X POST http://localhost:9090/login \
     -H "Content-Type: application/json" \
     -d '{"login":5049130509,"password":"your_password","server":"MetaQuotes-Demo"}'
   ```

### Q2: 容器连接不到API Bridge？

**测试连通性**：
```bash
docker exec -it mt4-factory-execution curl http://host.docker.internal:9090/health
```

**检查配置**：
```yaml
mt5_hosts:
  demo_1:
    host: "host.docker.internal"     # ✅ 正确
    # host: "localhost"              # ❌ 容器内不通
```

### Q3: 密码包含特殊字符？

**使用环境变量**：
```bash
# .env
MT5_DEMO_PASSWORD='p@ssw0rd!#$%'

# config/windows.yaml
password: "${MT5_DEMO_PASSWORD}"
```

---

## 测试脚本

创建测试脚本验证自动登录：

```python
# scripts/test_auto_login.py

from src.common.mt5_client import create_mt5_client
import sys

def test_auto_login():
    print("=" * 50)
    print("  MT5自动登录测试")
    print("=" * 50)
    print()

    try:
        # 创建客户端（自动登录）
        print("[1/3] 创建MT5客户端...")
        client = create_mt5_client("demo_1", auto_login=True)
        print("✓ 客户端创建成功")
        print()

        # 获取账户信息
        print("[2/3] 获取账户信息...")
        account = client.get_account()
        print(f"✓ 账户: {account['login']}")
        print(f"  服务器: {account['server']}")
        print(f"  余额: ${account['balance']:.2f}")
        print()

        # 获取市场数据
        print("[3/3] 获取市场数据...")
        bars = client.get_bars("EURUSD", "H1", 5)
        print(f"✓ 获取到 {len(bars)} 条K线数据")
        print()

        print("=" * 50)
        print("✓ 所有测试通过！")
        print("=" * 50)
        return True

    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        return False


if __name__ == "__main__":
    success = test_auto_login()
    sys.exit(0 if success else 1)
```

运行测试：
```bash
# 在容器内运行
docker exec -it mt4-factory-execution python scripts/test_auto_login.py
```

---

## 总结

### 完整流程

```
1. Windows: 启动MT5终端（可不登录）
2. Windows: 启动API Bridge (scripts\windows_mt5_script\start_mt5_bridge.bat)
3. 配置文件: 填写login/password/server
4. 代码: MT5Client.from_config("demo_1", auto_login=True)
5. 自动: 发送HTTP登录请求到API Bridge
6. 自动: API Bridge调用mt5.login()登录MT5
7. 自动: MT5连接做市商服务器
8. 完成: 可以获取数据、下单等操作
```

### 关键点

- ✅ **不需要手动登录MT5终端**（API Bridge自动登录）
- ✅ **配置文件中的login/password会被使用**（自动登录）
- ✅ **Execution/Orchestrator直接读取yaml**（通过MT5Client）
- ✅ **Windows负责MT5+API Bridge**（其他服务只需HTTP调用）

---

## 相关文档

- [MT5 Client API文档](../src/common/mt5_client.py)
- [MT5主机配置指南](../config/MT5_HOSTS_GUIDE.md)
- [MT5连接架构](./MT5_CONNECTION_ARCHITECTURE.md)
- [Docker部署指南](./DOCKER_DEPLOYMENT.md)
