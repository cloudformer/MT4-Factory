# Windows快速启动指南

## 🎯 目标

在Windows系统上启动完整的MT4 Factory系统，包括：
- PostgreSQL数据库（容器）
- Validator服务（容器，7x24验证策略）
- MT5 API Bridge（宿主机，包装MT5）
- MT5 Terminal（宿主机，真实MT5）

---

## 📋 前置条件

### 1. 软件安装

```
✅ Docker Desktop for Windows
✅ Python 3.11+
✅ MetaTrader 5 Terminal
✅ Git
```

### 2. MT5账户

```
需要准备：
- MT5 Demo账户（用于Validator）
- 账号、密码、服务器名称
```

---

## 🚀 启动步骤

### **Step 1：配置环境变量**

```bash
# 进入项目目录
cd MT4-Factory

# 复制环境变量模板
copy .env.example .env

# 编辑.env文件，填写实际值
notepad .env
```

**必填项**：
```bash
MT5_DEMO_LOGIN=your_demo_account        # 你的Demo账号
MT5_DEMO_PASSWORD=your_demo_password    # 你的Demo密码
MT5_DEMO_SERVER=MetaQuotes-Demo         # 你的服务器名称
```

---

### **Step 2：配置windows.yaml**

```bash
# 编辑配置文件
notepad config\windows.yaml
```

**需要修改的地方**：
```yaml
mt5:
  login: 5049130509              # ← 改为你的Demo账号
  password: "your_password_here" # ← 改为你的密码
  server: "MetaQuotes-Demo"      # ← 改为你的服务器
```

---

### **Step 3：启动MT5 API Bridge**

**方式1：使用启动脚本（推荐）**

```bash
# 双击运行
scripts\start_mt5_api_bridge.bat
```

**方式2：手动启动**

```bash
# 设置环境变量
set MT5_API_HOST=0.0.0.0
set MT5_API_PORT=9090
set MT5_API_KEYS=demo_key_12345

# 启动服务
python -m src.services.mt5_api_bridge.app
```

**验证启动成功**：
```bash
# 浏览器访问
http://localhost:9090/health

# 或使用curl
curl http://localhost:9090/health
```

---

### **Step 4：启动PostgreSQL容器**

```bash
# 启动PostgreSQL
docker-compose up -d postgres

# 查看日志（确认启动成功）
docker-compose logs -f postgres

# 按Ctrl+C退出日志查看
```

**验证数据库**：
```bash
# 连接PostgreSQL
docker exec -it mt4-factory-postgres psql -U evo_trade_user -d evo_trade

# 查看表
\dt

# 退出
\q
```

---

### **Step 5：数据库迁移（如果需要）**

```bash
# 添加Validator字段（首次运行）
docker exec -it mt4-factory-postgres psql -U evo_trade_user -d evo_trade -f /app/scripts/add_validator_fields.sql

# 或者从宿主机执行
docker exec -i mt4-factory-postgres psql -U evo_trade_user -d evo_trade < scripts\add_validator_fields.sql
```

---

### **Step 6：启动Validator容器**

```bash
# 构建并启动Validator
docker-compose up -d validator

# 查看日志
docker-compose logs -f validator
```

**预期日志输出**：
```
=============================================================
🚀 启动Validator服务
   并发数: 20
   MT5: host.docker.internal:9090
=============================================================
✅ MT5连接测试成功
✅ MT5数据获取成功（测试获取10根K线）
🔄 执行首次验证...
📊 找到 X 个Active策略，开始并发验证（并发数：20）...
```

---

## ✅ 验证完整流程

### **1. 测试MT5 API Bridge**

```bash
# 健康检查
curl http://localhost:9090/health

# 获取K线数据
curl "http://localhost:9090/bars/EURUSD?timeframe=H1&count=10"

# 获取报价
curl http://localhost:9090/tick/EURUSD
```

### **2. 测试Validator服务**

```bash
# 查看Validator日志
docker-compose logs -f validator

# 应该看到：
# ✅ 批量验证完成
# 总计: X | 成功: Y | 失败: Z
# 耗时: X秒
```

### **3. 查看数据库验证结果**

```bash
# 连接数据库
docker exec -it mt4-factory-postgres psql -U evo_trade_user -d evo_trade

# 查询验证结果
SELECT 
  id, 
  name, 
  status,
  last_validation_time,
  validation_win_rate,
  validation_total_return
FROM strategies 
WHERE status = 'active'
ORDER BY last_validation_time DESC;
```

---

## 📊 服务管理

### **查看所有服务状态**

```bash
docker-compose ps
```

### **查看服务日志**

```bash
# Validator日志
docker-compose logs -f validator

# PostgreSQL日志
docker-compose logs -f postgres

# 所有服务日志
docker-compose logs -f
```

### **重启服务**

```bash
# 重启Validator
docker-compose restart validator

# 重启PostgreSQL
docker-compose restart postgres

# 重启所有服务
docker-compose restart
```

### **停止服务**

```bash
# 停止Validator
docker-compose stop validator

# 停止所有服务
docker-compose stop

# 停止并删除容器
docker-compose down
```

---

## 🔧 常见问题

### **问题1：MT5 API Bridge启动失败**

```
错误：ModuleNotFoundError: No module named 'MetaTrader5'

解决：
pip install MetaTrader5

或者：
pip install -r requirements.txt
```

### **问题2：Validator无法连接MT5**

```
错误：❌ MT5连接失败

解决：
1. 确认MT5 API Bridge已启动（http://localhost:9090/health）
2. 确认Docker Desktop已启动
3. 检查config/windows.yaml中的MT5配置
4. 查看MT5 Terminal是否已登录
```

### **问题3：Validator无法连接数据库**

```
错误：could not connect to server

解决：
1. 确认PostgreSQL容器已启动：docker-compose ps
2. 等待PostgreSQL完全启动（约10-30秒）
3. 查看PostgreSQL日志：docker-compose logs postgres
4. 重启Validator：docker-compose restart validator
```

### **问题4：Validator未找到Active策略**

```
日志：⚠️  未找到Active策略

解决：
1. 打开Dashboard: http://localhost:8001
2. 生成一些策略
3. 将策略状态改为"Active"
4. 等待Validator下次执行（默认每小时）
5. 或手动重启Validator触发验证
```

---

## 🎯 性能监控

### **查看资源使用**

```bash
# Docker资源使用
docker stats

# Validator容器资源
docker stats mt4-factory-validator
```

### **调整并发数**

编辑 `config/windows.yaml`：

```yaml
validator:
  concurrency: 50  # 提高到50（默认20）
```

然后重启：
```bash
docker-compose restart validator
```

---

## 📈 扩展配置

### **多Validator实例（处理更多策略）**

编辑 `docker-compose.yml`：

```yaml
services:
  validator1:
    # ... 同validator配置
    container_name: mt4-factory-validator-1
  
  validator2:
    # ... 同validator配置
    container_name: mt4-factory-validator-2
  
  validator3:
    # ... 同validator配置
    container_name: mt4-factory-validator-3
```

启动：
```bash
docker-compose up -d validator1 validator2 validator3
```

---

## ✅ 完整系统架构

```
Windows宿主机：
├─ MT5 Terminal（原生进程）
├─ MT5 API Bridge（Python进程，端口9090）
└─ Docker Desktop
    ├─ PostgreSQL容器（端口5432）
    └─ Validator容器（连接host.docker.internal:9090）

验证流程：
1. Validator容器（每小时触发）
2. 查询数据库 → 获取所有Active策略
3. 并发20个协程 → HTTP请求 → host.docker.internal:9090
4. MT5 API Bridge → 本地MT5 Terminal → 获取K线数据
5. Validator运行回测 → 计算指标
6. 更新数据库 → 验证结果
```

---

## 🚀 下一步

完成上述步骤后：

1. ✅ 打开Dashboard：http://localhost:8001
2. ✅ 生成策略并设为Active
3. ✅ 观察Validator日志（每小时自动验证）
4. ✅ 查看数据库中的验证结果

**系统已就绪！可以开始策略验证了！** 🎉

---

## 📚 相关文档

- [MT5统一客户端使用指南](./MT5_UNIFIED_CLIENT_GUIDE.md)
- [Validator并发架构](./VALIDATOR_CONCURRENT_ARCHITECTURE.md)
- [Docker部署指南](./DOCKER_DEPLOYMENT_GUIDE.md)
- [统一架构方案](./UNIFIED_ARCHITECTURE_PLAN.md)
