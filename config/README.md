# 配置文件说明

## 概述

所有服务间的调用都通过配置文件中的 `service_urls` 进行管理，避免硬编码URL，便于不同环境的部署。

MT5连接配置统一在 `mt5` 配置节中管理，支持完整的连接参数和代理设置。

## 配置文件

- `development.yaml` - 开发环境配置（本地调试）
- `production.yaml` - 生产环境配置示例

## 服务URL配置方式

### 方式1: 本地开发（默认）
```yaml
service_urls:
  strategy: "http://127.0.0.1:8001"
  orchestrator: "http://127.0.0.1:8002"
  execution: "http://127.0.0.1:8003"
  dashboard: "http://127.0.0.1:8000"
```

### 方式2: 独立域名部署
```yaml
service_urls:
  strategy: "https://strategy.evotrade.com"
  orchestrator: "https://orchestrator.evotrade.com"
  execution: "https://execution.evotrade.com"
  dashboard: "https://dashboard.evotrade.com"
```

### 方式3: API网关 + 路径前缀
```yaml
service_urls:
  strategy: "https://api.evotrade.com/strategy"
  orchestrator: "https://api.evotrade.com/orchestrator"
  execution: "https://api.evotrade.com/execution"
  dashboard: "https://api.evotrade.com/dashboard"
```

### 方式4: Kubernetes/Docker内网服务发现
```yaml
service_urls:
  strategy: "http://strategy-service:8001"
  orchestrator: "http://orchestrator-service:8002"
  execution: "http://execution-service:8003"
  dashboard: "http://dashboard-service:8000"
```

## 切换环境

### 方法1: 设置环境变量
```bash
export ENV=production
python -m uvicorn src.services.dashboard.api.app:app --host 0.0.0.0 --port 8000
```

### 方法2: 直接指定配置文件（需要在settings.py中实现）
```bash
python -m uvicorn src.services.dashboard.api.app:app --host 0.0.0.0 --port 8000 --env-file config/production.yaml
```

## 服务调用示例

### Dashboard调用Orchestrator
```python
from src.common.config.settings import settings

# 从配置读取URL
orchestrator_url = settings.get("service_urls", {}).get("orchestrator", "http://127.0.0.1:8002")

# 调用API
async with httpx.AsyncClient() as client:
    response = await client.get(f"{orchestrator_url}/registration/summary")
```

### CLI脚本调用
```python
from src.common.config.settings import settings

# 自动读取配置中的URL
orchestrator_url = settings.get("service_urls", {}).get("orchestrator", "http://127.0.0.1:8002")
response = requests.get(f"{orchestrator_url}/registration/candidates")
```

## 受影响的文件

已修改为从配置读取URL的文件：
- `src/services/dashboard/api/routes/data.py` - Dashboard数据路由
- `src/services/dashboard/api/routes/registration.py` - Dashboard注册路由
- `scripts/manage_registration.py` - CLI管理脚本

## 未来扩展

配置统一后，可以轻松实现：
1. 多环境部署（dev/staging/production）
2. 服务负载均衡（通过改变URL指向负载均衡器）
3. 灰度发布（部分流量指向新版本服务）
4. 服务网格集成（Istio、Linkerd等）
5. 跨区域部署（不同地区使用不同的service_urls）

## MT5配置说明

### 基础配置
```yaml
mt5:
  company: "MetaQuotes Ltd."       # 经纪商公司名
  server: "MetaQuotes-Demo"        # 服务器名称
  login: 5049130509                # 账号
  password: "-ySbKy4z"             # 主密码（交易模式）
  investor_password: "Fn@4ElKo"    # 投资者密码（只读模式）
```

### 高级配置（Windows生产环境）
```yaml
mt5:
  path: "C:/Program Files/MetaTrader 5/terminal64.exe"  # MT5终端路径
  timeout: 60000   # 连接超时（毫秒）
  portable: false  # 是否使用便携模式
```

### 代理配置（可选）
```yaml
mt5:
  proxy:
    enabled: true
    host: "proxy.example.com"  # 代理服务器地址
    port: 8888                 # 代理端口
    type: "HTTP"               # 代理类型: HTTP/HTTPS/SOCKS5
```

### 使用模式

**1. 交易模式（默认）**
- 使用主密码（password）
- 拥有完整交易权限
- 可以下单、平仓、修改订单

**2. 投资者模式（只读）**
- 使用投资者密码（investor_password）
- 只能查看账户和持仓
- 无法进行交易操作
- 适用于监控和数据采集

### 测试连接
```bash
# 使用测试工具
python scripts/test_mt5_connection.py

# 或者通过Execution服务健康检查
curl http://localhost:8003/health
```

## 注意事项

1. **默认值**: 所有读取配置的地方都提供了默认值，确保向后兼容
2. **环境变量**: production.yaml中的敏感信息（如MT5密码）使用 `${VAR_NAME}` 语法，运行时从环境变量读取
3. **配置优先级**: 环境变量 > 配置文件 > 默认值
4. **网络策略**: 生产环境需要配置防火墙规则，只允许服务间内网通信
5. **平台限制**: 真实MT5连接仅支持Windows，macOS/Linux自动使用Mock客户端
6. **密码安全**: 生产环境请使用环境变量存储密码，不要直接写在配置文件中
