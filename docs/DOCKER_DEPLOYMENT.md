# Docker部署指南

## 环境说明

| 环境 | 部署方式 | 服务 |
|------|---------|------|
| **Mac** | 本地Python进程 | Dashboard only（UI开发） |
| **Windows** | Docker Compose | Dashboard, Orchestrator, Strategy, Validator, Execution |
| **Cloud** | Docker Compose | 所有服务 |

**MT5配置**：通过配置文件中的`mt5_host`选择连接哪个MT5主机（详见 [MT5主机配置指南](../config/MT5_HOSTS_GUIDE.md)）

---

## Windows环境（开发/测试）

### 前置条件
- ✅ 安装Docker Desktop for Windows
- ✅ 本地运行MT5（Demo账户）
- ✅ MT5 API Bridge运行在`localhost:9090`

### 一键启动

```bash
# 方式1：使用启动脚本（推荐）
scripts\windows\start_all.bat

# 方式2：手动命令
set ENV=windows
docker-compose --profile dev up -d
```

### 启动的服务
- ✅ `postgres` - PostgreSQL数据库
- ✅ `dashboard` - 前端UI (http://localhost:8001)
- ✅ `orchestrator` - 策略编排 (http://localhost:8002)
- ✅ `strategy` - 策略生成 (http://localhost:8000)
- ✅ `validator` - 策略验证 (http://localhost:8080)
- ✅ `execution` - 交易执行 (http://localhost:8003)

### 停止服务

```bash
# 方式1：使用停止脚本
scripts\windows\stop_all.bat

# 方式2：手动命令
docker-compose --profile dev down
```

### 查看日志

```bash
# 查看所有服务日志
docker-compose logs -f

# 查看特定服务日志
docker-compose logs -f validator
docker-compose logs -f dashboard

# 进入容器调试
docker exec -it mt4-factory-validator bash
```

### 代码修改后

**无需重新构建！** 代码已映射到容器内：
```yaml
volumes:
  - ./src:/app/src    # 代码实时同步
```

只需重启容器：
```bash
docker-compose restart validator
```

### 添加新依赖后

修改`requirements.txt`后需要重建镜像：
```bash
# 使用重建脚本
scripts\windows\rebuild_all.bat

# 或手动命令
docker-compose build validator
docker-compose up -d validator
```

---

## Cloud环境（生产部署）

### 前置条件
- ✅ Linux服务器（Ubuntu/CentOS）
- ✅ 安装Docker和Docker Compose
- ✅ 配置环境变量文件`.env.production`
- ✅ 远程Windows VPS运行MT5（真实账户）⚠️

### 创建环境变量文件

```bash
# .env.production
ENV=production
POSTGRES_PASSWORD=your_strong_password_here
MT5_REAL_PASSWORD=your_mt5_real_password
MT5_REAL_API_KEY=your_strong_api_key
ANTHROPIC_API_KEY=your_anthropic_api_key
SLACK_WEBHOOK_URL=your_slack_webhook
ALERT_EMAIL=your_email@example.com
BACKUP_S3_BUCKET=your_s3_bucket_name
```

### 启动生产服务

```bash
# 方式1：使用启动脚本（推荐）
bash scripts/cloud/start_all.sh

# 方式2：手动命令
export ENV=production
source .env.production
docker-compose --profile production up -d
```

### 启动的服务
- ✅ `postgres` - 使用外部RDS（或容器）
- ✅ `dashboard` - 前端UI
- ✅ `orchestrator` - 策略编排
- ✅ `strategy` - 策略生成
- ✅ `validator` - 策略验证
- ✅ `execution` - 交易执行

### 监控和维护

```bash
# 查看服务状态
docker-compose ps

# 查看实时日志
docker-compose logs -f execution
docker-compose logs -f validator

# 重启服务
docker-compose restart execution

# 停止所有服务
docker-compose --profile production down
```

### 安全建议⚠️

1. **Execution服务仅在Cloud启用**
   - Windows和Mac环境不启动该服务
   - 真实交易需要严格风控

2. **敏感信息使用环境变量**
   ```bash
   # 不要在代码中硬编码密码
   MT5_REAL_PASSWORD=${MT5_REAL_PASSWORD}
   ```

3. **定期备份数据库**
   ```bash
   # 使用backup配置（config/cloud.yaml）
   backup:
     enabled: true
     schedule: "0 2 * * *"
   ```

---

## Mac环境（UI开发）

Mac环境**不使用Docker**，直接运行Python进程：

```bash
# 设置环境变量
export DEVICE=mac

# 启动Dashboard
python -m uvicorn src.services.dashboard.api.app:app --host 0.0.0.0 --port 8001

# 或使用Mac启动脚本
bash scripts/mac/start_all.sh
```

---

## Profiles说明

Docker Compose使用profiles控制不同环境的服务：

| Profile | 包含服务 | 使用环境 |
|---------|---------|---------|
| `dev` | dashboard, orchestrator, strategy, validator | Windows开发 |
| `production` | 所有服务 + execution | Cloud生产 |
| `tools` | pgadmin | 可选数据库管理工具 |

### 启动可选工具

```bash
# 启动pgAdmin（数据库管理）
docker-compose --profile tools up -d pgadmin

# 访问：http://localhost:5050
# 账号：admin@mt4factory.local
# 密码：admin
```

---

## 服务端口映射

| 服务 | 容器端口 | 宿主机端口 | URL |
|------|---------|-----------|-----|
| Dashboard | 8001 | 8001 | http://localhost:8001 |
| Orchestrator | 8002 | 8002 | http://localhost:8002 |
| Strategy | 8000 | 8000 | http://localhost:8000 |
| Validator | 8080 | 8080 | http://localhost:8080 |
| Execution | 8003 | 8003 | http://localhost:8003 |
| PostgreSQL | 5432 | 5432 | localhost:5432 |
| pgAdmin | 80 | 5050 | http://localhost:5050 |

---

## 常见问题

### Q1: 修改代码后不生效？

**A:** 重启容器即可（代码已映射）：
```bash
docker-compose restart validator
```

### Q2: 添加Python包后找不到？

**A:** 需要重新构建镜像：
```bash
docker-compose build validator
docker-compose up -d validator
```

### Q3: 容器无法连接MT5？

**A:** 检查`host.docker.internal`配置：
```yaml
extra_hosts:
  - "host.docker.internal:host-gateway"  # 允许容器访问宿主机
```

Windows配置：
```yaml
mt5_hosts:
  demo_1:
    host: "host.docker.internal"  # 指向宿主机MT5
    port: 9090
```

### Q4: 数据库连接失败？

**A:** 确保PostgreSQL服务健康：
```bash
docker-compose ps postgres
# 状态应该是 "healthy"

# 手动测试连接
docker exec -it mt4-factory-postgres psql -U evo_trade_user -d evo_trade
```

### Q5: 如何切换MT5主机？

**A:** 修改配置文件中的`mt5_host`参数：

```yaml
# config/windows.yaml 或 config/cloud.yaml
validator:
  mt5_host: "demo_1"  # 可选: demo_1, real_1

execution:
  mt5_host: "demo_1"  # 可选: demo_1, real_1
```

MT5主机的实际地址和账户在`mt5_hosts`配置中定义。

详见：[MT5主机配置指南](../config/MT5_HOSTS_GUIDE.md)

---

## 相关文档

- [配置文件说明](../config/README.md)
- [环境配置指南](./ENVIRONMENT_SETUP.md)
- [历史数据导入](./HISTORICAL_DATA_GUIDE.md)
