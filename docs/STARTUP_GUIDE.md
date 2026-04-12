# MT4-Factory 启动指南

## 环境配置

系统使用 `DEVICE` 环境变量来选择配置文件：

| 环境变量 | 配置文件 | 数据库 | 用途 |
|---------|---------|--------|------|
| `DEVICE=mac` | `config/mac.yaml` | SQLite | Mac本地开发 |
| `DEVICE=windows` | `config/windows.yaml` | PostgreSQL (Docker) | Windows本地/Docker **【默认】** |
| `DEVICE=cloud` | `config/cloud.yaml` | PostgreSQL (Cloud) | 生产环境 |

**配置加载优先级**：
1. 环境变量 `DEVICE`
2. 默认值：`windows`

---

## 启动命令

### **Mac本地开发**

```bash
# 激活虚拟环境
source venv/bin/activate

# 设置环境变量并启动Dashboard
export DEVICE=mac && uvicorn src.services.dashboard.api.app:app --host 0.0.0.0 --port 8001

# 后台启动（可选）
export DEVICE=mac && nohup uvicorn src.services.dashboard.api.app:app --host 0.0.0.0 --port 8001 > logs/dashboard.log 2>&1 &
```

**特点**：
- 使用SQLite数据库（无需Docker）
- 数据文件：`data/evo_trade.db`
- 轻量级，适合快速开发

---

### **Windows本地/Docker**

```bash
# 激活虚拟环境
venv\Scripts\activate

# 启动Dashboard（不设置DEVICE，自动使用windows配置）
uvicorn src.services.dashboard.api.app:app --host 0.0.0.0 --port 8001

# 或显式指定DEVICE
set DEVICE=windows
uvicorn src.services.dashboard.api.app:app --host 0.0.0.0 --port 8001
```

**前置条件**：
```bash
# 启动PostgreSQL数据库
docker-compose up -d postgres

# 启动MT5 API Bridge（如果需要）
scripts\start_mt5_api_bridge.bat

# 启动Validator（可选）
docker-compose up -d validator
```

**特点**：
- 使用PostgreSQL数据库（Docker容器）
- 支持MT5实时连接
- 适合完整功能测试

---

### **生产环境（云端）**

```bash
# 激活虚拟环境
source venv/bin/activate

# 设置环境变量并启动Dashboard
export DEVICE=cloud && uvicorn src.services.dashboard.api.app:app --host 0.0.0.0 --port 8001

# 使用gunicorn（推荐用于生产）
export DEVICE=cloud && gunicorn src.services.dashboard.api.app:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8001
```

**特点**：
- 连接云端PostgreSQL数据库
- 连接远程Windows VPS上的MT5
- 7x24运行

---

## 启动所有服务

### **Mac本地**

```bash
# Dashboard（端口8001）
export DEVICE=mac && uvicorn src.services.dashboard.api.app:app --host 0.0.0.0 --port 8001 &

# Orchestrator（端口8002）
export DEVICE=mac && uvicorn src.services.orchestrator.main:app --host 0.0.0.0 --port 8002 &

# Strategy Service（端口8003）
export DEVICE=mac && python -m src.services.strategy.app &

# Signal Service（端口8004）
export DEVICE=mac && python -m src.services.signal.app &

# Execution Service（端口8005）- 生产环境才需要
# export DEVICE=mac && python -m src.services.execution.app &
```

---

### **Windows Docker环境**

```bash
# 启动所有容器
docker-compose up -d

# 查看运行状态
docker-compose ps

# 查看日志
docker-compose logs -f
```

**包含服务**：
- PostgreSQL（端口5432）
- Validator（端口8080）
- pgAdmin（可选，端口5050）

**本地服务**（需要手动启动）：
- Dashboard（端口8001）
- Orchestrator（端口8002）
- MT5 API Bridge（端口9090）- 在Windows上运行

---

### **生产环境（云端）**

使用Docker Compose或Kubernetes部署：

```bash
# Docker Compose方式
export DEVICE=cloud && docker-compose -f docker-compose.prod.yml up -d

# 或使用systemd服务管理
sudo systemctl start mt4-factory-dashboard
sudo systemctl start mt4-factory-orchestrator
sudo systemctl start mt4-factory-validator
```

---

## 服务端口映射

| 服务 | 端口 | 说明 |
|------|------|------|
| Dashboard | 8001 | Web UI界面 |
| Orchestrator | 8002 | 策略编排服务 |
| Strategy | 8003 | 策略生成服务 |
| Signal | 8004 | 信号生成服务 |
| Execution | 8005 | 订单执行服务 |
| Validator | 8080 | 策略验证服务 |
| MT5 API Bridge | 9090 | MT5 HTTP接口 |
| PostgreSQL | 5432 | 数据库 |
| pgAdmin | 5050 | 数据库管理界面 |

---

## 健康检查

```bash
# Dashboard
curl http://localhost:8001/health

# Orchestrator
curl http://localhost:8002/health

# Validator
curl http://localhost:8080/health

# MT5 API Bridge
curl http://localhost:9090/health

# PostgreSQL
docker exec -it mt4-factory-postgres pg_isready -U evo_trade_user
```

---

## 停止服务

### **Mac本地**

```bash
# 停止单个服务
pkill -f "uvicorn src.services.dashboard"

# 停止所有Python服务
pkill -f "uvicorn"
```

### **Windows Docker**

```bash
# 停止所有容器
docker-compose down

# 停止但保留数据
docker-compose stop

# 停止并删除数据
docker-compose down -v
```

---

## 常见问题

### **1. Mac本地无法连接数据库**

```bash
# 检查SQLite文件是否存在
ls -lh data/evo_trade.db

# 如果不存在，创建并初始化
mkdir -p data
export DEVICE=mac
python -c "from src.common.database.connection import db; from src.common.models.base import Base; Base.metadata.create_all(db.engine)"
```

### **2. Windows无法连接PostgreSQL**

```bash
# 检查Docker容器状态
docker-compose ps postgres

# 如果未运行，启动PostgreSQL
docker-compose up -d postgres

# 查看日志
docker-compose logs postgres
```

### **3. 端口已被占用**

```bash
# Mac查找占用端口的进程
lsof -i :8001

# Windows查找占用端口的进程
netstat -ano | findstr :8001

# 杀死进程
kill <PID>  # Mac
taskkill /PID <PID> /F  # Windows
```

### **4. 配置文件找不到**

```bash
# 检查DEVICE环境变量
echo $DEVICE  # Mac/Linux
echo %DEVICE%  # Windows

# 检查配置文件是否存在
ls -lh config/  # Mac/Linux
dir config\  # Windows
```

---

## 开发建议

### **Mac上开发**
- 使用 `DEVICE=mac` + SQLite
- 快速启动，无需Docker
- 适合代码开发和UI调试

### **Windows上测试**
- 使用 `DEVICE=windows` + PostgreSQL Docker
- 启动MT5 API Bridge测试实时数据
- 完整功能测试

### **云端部署**
- 使用 `DEVICE=cloud` + PostgreSQL Cloud
- 连接远程MT5 API
- 生产环境运行

---

## 快速启动脚本

### **Mac快速启动**

创建 `scripts/start_mac.sh`：
```bash
#!/bin/bash
export DEVICE=mac
source venv/bin/activate
uvicorn src.services.dashboard.api.app:app --host 0.0.0.0 --port 8001
```

### **Windows快速启动**

创建 `scripts/start_windows.bat`：
```bat
@echo off
set DEVICE=windows
call venv\Scripts\activate
uvicorn src.services.dashboard.api.app:app --host 0.0.0.0 --port 8001
```

---

## 相关文档

- [Validator功能总结](./VALIDATOR_FEATURES_SUMMARY.md)
- [配置文件说明](../config/README.md)
- [架构设计文档](./ARCHITECTURE.md)
- [Windows快速启动](./QUICK_START_WINDOWS.md)
