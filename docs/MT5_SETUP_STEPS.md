# MT5连接3步设置指南

## 📍 执行位置总览

```
┌──────────────────────────────────────────────────┐
│ 步骤1: Windows系统上                              │
│ 位置: Windows物理机/VPS                           │
│ 操作: 运行bat脚本                                 │
└──────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────┐
│ 步骤2: 配置文件                                   │
│ 位置: config/windows.yaml 或 config/cloud.yaml  │
│ 操作: 填写MT5账号密码                             │
└──────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────┐
│ 步骤3: Execution服务代码                         │
│ 位置: src/services/execution/                   │
│ 操作: 创建MT5客户端，执行交易                     │
└──────────────────────────────────────────────────┘
```

---

## 步骤1: Windows系统 - 启动MT5和API Bridge

### 📍 执行位置
**Windows系统（物理机或VPS）**

### 🎯 操作
打开CMD或PowerShell，执行：

```bash
# 进入项目目录
cd C:\path\to\MT4-Factory

# 运行启动脚本
scripts\windows_mt5_script\start_mt5_bridge.bat
```

### ✅ 预期结果
```
========================================
  MT5 API Bridge 启动
========================================

[✓] Python已安装
[✓] MetaTrader5库已安装
[✓] MT5终端已运行 (terminal64.exe)

========================================
  启动API Bridge服务
========================================

监听地址: http://0.0.0.0:9090
INFO:     Uvicorn running on http://0.0.0.0:9090
```

### 📝 说明
- 这个脚本启动HTTP服务，监听9090端口
- 容器通过这个端口连接MT5
- **保持这个窗口运行，不要关闭**

---

## 步骤2: 配置文件 - 填写MT5账号信息

### 📍 执行位置
**项目配置文件**

#### Windows本地开发
编辑文件：`config/windows.yaml`

#### Cloud生产环境
编辑文件：`config/cloud.yaml`

### 🎯 操作
找到`mt5_hosts`配置段，填写你的MT5账号信息：

```yaml
# config/windows.yaml

mt5_hosts:
  # Demo账户配置
  demo_1:
    enabled: true
    host: "host.docker.internal"          # ← Windows本地固定用这个
    port: 9090                             # ← API Bridge端口
    login: 5049130509                      # ← 改成你的MT5账号
    password: "your_password_here"         # ← 改成你的MT5密码
    server: "MetaQuotes-Demo"              # ← 改成你的MT5服务器
    api_key: "demo_key_12345"              # ← API密钥（可选）
    timeout: 10
    use_investor: true                     # true=只读模式

  # Real账户配置（生产交易用）
  real_1:
    enabled: false                         # 默认禁用
    host: "host.docker.internal"
    port: 9091
    login: 8012345678                      # ← 改成你的真实账号
    password: "${MT5_REAL_PASSWORD}"       # ← 从环境变量读取（安全）
    server: "ICMarkets-Live"               # ← 改成你的经纪商服务器
    api_key: "${MT5_REAL_API_KEY}"
    timeout: 15
    use_investor: false                    # false=可交易模式
```

### 📝 说明

#### 必须修改的字段
```yaml
login: 5049130509              # ← 你的MT5登录账号
password: "your_password"      # ← 你的MT5密码
server: "MetaQuotes-Demo"      # ← 你的MT5服务器名称
```

#### 如何获取这些信息？
1. **登录账号**：经纪商提供的账号（通常是一串数字）
2. **密码**：你设置的MT5密码
3. **服务器**：经纪商提供的服务器名称
   - Demo账户示例：`MetaQuotes-Demo`, `ICMarkets-Demo01`
   - Real账户示例：`ICMarkets-Live`, `Pepperstone-Live`

#### 安全提示
生产环境使用环境变量：
```yaml
password: "${MT5_REAL_PASSWORD}"  # 从环境变量读取，不硬编码
```

---

## 步骤3: Execution服务 - 创建交易客户端

### 📍 执行位置
**Execution服务代码**

文件：`src/services/execution/execution_service.py`

### 🎯 操作

#### 3.1 在Execution服务初始化时创建客户端

```python
# src/services/execution/execution_service.py

from src.common.mt5_client import MT5Client
from src.common.config.settings import settings

class ExecutionService:
    def __init__(self):
        """初始化Execution服务"""
        
        # 从配置读取使用哪个MT5主机
        mt5_host_key = settings.get("execution", {}).get("mt5_host", "demo_1")
        
        print(f"[Execution] 连接MT5主机: {mt5_host_key}")
        
        # 创建MT5客户端（自动读取yaml中的login/password/server并登录）
        self.mt5_client = MT5Client.from_config(
            mt5_host_key=mt5_host_key,
            auto_login=True  # ← 关键：自动使用yaml中的账号密码登录
        )
        
        # 验证连接
        account = self.mt5_client.get_account()
        print(f"[Execution] ✓ 已连接MT5账户: {account['login']}")
        print(f"[Execution]   服务器: {account['server']}")
        print(f"[Execution]   余额: ${account['balance']:.2f}")
```

#### 3.2 执行交易操作

```python
class ExecutionService:
    # ... __init__ 见上方
    
    def place_buy_order(self, symbol: str, volume: float, sl: float = None, tp: float = None):
        """
        下买单
        
        Args:
            symbol: 交易品种 (如 "EURUSD")
            volume: 手数 (如 0.1)
            sl: 止损价
            tp: 止盈价
        """
        print(f"[Execution] 下买单: {symbol} {volume}手")
        
        # 调用MT5客户端下单
        result = self.mt5_client.place_order(
            symbol=symbol,
            action="buy",  # 买入
            volume=volume,
            sl=sl,
            tp=tp,
            comment="Auto Trading"
        )
        
        if result.get("success"):
            print(f"[Execution] ✓ 订单成功: {result['order']}")
            return result
        else:
            print(f"[Execution] ✗ 订单失败: {result.get('error')}")
            raise Exception(f"下单失败: {result.get('error')}")
    
    def place_sell_order(self, symbol: str, volume: float, sl: float = None, tp: float = None):
        """下卖单"""
        print(f"[Execution] 下卖单: {symbol} {volume}手")
        
        result = self.mt5_client.place_order(
            symbol=symbol,
            action="sell",  # 卖出
            volume=volume,
            sl=sl,
            tp=tp,
            comment="Auto Trading"
        )
        
        if result.get("success"):
            print(f"[Execution] ✓ 订单成功: {result['order']}")
            return result
        else:
            print(f"[Execution] ✗ 订单失败: {result.get('error')}")
            raise Exception(f"下单失败: {result.get('error')}")
    
    def get_positions(self):
        """获取当前持仓"""
        positions = self.mt5_client.get_positions()
        print(f"[Execution] 当前持仓数: {len(positions)}")
        return positions
    
    def close_position(self, ticket: int):
        """平仓"""
        print(f"[Execution] 平仓: {ticket}")
        result = self.mt5_client.close_position(ticket)
        return result


# ==================== 使用示例 ====================

if __name__ == "__main__":
    # 创建服务实例
    service = ExecutionService()
    
    # 示例1: 下买单
    order1 = service.place_buy_order(
        symbol="EURUSD",
        volume=0.1,
        sl=1.08000,  # 止损
        tp=1.09000   # 止盈
    )
    print(f"买单结果: {order1}")
    
    # 示例2: 查看持仓
    positions = service.get_positions()
    for pos in positions:
        print(f"持仓: {pos['symbol']} {pos['volume']}手 盈亏=${pos['profit']:.2f}")
    
    # 示例3: 平仓
    if positions:
        ticket = positions[0]['ticket']
        service.close_position(ticket)
```

### 📝 说明

#### 关键代码
```python
# 这一行完成所有工作：
# 1. 读取config/windows.yaml中的mt5_hosts.demo_1配置
# 2. 连接http://host.docker.internal:9090
# 3. 使用yaml中的login/password/server自动登录MT5
# 4. 返回可用的MT5客户端
self.mt5_client = MT5Client.from_config("demo_1", auto_login=True)
```

#### 自动登录原理
```python
MT5Client.from_config("demo_1", auto_login=True)
    ↓
读取 config/windows.yaml
    mt5_hosts.demo_1.login = 5049130509
    mt5_hosts.demo_1.password = "your_password"
    mt5_hosts.demo_1.server = "MetaQuotes-Demo"
    ↓
发送HTTP请求到Windows API Bridge
    POST http://host.docker.internal:9090/login
    Body: {login: 5049130509, password: "xxx", server: "MetaQuotes-Demo"}
    ↓
Windows API Bridge调用MT5库
    mt5.login(5049130509, "xxx", "MetaQuotes-Demo")
    ↓
MT5连接做市商服务器
    ↓
登录成功！
```

---

## 完整测试流程

### 测试1: 验证连接

```python
# scripts/test_execution.py

from src.services.execution.execution_service import ExecutionService

# 创建服务（会自动连接和登录）
service = ExecutionService()

# 获取账户信息
account = service.mt5_client.get_account()
print(f"账户: {account['login']}")
print(f"余额: ${account['balance']:.2f}")

# 获取实时报价
tick = service.mt5_client.get_tick("EURUSD")
print(f"EURUSD报价: Bid={tick['bid']} Ask={tick['ask']}")
```

### 测试2: 模拟交易

```python
# scripts/test_trading.py

from src.services.execution.execution_service import ExecutionService

service = ExecutionService()

# 下单测试（Demo账户）
print("下单测试...")
order = service.place_buy_order(
    symbol="EURUSD",
    volume=0.01,  # 0.01手（最小手数）
    sl=1.08000,
    tp=1.09000
)

print(f"订单号: {order['order']}")
print(f"成交价: {order['price']}")

# 查看持仓
positions = service.get_positions()
print(f"当前持仓: {len(positions)}个")
```

---

## 配置检查清单

### ✅ Windows系统
- [ ] MT5终端已安装
- [ ] 运行 `scripts\windows_mt5_script\start_mt5_bridge.bat`
- [ ] 看到 "Uvicorn running on http://0.0.0.0:9090"

### ✅ 配置文件
- [ ] 打开 `config/windows.yaml`
- [ ] 找到 `mt5_hosts.demo_1`
- [ ] 填写 `login: 你的账号`
- [ ] 填写 `password: "你的密码"`
- [ ] 填写 `server: "你的服务器"`

### ✅ Execution服务
- [ ] 代码中使用 `MT5Client.from_config("demo_1", auto_login=True)`
- [ ] 自动读取yaml配置
- [ ] 自动连接Windows API Bridge
- [ ] 自动登录MT5

---

## 常见问题

### Q1: 在哪里填写账号密码？

**A:** 在配置文件
```
config/windows.yaml (Windows本地)
config/cloud.yaml (Cloud生产)

找到 mt5_hosts → demo_1 → login/password/server
```

### Q2: 代码在哪里创建客户端？

**A:** 在Execution服务初始化
```python
# src/services/execution/execution_service.py

def __init__(self):
    self.mt5_client = MT5Client.from_config("demo_1", auto_login=True)
```

### Q3: 如何切换使用Real账户？

**A:** 修改配置
```yaml
# config/windows.yaml

execution:
  mt5_host: "real_1"  # 从demo_1改为real_1
```

### Q4: 如何确认已经登录成功？

**A:** 查看Execution日志
```bash
docker-compose logs -f execution

# 应该看到:
# [Execution] 连接MT5主机: demo_1
# [Execution] ✓ 已连接MT5账户: 5049130509
# [Execution]   服务器: MetaQuotes-Demo
# [Execution]   余额: $100000.00
```

---

## 目录结构

```
MT4-Factory/
├── config/
│   ├── windows.yaml              ← 步骤2: 在这里填写账号密码
│   └── cloud.yaml                ← 步骤2: Cloud环境在这里填写
│
├── scripts/
│   └── windows_mt5_script/
│       └── start_mt5_bridge.bat  ← 步骤1: Windows执行这个脚本
│
└── src/
    ├── common/
    │   └── mt5_client.py         ← MT5客户端库（已实现）
    │
    └── services/
        └── execution/
            └── execution_service.py  ← 步骤3: 在这里创建客户端和交易
```

---

## 总结

| 步骤 | 位置 | 操作 | 说明 |
|------|------|------|------|
| **步骤1** | Windows系统 | `scripts\windows_mt5_script\start_mt5_bridge.bat` | 启动HTTP服务（端口9090） |
| **步骤2** | `config/windows.yaml` | 填写`login`/`password`/`server` | MT5账号信息 |
| **步骤3** | `src/services/execution/` | `MT5Client.from_config("demo_1", auto_login=True)` | 创建客户端，执行交易 |

3步完成，自动登录，直接交易！
