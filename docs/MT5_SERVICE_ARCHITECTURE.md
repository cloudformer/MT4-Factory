# MT5服务架构 - Demo和Real统一管理

## 核心架构

```
┌─────────────────────────────────────────────────────────────┐
│ 配置层（唯一的区别）                                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  config/windows.yaml (或 cloud.yaml)                        │
│  ┌───────────────────────────────────────────────────────┐ │
│  │ mt5_hosts:                                            │ │
│  │   demo_1:                           ← Demo MT5配置    │ │
│  │     host: "host.docker.internal"                      │ │
│  │     login: 5049130509                                 │ │
│  │     password: "demo_password"                         │ │
│  │     server: "MetaQuotes-Demo"                         │ │
│  │                                                       │ │
│  │   real_1:                           ← Real MT5配置    │ │
│  │     host: "52.10.20.40"                               │ │
│  │     login: 8012345678                                 │ │
│  │     password: "real_password"                         │ │
│  │     server: "ICMarkets-Live"                          │ │
│  └───────────────────────────────────────────────────────┘ │
│                                                             │
│  validator:                                                 │
│    mt5_host: "demo_1"     ← Validator用Demo跑分            │
│                                                             │
│  execution:                                                 │
│    mt5_host: "demo_1"     ← Execution用Demo测试            │
│    # mt5_host: "real_1"   ← 切换到Real真实交易             │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 服务层（代码完全相同）                                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Validator服务                  Execution服务               │
│  ┌──────────────────┐          ┌──────────────────┐       │
│  │ 读取配置:        │          │ 读取配置:        │       │
│  │   mt5_host="demo_1"│        │   mt5_host="demo_1"│     │
│  │                  │          │   (或"real_1")    │       │
│  │ 创建客户端:      │          │                  │       │
│  │   MT5Client.from_config("demo_1")  │                   │
│  │                  │          │ 创建客户端:      │       │
│  │ 功能:            │          │   MT5Client.from_config() │
│  │ - 验证策略       │          │                  │       │
│  │ - 回测           │          │ 功能:            │       │
│  │ - 跑分           │          │ - 执行交易       │       │
│  │ - 获取行情       │          │ - 下单平仓       │       │
│  └──────────────────┘          │ - 风控管理       │       │
│                                └──────────────────┘       │
│                                                             │
│  使用同一个MT5Client库，代码逻辑完全相同                     │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ Windows层（根据配置连接不同的MT5）                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Demo Windows (host.docker.internal:9090)                  │
│  ├─ MT5终端 (Demo账户: 5049130509)                         │
│  └─ API Bridge (端口9090)                                  │
│                                                             │
│  Real Windows (52.10.20.40:9091)                           │
│  ├─ MT5终端 (Real账户: 8012345678)                         │
│  └─ API Bridge (端口9091)                                  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 配置示例

### 完整配置 (config/windows.yaml)

```yaml
# ==================== MT5主机配置 ====================
mt5_hosts:
  # Demo MT5 - 用于验证和测试
  demo_1:
    enabled: true
    name: "Demo MT5 本地"
    host: "host.docker.internal"      # 本地Windows
    port: 9090
    login: 5049130509                  # Demo账号
    password: "demo_password"
    server: "MetaQuotes-Demo"
    api_key: "demo_key_12345"
    timeout: 10
    use_investor: true                 # 只读模式（推荐）

  # Real MT5 - 用于真实交易
  real_1:
    enabled: true
    name: "Real MT5 生产"
    host: "52.10.20.40"                # 远程VPS或本地
    port: 9091                         # 不同端口（可选）
    login: 8012345678                  # Real账号
    password: "${MT5_REAL_PASSWORD}"   # 从环境变量读取（安全）
    server: "ICMarkets-Live"
    api_key: "${MT5_REAL_API_KEY}"
    timeout: 15
    use_investor: false                # 可交易模式

# ==================== Validator配置 ====================
# 用途：实时验证策略，跑分评估
validator:
  enabled: true
  mt5_host: "demo_1"                   # ← 始终用Demo（安全）
  
  # 数据源配置
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
  
  # 并发配置
  concurrency: 20
  schedule_interval: 3600

# ==================== Execution配置 ====================
# 用途：执行真实交易
execution:
  enabled: true
  
  # ========== 关键配置：切换Demo/Real ==========
  mt5_host: "demo_1"                   # ← 测试阶段用Demo
  # mt5_host: "real_1"                 # ← 生产环境改为Real
  
  # 风控配置
  risk_limits:
    max_order_size: 0.1                # 最大手数
    max_daily_loss: 1000               # 每日最大亏损
    max_position_count: 5              # 最大持仓数
    allowed_symbols:
      - "EURUSD"
      - "GBPUSD"
      - "USDJPY"
```

---

## 代码实现（完全相同）

### Validator服务

```python
# src/services/validator/validator_service.py

from src.common.mt5_client import MT5Client
from src.common.config.settings import settings

class ValidatorService:
    def __init__(self):
        """初始化Validator服务"""
        # 从配置读取mt5_host（始终是demo_1）
        mt5_host_key = settings.get("validator", {}).get("mt5_host", "demo_1")
        
        print(f"[Validator] 连接MT5: {mt5_host_key}")
        
        # 创建MT5客户端（自动登录）
        self.mt5_client = MT5Client.from_config(mt5_host_key, auto_login=True)
        
        # 验证连接
        account = self.mt5_client.get_account()
        print(f"[Validator] ✓ 已连接: {account['login']}@{account['server']}")
        print(f"[Validator]   余额: ${account['balance']:.2f}")
    
    def validate_strategy(self, strategy_code: str, symbol: str, timeframe: str):
        """
        验证策略（使用Demo MT5数据）
        
        Args:
            strategy_code: 策略代码
            symbol: 交易品种
            timeframe: 时间周期
        """
        print(f"[Validator] 验证策略: {symbol} {timeframe}")
        
        # 获取历史数据（从Demo MT5）
        bars = self.mt5_client.get_bars(symbol, timeframe, 500)
        print(f"[Validator] 获取到 {len(bars)} 条K线数据")
        
        # 运行策略回测
        # ... 策略验证逻辑 ...
        
        # 计算评分
        score = self._calculate_score(bars, strategy_code)
        
        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "score": score,
            "bars_count": len(bars)
        }
    
    def _calculate_score(self, bars, strategy_code):
        """计算策略评分"""
        # ... 评分逻辑 ...
        return 85.5
```

### Execution服务

```python
# src/services/execution/execution_service.py

from src.common.mt5_client import MT5Client
from src.common.config.settings import settings

class ExecutionService:
    def __init__(self):
        """初始化Execution服务"""
        # 从配置读取mt5_host（可以是demo_1或real_1）
        mt5_host_key = settings.get("execution", {}).get("mt5_host", "demo_1")
        
        print(f"[Execution] 连接MT5: {mt5_host_key}")
        
        # 创建MT5客户端（自动登录）
        self.mt5_client = MT5Client.from_config(mt5_host_key, auto_login=True)
        
        # 验证连接
        account = self.mt5_client.get_account()
        print(f"[Execution] ✓ 已连接: {account['login']}@{account['server']}")
        print(f"[Execution]   余额: ${account['balance']:.2f}")
        
        # ⚠️ 警告：如果是Real账户
        if "real" in mt5_host_key.lower():
            print(f"[Execution] ⚠️  真实账户交易模式！")
    
    def execute_trade(self, symbol: str, action: str, volume: float):
        """
        执行交易（使用配置的MT5：Demo或Real）
        
        Args:
            symbol: 交易品种
            action: "buy" 或 "sell"
            volume: 手数
        """
        print(f"[Execution] 执行交易: {action} {symbol} {volume}手")
        
        # 下单（无论Demo还是Real，代码一样）
        result = self.mt5_client.place_order(
            symbol=symbol,
            action=action,
            volume=volume,
            comment="Auto Trading"
        )
        
        if result.get("success"):
            print(f"[Execution] ✓ 订单成功: {result['order']}")
            return result
        else:
            print(f"[Execution] ✗ 订单失败: {result.get('error')}")
            raise Exception(f"下单失败: {result.get('error')}")
    
    def get_positions(self):
        """获取持仓（Demo或Real）"""
        positions = self.mt5_client.get_positions()
        print(f"[Execution] 当前持仓: {len(positions)}个")
        return positions
    
    def close_position(self, ticket: int):
        """平仓（Demo或Real）"""
        print(f"[Execution] 平仓: {ticket}")
        result = self.mt5_client.close_position(ticket)
        return result
```

**关键点**：
- Validator和Execution的代码**完全相同**
- 唯一区别是配置文件中的`mt5_host`参数
- 同一套代码，通过配置控制连接Demo还是Real

---

## 切换Demo/Real的方式

### 方式1：修改配置文件（推荐）

```yaml
# config/windows.yaml

# 测试阶段：两个服务都用Demo
validator:
  mt5_host: "demo_1"

execution:
  mt5_host: "demo_1"        # ← Demo测试
```

测试稳定后，只需改一行：

```yaml
execution:
  mt5_host: "real_1"        # ← 切换到Real
```

### 方式2：环境变量覆盖

```bash
# 启动时指定
export EXECUTION_MT5_HOST=real_1
docker-compose --profile dev up -d
```

### 方式3：动态切换（代码层）

```python
# 在运行时决定
if is_production:
    mt5_host = "real_1"
else:
    mt5_host = "demo_1"

client = MT5Client.from_config(mt5_host, auto_login=True)
```

---

## 使用场景

### 场景1：开发测试阶段

```yaml
validator:
  mt5_host: "demo_1"    # Validator始终用Demo

execution:
  mt5_host: "demo_1"    # Execution也用Demo测试
```

**所有操作都在Demo环境**，安全测试交易逻辑。

### 场景2：生产环境

```yaml
validator:
  mt5_host: "demo_1"    # Validator继续用Demo跑分

execution:
  mt5_host: "real_1"    # Execution切换到Real交易
```

**Validator用Demo评估策略，Execution用Real执行交易**。

### 场景3：多账户配置

```yaml
mt5_hosts:
  demo_1:
    host: "host.docker.internal:9090"
    login: 5049130509
  
  demo_2:
    host: "host.docker.internal:9091"
    login: 5049130510
  
  real_icmarkets:
    host: "52.10.20.40:9091"
    login: 8012345678
    server: "ICMarkets-Live"
  
  real_pepperstone:
    host: "52.10.20.50:9091"
    login: 8012345679
    server: "Pepperstone-Live"

execution:
  mt5_host: "real_icmarkets"    # 使用ICMarkets交易
  # mt5_host: "real_pepperstone" # 或切换到Pepperstone
```

---

## Demo和Real的本质区别

| 对比项 | Demo | Real |
|-------|------|------|
| **代码** | 完全相同 | 完全相同 |
| **MT5Client** | 完全相同 | 完全相同 |
| **API调用** | 完全相同 | 完全相同 |
| **配置** | `mt5_host: "demo_1"` | `mt5_host: "real_1"` |
| **连接地址** | 配置中的host/port | 配置中的host/port |
| **MT5账号** | 配置中的login/password | 配置中的login/password |
| **资金** | 虚拟资金 | 真实资金 ⚠️ |
| **风险** | 无风险 | 有风险 ⚠️ |

**结论**：Demo和Real在代码层面**没有任何区别**，完全通过配置控制。

---

## 最佳实践

### ✅ 推荐流程

```
1. 开发阶段
   Validator: demo_1
   Execution: demo_1
   → 全部用Demo测试

2. 测试阶段
   Validator: demo_1
   Execution: demo_1
   → 充分测试交易逻辑

3. 小规模生产
   Validator: demo_1
   Execution: real_1 (小手数、严格风控)
   → 真实交易，但风险可控

4. 全量生产
   Validator: demo_1
   Execution: real_1 (正常手数)
   → 正式运营
```

### ✅ 安全配置

```yaml
# Demo账户：明文密码（开发环境可接受）
demo_1:
  password: "demo_password"

# Real账户：环境变量（生产环境必须）
real_1:
  password: "${MT5_REAL_PASSWORD}"
  api_key: "${MT5_REAL_API_KEY}"
```

### ✅ 风控配置

```yaml
execution:
  mt5_host: "real_1"
  
  # Real账户严格风控
  risk_limits:
    max_order_size: 0.1          # 小手数
    max_daily_loss: 1000         # 严格止损
    max_position_count: 5        # 限制持仓数
    allowed_symbols:             # 白名单
      - "EURUSD"
```

---

## 部署架构

### Windows本地开发

```
Windows机器
├── MT5终端 (Demo) - 端口9090
│   └── API Bridge
└── MT5终端 (Real，可选) - 端口9091
    └── API Bridge

Docker容器
├── Validator → host.docker.internal:9090 (Demo)
└── Execution → host.docker.internal:9090 (Demo测试)
               host.docker.internal:9091 (Real可选)
```

### Cloud生产环境

```
Linux服务器
└── Docker容器
    ├── Validator → 52.10.20.30:9090 (Demo VPS)
    └── Execution → 52.10.20.40:9091 (Real VPS)

Windows VPS #1 (52.10.20.30)
└── MT5终端 (Demo) + API Bridge :9090

Windows VPS #2 (52.10.20.40)
└── MT5终端 (Real) + API Bridge :9091
```

---

## 总结

### 核心理念

1. **代码统一**：Validator和Execution使用相同的MT5Client
2. **配置分离**：Demo和Real只在配置文件中区分
3. **灵活切换**：修改一行配置即可切换Demo/Real
4. **安全优先**：Validator始终用Demo，Execution根据阶段选择

### 配置即切换

```yaml
# 一行配置决定一切
execution:
  mt5_host: "demo_1"    # Demo安全测试
  # mt5_host: "real_1"  # Real真实交易
```

**本质没有区别，完全通过配置控制！** ✅
