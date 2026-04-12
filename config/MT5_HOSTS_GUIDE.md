# MT5主机配置指南

## 概述

系统支持配置多个MT5主机，通过`mt5_hosts`配置，Validator和Execution服务可以选择连接不同的MT5实例。

---

## 配置结构

```yaml
mt5_hosts:
  # MT5主机1
  demo_1:
    enabled: true
    name: "MT5 Worker 1"
    type: "demo"                      # 类型标识（demo/real）
    host: "host.docker.internal"      # MT5地址
    port: 9090                        # MT5端口
    login: 5049130509                 # MT5账号
    password: "your_password"         # MT5密码
    server: "MetaQuotes-Demo"         # MT5服务器
    api_key: "your_api_key"           # API密钥
    timeout: 10                       # 超时时间（秒）
    use_investor: true                # 只读模式

  # MT5主机2
  real_1:
    enabled: true
    name: "MT5 Worker 2"
    type: "real"
    host: "52.10.20.40"
    port: 9091
    login: 8012345678
    password: "${MT5_REAL_PASSWORD}"  # 环境变量（推荐）
    server: "ICMarkets-Live"
    api_key: "${MT5_REAL_API_KEY}"
    timeout: 15
    use_investor: false
```

---

## 服务选择MT5主机

### Validator服务

```yaml
validator:
  enabled: true
  mt5_host: "demo_1"                  # 选择使用demo_1主机
```

### Execution服务

```yaml
execution:
  enabled: true
  mt5_host: "real_1"                  # 选择使用real_1主机
```

**自由切换**：
- 修改`mt5_host`的值，选择不同的MT5主机
- 可以都用`demo_1`，或都用`real_1`，或混用
- 通过修改`mt5_hosts`中的`host`和`login`来控制连接哪个MT5

---

## 常见配置场景

### 场景1：本地开发（单个Demo MT5）

```yaml
mt5_hosts:
  demo_1:
    enabled: true
    host: "host.docker.internal"      # 本地MT5
    port: 9090
    login: 5049130509
    server: "MetaQuotes-Demo"
    use_investor: true

validator:
  mt5_host: "demo_1"

execution:
  mt5_host: "demo_1"                  # Execution也用Demo测试
```

### 场景2：远程VPS（单个Demo MT5）

```yaml
mt5_hosts:
  demo_1:
    enabled: true
    host: "52.10.20.30"               # 远程VPS
    port: 9090
    login: 5049130509
    server: "MetaQuotes-Demo"

validator:
  mt5_host: "demo_1"

execution:
  mt5_host: "demo_1"
```

### 场景3：两个MT5主机（Validator用Demo，Execution用Real）

```yaml
mt5_hosts:
  demo_1:
    enabled: true
    host: "52.10.20.30"               # VPS #1 - Demo
    port: 9090
    login: 5049130509
    server: "MetaQuotes-Demo"

  real_1:
    enabled: true
    host: "52.10.20.40"               # VPS #2 - Real
    port: 9091
    login: 8012345678
    password: "${MT5_REAL_PASSWORD}"  # 环境变量
    server: "ICMarkets-Live"

validator:
  mt5_host: "demo_1"                  # Validator用Demo

execution:
  mt5_host: "real_1"                  # Execution用Real
```

### 场景4：多个MT5主机（扩展）

```yaml
mt5_hosts:
  demo_1:
    enabled: true
    name: "MetaQuotes Demo"
    host: "52.10.20.30"
    # ...

  real_icmarkets:
    enabled: true
    name: "ICMarkets Real"
    host: "52.10.20.40"
    # ...

  real_pepperstone:
    enabled: true
    name: "Pepperstone Real"
    host: "52.10.20.50"
    # ...

validator:
  mt5_host: "demo_1"                  # 验证用Demo

execution:
  mt5_host: "real_icmarkets"          # 执行用ICMarkets
  # 需要时可以切换到 "real_pepperstone"
```

---

## 配置说明

### type字段

```yaml
type: "demo"    # 标识类型（仅用于说明，不影响功能）
type: "real"    # 标识类型（仅用于说明，不影响功能）
```

实际连接的账户取决于`host`、`login`、`password`等配置。

### host字段

```yaml
# Docker容器访问宿主机（Windows/Mac本地MT5）
host: "host.docker.internal"

# 远程VPS
host: "52.10.20.30"

# 域名
host: "mt5.example.com"
```

### password字段

```yaml
# 开发环境：明文（不推荐生产）
password: "my_password_123"

# 生产环境：环境变量（推荐）
password: "${MT5_REAL_PASSWORD}"
```

### use_investor字段

```yaml
# 只读模式（推荐Validator使用）
use_investor: true

# 可交易模式（Execution需要）
use_investor: false
```

---

## 切换MT5主机

### 临时切换

直接修改配置文件：

```yaml
# 原配置
execution:
  mt5_host: "demo_1"

# 改为
execution:
  mt5_host: "real_1"
```

重启服务生效：
```bash
docker-compose restart execution
```

### 动态切换（未来支持）

计划支持通过API动态切换MT5主机，无需重启服务。

---

## 验证当前配置

### 查看配置

```bash
# 查看Validator使用的MT5主机
grep -A2 "validator:" config/windows.yaml | grep mt5_host

# 查看Execution使用的MT5主机
grep -A2 "execution:" config/windows.yaml | grep mt5_host
```

### 查看日志

```bash
# 查看服务启动日志
docker-compose logs validator | grep "MT5"
docker-compose logs execution | grep "MT5"

# 应该看到类似输出：
# [INFO] Validator connected to MT5: demo_1 (host.docker.internal:9090)
# [INFO] Execution connected to MT5: real_1 (52.10.20.40:9091)
```

---

## 最佳实践

### ✅ 推荐

1. **密码使用环境变量**
   ```yaml
   password: "${MT5_REAL_PASSWORD}"
   ```

2. **Validator使用只读模式**
   ```yaml
   use_investor: true
   ```

3. **测试先用Demo**
   ```yaml
   execution:
     mt5_host: "demo_1"  # 先测试
   ```

4. **清晰的主机命名**
   ```yaml
   demo_1:
     name: "MetaQuotes Demo VPS1"
   real_icmarkets:
     name: "ICMarkets Real VPS2"
   ```

### ❌ 避免

1. ❌ 硬编码真实账户密码
2. ❌ Execution使用Validator的投资者账户
3. ❌ 未测试就直接用Real主机

---

## 故障排查

### Q: 服务无法连接MT5？

**A:** 检查配置和网络：

```bash
# 1. 验证MT5主机配置
cat config/windows.yaml | grep -A10 "demo_1:"

# 2. 测试网络连通性（Windows容器访问宿主机）
docker exec -it mt4-factory-validator ping host.docker.internal

# 3. 测试端口连通性
docker exec -it mt4-factory-validator nc -zv host.docker.internal 9090

# 4. 查看详细日志
docker-compose logs -f validator
```

### Q: 修改配置不生效？

**A:** 重启对应服务：

```bash
# 重启Validator
docker-compose restart validator

# 重启Execution
docker-compose restart execution
```

### Q: 如何确认使用的是哪个MT5主机？

**A:** 查看启动日志：

```bash
docker-compose logs validator | grep "mt5_host"
docker-compose logs execution | grep "mt5_host"
```

---

## 相关文档

- [配置文件说明](./README.md)
- [Docker部署指南](../docs/DOCKER_DEPLOYMENT.md)
- [环境配置指南](../docs/ENVIRONMENT_SETUP.md)
