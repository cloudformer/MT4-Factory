# MT5连接快速参考卡

## 🎯 核心依赖

```
┌─────────────────────────────────────────────────────┐
│  必需组件（Windows系统）                              │
├─────────────────────────────────────────────────────┤
│                                                     │
│  1. ✅ Windows系统                                   │
│     └─ Windows 10/11 或 Server 2019/2022           │
│     └─ MT5仅支持Windows（不支持Linux/Mac）          │
│                                                     │
│  2. ✅ MT5终端 (MetaTrader5.exe)                     │
│     └─ 下载: metatrader5.com/en/download           │
│     └─ 或从经纪商官网下载                            │
│     └─ 必须保持运行+登录账户                         │
│                                                     │
│  3. ✅ Python 3.11+ (64位)                           │
│     └─ 下载: python.org/downloads                  │
│     └─ 勾选: Add Python to PATH                    │
│                                                     │
│  4. ✅ MetaTrader5 Python库                         │
│     └─ 安装: pip install MetaTrader5               │
│     └─ 仅Windows支持！                              │
│                                                     │
│  5. ✅ MT5 API Bridge (HTTP服务)                     │
│     └─ 位置: src/services/mt5_api_bridge/app.py   │
│     └─ 启动: scripts\windows\start_mt5_bridge.bat │
│     └─ 端口: 9090                                  │
│                                                     │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│  可选组件（根据环境）                                 │
├─────────────────────────────────────────────────────┤
│                                                     │
│  6. ⭐ Docker Desktop (Windows本地)                  │
│     └─ 运行业务容器                                  │
│     └─ 容器通过 host.docker.internal 访问宿主机      │
│                                                     │
│  7. ⭐ mstsc (远程桌面) - Cloud环境                   │
│     └─ 管理远程Windows VPS                          │
│     └─ Win+R → mstsc → 输入VPS IP                  │
│                                                     │
│  8. ⭐ NSSM (服务管理器) - 生产环境                   │
│     └─ 下载: nssm.cc/download                      │
│     └─ 将API Bridge注册为Windows服务                │
│     └─ 开机自启动                                    │
│                                                     │
└─────────────────────────────────────────────────────┘
```

---

## 📋 启动检查清单

### Windows本地开发

```bash
# ✅ 步骤1: 启动MT5终端
双击MT5图标 → 登录Demo账户 → 保持运行

# ✅ 步骤2: 启动MT5 API Bridge
scripts\windows\start_mt5_bridge.bat
# 验证: http://localhost:9090/health

# ✅ 步骤3: 启动Docker服务
scripts\windows\start_all.bat

# ✅ 步骤4: 验证连接
docker-compose logs -f validator
# 应该看到: Connected to MT5: demo_1 (host.docker.internal:9090)
```

### Cloud生产环境

```bash
# ========== Windows VPS ==========

# ✅ 1. 远程连接
mstsc /v:52.10.20.30

# ✅ 2. 启动MT5终端
启动MetaTrader5 → 登录Real账户

# ✅ 3. 启动API Bridge服务
services.msc → 启动 "MT5-API-Bridge"

# ✅ 4. 验证服务
http://localhost:9090/health

# ✅ 5. 开放防火墙
防火墙 → 入站规则 → 9090端口


# ========== Linux服务器 ==========

# ✅ 1. 启动Docker服务
bash scripts/cloud/start_all.sh

# ✅ 2. 验证连接
docker-compose logs -f validator
# 应该看到: Connected to MT5: demo_1 (52.10.20.30:9090)
```

---

## 🔗 连接流程

```
Windows本地开发:
Validator容器 (Linux)
    ↓ HTTP
host.docker.internal:9090
    ↓
MT5 API Bridge (Windows)
    ↓ COM接口
MT5终端进程 (MetaTrader5.exe)
    ↓ 网络
MetaQuotes服务器


Cloud生产环境:
Validator容器 (Linux服务器)
    ↓ HTTP
52.10.20.30:9090
    ↓ (公网)
MT5 API Bridge (Windows VPS)
    ↓ COM接口
MT5终端进程 (MetaTrader5.exe)
    ↓ 网络
ICMarkets服务器
```

---

## 🛠️ 常用命令

### MT5 API Bridge

```bash
# 启动（开发）
python -m uvicorn src.services.mt5_api_bridge.app:app --host 0.0.0.0 --port 9090

# 启动（脚本）
scripts\windows\start_mt5_bridge.bat

# 安装为服务
scripts\windows\install_mt5_bridge_service.bat

# 服务管理
nssm start MT5-API-Bridge
nssm stop MT5-API-Bridge
nssm restart MT5-API-Bridge
nssm status MT5-API-Bridge
```

### 健康检查

```bash
# 本地检查
curl http://localhost:9090/health

# 容器检查
docker exec -it mt4-factory-validator curl http://host.docker.internal:9090/health

# 远程检查
curl http://52.10.20.30:9090/health
```

### 防火墙

```powershell
# 开放端口
New-NetFirewallRule -DisplayName "MT5 API Bridge" -Direction Inbound -LocalPort 9090 -Protocol TCP -Action Allow

# 查看规则
Get-NetFirewallRule -DisplayName "MT5 API Bridge"

# 删除规则
Remove-NetFirewallRule -DisplayName "MT5 API Bridge"
```

### 进程检查

```powershell
# 查看MT5进程
tasklist | findstr terminal

# 查看Python进程
tasklist | findstr python

# 查看端口占用
netstat -ano | findstr :9090
```

---

## ⚠️ 常见问题

| 问题 | 原因 | 解决 |
|------|------|------|
| ModuleNotFoundError: MetaTrader5 | 未安装库 | `pip install MetaTrader5` |
| MT5 initialize failed | MT5未运行 | 启动MT5终端并登录 |
| Connection refused | API Bridge未启动 | 运行`start_mt5_bridge.bat` |
| 容器连接不到 | Docker网络问题 | 检查`host.docker.internal` |
| 端口被占用 | 端口冲突 | 更改端口或关闭占用进程 |

---

## 📚 完整文档

| 文档 | 说明 |
|------|------|
| [MT5连接架构](./MT5_CONNECTION_ARCHITECTURE.md) | 完整架构图和技术栈 |
| [MT5 API Bridge启动指南](./MT5_API_BRIDGE_SETUP.md) | 详细启动步骤 |
| [MT5主机配置指南](../config/MT5_HOSTS_GUIDE.md) | 配置文件说明 |
| [Docker部署指南](./DOCKER_DEPLOYMENT.md) | 容器部署 |

---

## 🚀 快速启动

### 30秒启动（Windows本地）

```bash
# 1. 启动MT5（双击桌面图标）
# 2. 启动API Bridge
scripts\windows\start_mt5_bridge.bat
# 3. 启动业务服务
scripts\windows\start_all.bat
```

### 配置验证

```bash
# 检查配置
cat config/windows.yaml | grep -A5 "mt5_hosts:"

# 应该看到:
mt5_hosts:
  demo_1:
    host: "host.docker.internal"    # ✅ Windows本地
    port: 9090                       # ✅ API Bridge端口
```

---

## 📞 技术支持

如有问题，检查：
1. MT5终端是否运行：`tasklist | findstr terminal`
2. API Bridge是否运行：`curl http://localhost:9090/health`
3. 容器日志：`docker-compose logs -f validator`
4. 网络连通性：`docker exec -it mt4-factory-validator ping host.docker.internal`
