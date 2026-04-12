# Docker容器化部署指南

## 🎯 架构设计理念

### **为什么全部容器化？**

```
✅ 优势：
1. 环境一致性（Mac开发 = Windows调试 = 云部署）
2. 一键启动/停止所有服务
3. 便于迁移（本地→云服务器，一个命令）
4. 资源隔离（服务独立，互不影响）
5. 易于扩展（加服务只需改docker-compose.yml）
6. CI/CD友好（自动构建、部署）

📦 容器化内容：
  ✅ PostgreSQL数据库
  ✅ Dashboard服务
  ✅ Orchestrator服务
  ✅ Strategy服务
  ✅ Execution服务
  ⚠️  MT5（特殊处理，见后文）
```

---

## 🏗️ 三环境架构详解

### **环境1：Mac开发环境**

```yaml
用途: 代码开发、功能测试
运行: 本地Python（venv）或 Docker
MT5: Mock模式（模拟MT5接口）
数据库: SQLite（轻量）或 PostgreSQL容器

工作流:
  1. 写代码（VS Code）
  2. 本地测试（Mock MT5）
  3. Git提交
  4. 推送到远程仓库
```

**配置文件**：`config/development.yaml`

```yaml
mt5:
  mock_mode: true  # Mac使用Mock模式

database:
  host: "localhost"  # 本地PostgreSQL容器
  port: 5432
```

---

### **环境2：Windows调试环境** ⭐ 重点

```yaml
用途: MT5真实对接、完整功能测试
运行: Docker容器（所有服务）
MT5: 真实MT5 Terminal（连接Demo/Real账户）
数据库: PostgreSQL容器

工作流:
  1. Git拉取最新代码
  2. docker-compose up -d（启动所有服务）
  3. MT5 Terminal运行（真实行情）
  4. 测试完整流程
  5. 发现问题→修改代码→重启容器
```

**配置文件**：`config/windows.yaml`

```yaml
mt5:
  mock_mode: false  # 真实MT5
  use_investor: true  # 只读模式

database:
  host: "postgres"  # Docker网络内部名称
  port: 5432

services:
  execution:
    mt5_connection: "windows_native"  # 使用Windows原生MT5
```

---

### **环境3：云生产环境**

```yaml
用途: 7x24运行、策略验证、真实交易
运行: 云服务器 + Docker Compose
MT5: Wine运行MT5（Linux）或 Windows Server
数据库: PostgreSQL容器（持久化卷）

特点:
  ✅ 自动重启（容器崩溃自动恢复）
  ✅ 日志收集（集中监控）
  ✅ 数据备份（定时任务）
  ✅ Nginx反向代理（HTTPS访问）
  ✅ Validator服务（7x24运行）
```

**配置文件**：`config/production.yaml`

```yaml
mt5:
  mock_mode: false
  use_investor: false  # 真实交易（小心！）

database:
  host: "postgres"
  port: 5432

services:
  validator:
    enabled: true  # 启用实时验证服务
    demo_mode: true  # 使用Demo账户
```

---

## 📦 完整Docker Compose配置

### **docker-compose.yml（完整版）**

```yaml
version: '3.8'

services:
  # ========== 数据库 ==========
  postgres:
    image: postgres:16-alpine
    container_name: mt4-postgres
    environment:
      POSTGRES_DB: evo_trade
      POSTGRES_USER: evo_trade_user
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-evo_trade_pass_dev}
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./scripts/init_db.sql:/docker-entrypoint-initdb.d/init.sql:ro
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U evo_trade_user -d evo_trade"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped
    networks:
      - mt4-network

  # ========== Dashboard服务 ==========
  dashboard:
    build:
      context: .
      dockerfile: docker/Dockerfile.dashboard
    container_name: mt4-dashboard
    environment:
      - ENV=production
      - DATABASE_HOST=postgres
      - DATABASE_PORT=5432
    ports:
      - "8001:8001"
    depends_on:
      postgres:
        condition: service_healthy
    volumes:
      - ./logs:/app/logs
      - ./config:/app/config:ro
    restart: unless-stopped
    networks:
      - mt4-network

  # ========== Orchestrator服务 ==========
  orchestrator:
    build:
      context: .
      dockerfile: docker/Dockerfile.orchestrator
    container_name: mt4-orchestrator
    environment:
      - ENV=production
      - DATABASE_HOST=postgres
      - DATABASE_PORT=5432
    ports:
      - "8002:8002"
    depends_on:
      postgres:
        condition: service_healthy
    volumes:
      - ./logs:/app/logs
      - ./config:/app/config:ro
    restart: unless-stopped
    networks:
      - mt4-network

  # ========== Strategy服务 ==========
  strategy:
    build:
      context: .
      dockerfile: docker/Dockerfile.strategy
    container_name: mt4-strategy
    environment:
      - ENV=production
      - DATABASE_HOST=postgres
      - DATABASE_PORT=5432
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy
    volumes:
      - ./logs:/app/logs
      - ./config:/app/config:ro
    restart: unless-stopped
    networks:
      - mt4-network

  # ========== Execution服务 ==========
  # 注意：Execution服务需要连接MT5，部署需特殊处理
  execution:
    build:
      context: .
      dockerfile: docker/Dockerfile.execution
    container_name: mt4-execution
    environment:
      - ENV=production
      - DATABASE_HOST=postgres
      - DATABASE_PORT=5432
      - MT5_MODE=${MT5_MODE:-mock}  # mock/windows/wine
    ports:
      - "8003:8003"
    depends_on:
      postgres:
        condition: service_healthy
    volumes:
      - ./logs:/app/logs
      - ./config:/app/config:ro
      # Windows环境：挂载MT5数据目录
      # - C:/Program Files/MetaTrader 5:/mt5:ro
    restart: unless-stopped
    networks:
      - mt4-network
    # Windows环境需要：
    # extra_hosts:
    #   - "host.docker.internal:host-gateway"

  # ========== Validator服务（可选）==========
  validator:
    build:
      context: .
      dockerfile: docker/Dockerfile.validator
    container_name: mt4-validator
    environment:
      - ENV=production
      - DATABASE_HOST=postgres
      - MT5_MODE=${MT5_MODE:-mock}
    depends_on:
      postgres:
        condition: service_healthy
    volumes:
      - ./logs:/app/logs
      - ./config:/app/config:ro
    restart: unless-stopped
    networks:
      - mt4-network
    profiles:
      - validator  # 可选启动：docker-compose --profile validator up

  # ========== Nginx反向代理（生产环境）==========
  nginx:
    image: nginx:alpine
    container_name: mt4-nginx
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./docker/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro  # HTTPS证书
    depends_on:
      - dashboard
    restart: unless-stopped
    networks:
      - mt4-network
    profiles:
      - production  # 生产环境启动

volumes:
  postgres_data:
    name: mt4-postgres-data

networks:
  mt4-network:
    name: mt4-network
    driver: bridge
```

---

## 🐳 Dockerfile示例

### **Dockerfile.dashboard**

```dockerfile
# Base image
FROM python:3.11-slim

# 工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制源代码
COPY src/ /app/src/
COPY config/ /app/config/

# 暴露端口
EXPOSE 8001

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD curl -f http://localhost:8001/health || exit 1

# 启动命令
CMD ["uvicorn", "src.services.dashboard.api.app:app", \
     "--host", "0.0.0.0", "--port", "8001"]
```

### **其他服务Dockerfile类似，只需修改端口和启动命令**

---

## 🪟 Windows环境特殊配置

### **MT5连接方式**

Windows上Docker容器连接MT5有三种方式：

#### **方式1：Host模式（推荐）** ✅

```yaml
# docker-compose.override.yml（Windows专用）
services:
  execution:
    environment:
      - MT5_HOST=host.docker.internal  # 访问宿主机
      - MT5_MODE=windows_native
    extra_hosts:
      - "host.docker.internal:host-gateway"
```

```python
# src/common/mt5/client.py
if os.getenv('MT5_MODE') == 'windows_native':
    # 通过命名管道或COM连接宿主机MT5
    mt5.initialize()
```

#### **方式2：网络共享**

```yaml
services:
  execution:
    network_mode: "host"  # 共享宿主机网络
```

**缺点**：Docker网络隔离失效

#### **方式3：Wine容器（Linux云环境）**

```yaml
services:
  mt5-wine:
    image: custom/mt5-wine  # 需要自己构建
    volumes:
      - ./mt5_config:/root/.wine/drive_c/MT5
```

**复杂度高，不推荐初期使用**

---

## ☁️  云部署方案

### **方案对比**

| 方案 | 优点 | 缺点 | 成本/月 | 推荐度 |
|------|------|------|---------|--------|
| **AWS EC2 Windows** | MT5原生支持 | 贵 | $50-100 | ⭐⭐⭐ |
| **阿里云 Windows** | 国内快 | 需备案 | ¥200-400 | ⭐⭐⭐ |
| **Vultr Windows** | 便宜灵活 | 海外 | $20-40 | ⭐⭐⭐⭐⭐ |
| **DigitalOcean + Wine** | 便宜 | MT5兼容差 | $12-20 | ⭐⭐ |

### **推荐方案：Vultr Windows VPS** ✅

```yaml
配置：
  CPU: 2核
  内存: 4GB
  存储: 80GB SSD
  系统: Windows Server 2022
  位置: 新加坡/日本（低延迟MT5）
  
成本: $28/月

优势:
  ✅ MT5原生支持
  ✅ Docker Desktop可用
  ✅ 价格合理
  ✅ 按小时计费（测试成本低）
  ✅ 无需备案
```

---

## 🚀 部署流程

### **Step 1：Windows本地调试**

```bash
# 1. 克隆代码
git clone <repo> && cd MT4-Factory

# 2. 启动所有服务
docker-compose up -d

# 3. 查看日志
docker-compose logs -f

# 4. 访问Dashboard
# http://localhost:8001

# 5. 测试MT5连接
# Execution服务会自动连接本地MT5
```

### **Step 2：推送到云服务器**

```bash
# 在云服务器上

# 1. 安装Docker
# 参考Docker官方文档

# 2. 克隆代码
git clone <repo> && cd MT4-Factory

# 3. 配置环境变量
cp .env.example .env
vim .env  # 修改密码等

# 4. 启动生产环境
docker-compose --profile production up -d

# 5. 配置Nginx（HTTPS）
# 申请Let's Encrypt证书
certbot --nginx -d your-domain.com

# 6. 设置自动重启
docker update --restart=unless-stopped $(docker ps -aq)
```

### **Step 3：CI/CD自动化（可选）**

```yaml
# .github/workflows/deploy.yml
name: Deploy to Cloud

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Deploy to Server
        uses: appleboy/ssh-action@master
        with:
          host: ${{ secrets.SERVER_IP }}
          username: ${{ secrets.SERVER_USER }}
          key: ${{ secrets.SSH_KEY }}
          script: |
            cd /opt/MT4-Factory
            git pull
            docker-compose up -d --build
```

---

## 📊 环境对比总结

| 维度 | Mac开发 | Windows调试 | 云生产 |
|------|---------|-------------|--------|
| **代码运行** | venv 或 容器 | 容器 ✅ | 容器 ✅ |
| **数据库** | SQLite 或 容器 | 容器 ✅ | 容器 ✅ |
| **MT5** | Mock | 真实 ✅ | 真实 ✅ |
| **用途** | 开发、快速测试 | 完整功能调试 | 7x24运行 |
| **网络** | 本地 | 本地/VPN | 公网 |
| **成本** | $0 | $0 | $20-50/月 |

---

## 🎯 推荐工作流

```
┌─────────────────────────────────────────────────────────┐
│                  日常开发流程                            │
└─────────────────────────────────────────────────────────┘

Mac开发：
  1. 写代码（VS Code）
  2. 本地测试（Mock MT5）
  3. Git commit & push

Windows调试：
  1. Git pull
  2. docker-compose up -d
  3. 测试MT5真实对接
  4. 发现问题→反馈给Mac开发

云部署：
  1. Git push to main
  2. CI/CD自动部署（或手动部署）
  3. 监控运行状态
  4. 7x24运行Validator服务
```

---

## 💡 总结建议

### **立即可做**

```
✅ 1. 创建docker-compose.yml（已完成）
✅ 2. Mac本地测试PostgreSQL容器
✅ 3. Windows上用Docker运行所有服务
```

### **近期规划（1-2周）**

```
⏸️  1. 编写各服务的Dockerfile
⏸️  2. Windows环境完整测试
⏸️  3. 优化容器启动速度
```

### **未来规划（1-3个月）**

```
🔮 1. 部署到云服务器（Vultr Windows）
🔮 2. 配置Nginx + HTTPS
🔮 3. 设置CI/CD自动部署
🔮 4. Validator服务7x24运行
```

---

## ✅ 关键决策

**Q: 代码应该跑在容器里吗？**

**A: 是的，强烈推荐！** ✅

```
理由：
  1. 环境一致（Mac = Windows = 云）
  2. 便于迁移（本地→云，一个命令）
  3. 易于扩展（加服务只需改配置）
  4. 生产就绪（Docker是标准）
  5. 未来云部署必需
  
实施：
  - Mac开发：可用venv（快速）或容器（一致性）
  - Windows调试：必须用容器 ✅
  - 云生产：必须用容器 ✅
```

**文档已创建，随时参考实施！** 📚
