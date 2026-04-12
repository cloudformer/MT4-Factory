# MT5 API Bridge 启动指南

## 概述

MT5 API Bridge是一个HTTP服务，运行在Windows系统上，为Docker容器（Linux）提供访问MT5的能力。

```
容器(Linux) → HTTP → API Bridge(Windows) → COM → MT5终端(Windows)
```

---

## 前置条件

### 1. Windows系统
- Windows 10/11 或 Windows Server 2019/2022
- **必须是Windows**（MT5和MetaTrader5库仅支持Windows）

### 2. 安装MT5终端
```
下载地址: https://www.metatrader5.com/en/download
或从经纪商官网下载（ICMarkets、Pepperstone等）
```

安装后：
- 登录Demo或Real账户
- 保持MT5运行（不要关闭）

### 3. 安装Python
```
下载地址: https://www.python.org/downloads/
推荐版本: Python 3.11 64位
```

安装时勾选：
- ✅ Add Python to PATH
- ✅ Install pip

### 4. 安装依赖库
```bash
# 在项目根目录执行
pip install -r requirements.txt

# 或单独安装
pip install MetaTrader5
pip install fastapi
pip install uvicorn
```

---

## 启动方式

### 方式1：命令行启动（开发测试）

```bash
# 1. 打开PowerShell或CMD
# 2. 进入项目目录
cd C:\path\to\MT4-Factory

# 3. 启动API Bridge
python -m uvicorn src.services.mt5_api_bridge.app:app --host 0.0.0.0 --port 9090

# 输出：
# INFO:     Uvicorn running on http://0.0.0.0:9090 (Press CTRL+C to quit)
# INFO:     Started reloader process [12345]
# INFO:     Started server process [12346]
# INFO:     Waiting for application startup.
# INFO:     Application startup complete.
```

**参数说明**：
- `--host 0.0.0.0`：监听所有网络接口（允许远程访问）
- `--port 9090`：监听端口（可修改）
- `--reload`：代码修改自动重载（开发环境）

### 方式2：批处理脚本启动

创建启动脚本：`scripts/windows/start_mt5_bridge.bat`

```batch
@echo off
echo Starting MT5 API Bridge...

cd C:\path\to\MT4-Factory

REM 可选：设置环境变量
set MT5_API_KEYS=your_api_key_here

REM 启动服务
python -m uvicorn src.services.mt5_api_bridge.app:app --host 0.0.0.0 --port 9090

pause
```

双击运行即可。

### 方式3：Windows服务（生产环境推荐）⭐

使用**NSSM**（Non-Sucking Service Manager）将Python脚本注册为Windows服务。

#### 安装NSSM

```
下载: https://nssm.cc/download
解压: C:\nssm\nssm.exe
```

#### 注册服务

```powershell
# 1. 以管理员身份运行PowerShell

# 2. 注册服务
C:\nssm\nssm.exe install MT5-API-Bridge

# 3. 在弹出窗口配置:
Path: C:\Python311\python.exe
Startup directory: C:\MT4-Factory
Arguments: -m uvicorn src.services.mt5_api_bridge.app:app --host 0.0.0.0 --port 9090

# 4. 启动服务
nssm start MT5-API-Bridge

# 5. 设置自动启动
nssm set MT5-API-Bridge Start SERVICE_AUTO_START
```

#### 服务管理

```powershell
# 查看状态
nssm status MT5-API-Bridge

# 停止服务
nssm stop MT5-API-Bridge

# 重启服务
nssm restart MT5-API-Bridge

# 删除服务
nssm remove MT5-API-Bridge confirm
```

---

## 验证运行

### 1. 浏览器访问

```
打开浏览器，访问:
http://localhost:9090/docs

应该看到FastAPI自动生成的API文档界面
```

### 2. 健康检查

```bash
# PowerShell或CMD
curl http://localhost:9090/health

# 或浏览器访问
http://localhost:9090/health

# 预期输出:
{
  "status": "ok",
  "mt5_initialized": true,
  "terminal_info": {
    "version": 2650,
    "build": 2650,
    "name": "MetaQuotes-Demo"
  }
}
```

### 3. 测试API

```bash
# 获取账户信息
curl http://localhost:9090/account

# 获取品种信息
curl "http://localhost:9090/symbol?symbol=EURUSD"

# 获取K线数据
curl "http://localhost:9090/bars?symbol=EURUSD&timeframe=H1&count=10"
```

---

## Docker容器访问

### Windows本地开发

容器通过`host.docker.internal`访问：

```yaml
# config/windows.yaml
mt5_hosts:
  demo_1:
    host: "host.docker.internal"    # Docker特殊地址
    port: 9090
```

测试：
```bash
# 容器内测试
docker exec -it mt4-factory-validator curl http://host.docker.internal:9090/health
```

### Cloud远程访问

```yaml
# config/cloud.yaml
mt5_hosts:
  demo_1:
    host: "52.10.20.30"             # Windows VPS公网IP
    port: 9090
```

⚠️ **防火墙配置**：
```powershell
# Windows VPS上开放9090端口
New-NetFirewallRule -DisplayName "MT5 API Bridge" -Direction Inbound -LocalPort 9090 -Protocol TCP -Action Allow
```

---

## 安全配置（生产环境）

### 启用API密钥认证

```bash
# 1. 设置环境变量（Windows）
set MT5_API_KEYS=your_secret_key_123,another_key_456

# 2. 重启API Bridge

# 3. 访问时需要带上密钥
curl -H "Authorization: Bearer your_secret_key_123" http://localhost:9090/health
```

### Docker配置中添加密钥

```yaml
# config/windows.yaml
mt5_hosts:
  demo_1:
    host: "host.docker.internal"
    port: 9090
    api_key: "your_secret_key_123"   # 添加API密钥
```

---

## 开机自启动

### 方式1：使用NSSM服务（推荐）

已经注册为服务的会自动启动，无需额外配置。

### 方式2：任务计划程序

```
1. Win + R → taskschd.msc
2. 创建基本任务
   名称: MT5 API Bridge
   触发器: 计算机启动时
   操作: 启动程序
   程序: C:\path\to\start_mt5_bridge.bat
3. 勾选"使用最高权限运行"
```

### 方式3：启动文件夹

```
1. Win + R → shell:startup
2. 复制 start_mt5_bridge.bat 快捷方式到此文件夹
3. 重启电脑测试
```

---

## 日志和监控

### 查看日志

```bash
# 命令行启动的日志直接在控制台

# NSSM服务日志
# 1. 配置日志文件
nssm set MT5-API-Bridge AppStdout C:\MT4-Factory\logs\mt5_bridge_stdout.log
nssm set MT5-API-Bridge AppStderr C:\MT4-Factory\logs\mt5_bridge_stderr.log

# 2. 查看日志
type C:\MT4-Factory\logs\mt5_bridge_stdout.log
```

### 监控进程

```powershell
# 查看进程
Get-Process | Where-Object { $_.ProcessName -like "*python*" }

# 查看端口占用
netstat -ano | findstr :9090
```

---

## 故障排查

### Q1: ModuleNotFoundError: No module named 'MetaTrader5'

**原因**：未安装MetaTrader5库

**解决**：
```bash
pip install MetaTrader5
```

### Q2: MT5 initialize failed

**原因**：
1. MT5终端未运行
2. MT5终端未登录账户
3. Python和MT5位数不匹配（32位vs64位）

**解决**：
```bash
# 1. 启动MT5终端并登录
# 2. 确认Python是64位（推荐）
python --version
# Python 3.11.0 (64-bit)

# 3. 测试连接
python -c "import MetaTrader5 as mt5; print(mt5.initialize())"
# 输出: True
```

### Q3: 容器连接不到API Bridge

**原因**：
1. API Bridge未启动
2. 防火墙阻止
3. Docker网络配置问题

**解决**：
```bash
# 1. Windows宿主机测试
curl http://localhost:9090/health

# 2. 容器内测试
docker exec -it mt4-factory-validator ping host.docker.internal
docker exec -it mt4-factory-validator curl http://host.docker.internal:9090/health

# 3. 检查防火墙
# Windows Defender 防火墙 → 允许应用通过防火墙 → Python
```

### Q4: 端口已被占用

**错误**：
```
ERROR:    [Errno 10048] error while attempting to bind on address ('0.0.0.0', 9090): 通常每个套接字地址(协议/网络地址/端口)只允许使用一次。
```

**解决**：
```powershell
# 1. 查找占用端口的进程
netstat -ano | findstr :9090

# 2. 结束进程
taskkill /PID <进程ID> /F

# 3. 或使用其他端口
python -m uvicorn src.services.mt5_api_bridge.app:app --host 0.0.0.0 --port 9091
```

---

## 完整启动检查清单

### Windows本地开发

- [ ] 1. MT5终端已启动并登录
- [ ] 2. Python已安装（3.11+ 64位）
- [ ] 3. 依赖已安装（pip install -r requirements.txt）
- [ ] 4. 启动API Bridge（python -m uvicorn ...）
- [ ] 5. 验证健康检查（http://localhost:9090/health）
- [ ] 6. Docker Desktop已启动
- [ ] 7. 启动业务容器（scripts\windows\start_all.bat）
- [ ] 8. 验证容器连接（docker-compose logs validator）

### Cloud生产环境

- [ ] 1. Windows VPS已配置
- [ ] 2. mstsc远程连接VPS成功
- [ ] 3. MT5终端已启动并登录Real账户
- [ ] 4. API Bridge注册为Windows服务（NSSM）
- [ ] 5. API Bridge服务已启动
- [ ] 6. 防火墙9090端口已开放
- [ ] 7. API密钥已配置（MT5_API_KEYS环境变量）
- [ ] 8. Linux服务器能访问VPS的9090端口
- [ ] 9. Docker服务已启动（bash scripts/cloud/start_all.sh）
- [ ] 10. 监控和告警已配置

---

## 相关文档

- [MT5连接架构](./MT5_CONNECTION_ARCHITECTURE.md)
- [MT5主机配置指南](../config/MT5_HOSTS_GUIDE.md)
- [Docker部署指南](./DOCKER_DEPLOYMENT.md)
- [API Bridge源码](../src/services/mt5_api_bridge/app.py)
