# MT5连接完整索引

## 📖 文档导航

### 🚀 快速开始
| 文档 | 说明 | 适用对象 |
|------|------|---------|
| [MT5快速参考](./MT5_QUICK_REFERENCE.md) | 30秒快速参考卡 | 所有人 ⭐ |
| [MT5 API Bridge启动指南](./MT5_API_BRIDGE_SETUP.md) | 详细启动步骤 | 新手 |

### 🏗️ 架构和原理
| 文档 | 说明 | 适用对象 |
|------|------|---------|
| [MT5连接架构](./MT5_CONNECTION_ARCHITECTURE.md) | 完整技术架构和依赖 | 开发者 |
| [MT5主机配置指南](../config/MT5_HOSTS_GUIDE.md) | 配置文件说明 | 运维人员 |

### 🐳 部署相关
| 文档 | 说明 | 适用对象 |
|------|------|---------|
| [Docker部署指南](./DOCKER_DEPLOYMENT.md) | 容器化部署 | DevOps |
| [环境配置指南](./ENVIRONMENT_SETUP.md) | 三环境说明 | 所有人 |

---

## 🛠️ 脚本工具

### Windows MT5脚本集合
位置：`scripts/windows_mt5_script/`

| 脚本 | 用途 | 使用场景 |
|------|------|---------|
| [start_mt5_bridge.bat](../scripts/windows_mt5_script/start_mt5_bridge.bat) | 启动MT5 API Bridge | 开发测试 |
| [install_mt5_bridge_service.bat](../scripts/windows_mt5_script/install_mt5_bridge_service.bat) | 安装为Windows服务 | 生产环境 |
| [check_mt5_status.bat](../scripts/windows_mt5_script/check_mt5_status.bat) | 检查运行状态 | 故障排查 |
| [restart_mt5_bridge.bat](../scripts/windows_mt5_script/restart_mt5_bridge.bat) | 重启服务 | 维护管理 |

📋 [查看脚本完整说明](../scripts/windows_mt5_script/README.md)

---

## 🎯 按场景查找

### 场景1：首次配置Windows本地开发
```
1. 阅读: MT5快速参考 (5分钟)
2. 阅读: MT5 API Bridge启动指南 (10分钟)
3. 运行: scripts/windows_mt5_script/start_mt5_bridge.bat
4. 运行: scripts/windows/start_all.bat
```

### 场景2：部署到Cloud生产环境
```
1. 阅读: MT5连接架构 (了解完整架构)
2. 阅读: MT5 API Bridge启动指南 > 生产环境部分
3. VPS上运行: scripts/windows_mt5_script/install_mt5_bridge_service.bat
4. Linux服务器运行: scripts/cloud/start_all.sh
```

### 场景3：连接问题排查
```
1. 运行: scripts/windows_mt5_script/check_mt5_status.bat
2. 查看: MT5快速参考 > 常见问题
3. 查看: MT5连接架构 > 故障排查
4. 查看日志: logs/mt5_bridge_stdout.log
```

### 场景4：配置多个MT5主机
```
1. 阅读: MT5主机配置指南
2. 编辑: config/windows.yaml 或 config/cloud.yaml
3. 添加新的mt5_hosts配置
4. 重启服务
```

---

## ⚙️ 核心依赖清单

### ✅ 必需（Windows系统）
1. **Windows 10/11 或 Server 2019/2022**
2. **MT5终端** (MetaTrader5.exe)
   - 下载：https://www.metatrader5.com/en/download
3. **Python 3.11+ (64位)**
   - 下载：https://www.python.org/downloads/
4. **MetaTrader5 Python库**
   ```bash
   pip install MetaTrader5
   ```
5. **MT5 API Bridge**
   - 位置：src/services/mt5_api_bridge/app.py

### ⭐ 可选
6. **Docker Desktop**（Windows本地开发）
7. **mstsc**（远程桌面，Cloud VPS管理）
8. **NSSM**（服务管理器，生产环境）
   - 下载：https://nssm.cc/download

---

## 🔗 连接流程图

```
┌──────────────────────────────────────────────────────┐
│ Windows本地开发                                       │
├──────────────────────────────────────────────────────┤
│                                                      │
│  1. MT5终端 (terminal64.exe)                         │
│     ↓ COM接口                                         │
│  2. MT5 API Bridge (Python HTTP服务)                │
│     监听: localhost:9090                             │
│     ↑ HTTP                                           │
│  3. Docker容器 (Validator/Execution)                │
│     通过: host.docker.internal:9090                  │
│                                                      │
└──────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────┐
│ Cloud生产环境                                         │
├──────────────────────────────────────────────────────┤
│                                                      │
│  Windows VPS (52.10.20.30)                          │
│  ├─ MT5终端 (terminal64.exe)                        │
│  │   ↓ COM接口                                       │
│  └─ MT5 API Bridge                                  │
│      监听: 0.0.0.0:9090                             │
│      ↑ HTTP (公网)                                   │
│                                                      │
│  Linux服务器 (52.10.20.10)                          │
│  └─ Docker容器 (Validator/Execution)                │
│      访问: 52.10.20.30:9090                         │
│                                                      │
└──────────────────────────────────────────────────────┘
```

---

## 🆘 快速问题解决

| 问题 | 文档位置 |
|------|---------|
| 如何启动MT5 API Bridge？ | [MT5 API Bridge启动指南](./MT5_API_BRIDGE_SETUP.md) |
| 容器连接不到MT5？ | [MT5连接架构 > 故障排查](./MT5_CONNECTION_ARCHITECTURE.md) |
| 如何配置多个MT5主机？ | [MT5主机配置指南](../config/MT5_HOSTS_GUIDE.md) |
| ModuleNotFoundError: MetaTrader5 | [MT5快速参考 > 常见问题](./MT5_QUICK_REFERENCE.md) |
| 如何安装为Windows服务？ | [MT5 API Bridge启动指南 > 方式3](./MT5_API_BRIDGE_SETUP.md) |
| Docker容器如何访问宿主机MT5？ | [MT5连接架构 > 场景1](./MT5_CONNECTION_ARCHITECTURE.md) |

---

## 📞 技术支持流程

遇到问题？按顺序操作：

### 步骤1：运行状态检查
```bash
scripts\windows_mt5_script\check_mt5_status.bat
```

### 步骤2：查看快速参考
```
docs/MT5_QUICK_REFERENCE.md
```

### 步骤3：查看详细日志
```bash
# 如果是Windows服务
type C:\MT4-Factory\logs\mt5_bridge_stdout.log

# 如果是命令行启动
查看控制台输出
```

### 步骤4：验证网络连通性
```bash
# 本地测试
curl http://localhost:9090/health

# 容器测试
docker exec -it mt4-factory-validator curl http://host.docker.internal:9090/health
```

### 步骤5：查找对应文档
根据错误信息，查找本索引中的相关文档。

---

## 🔄 更新记录

- 2024-04-11：创建MT5连接完整文档体系
- 2024-04-11：新增Windows MT5脚本集合
- 2024-04-11：优化配置文件结构

---

## 📚 相关项目文档

| 文档 | 说明 |
|------|------|
| [配置文件说明](../config/README.md) | 三环境配置总览 |
| [Docker部署指南](./DOCKER_DEPLOYMENT.md) | 容器化部署 |
| [历史数据指南](./HISTORICAL_DATA_GUIDE.md) | Phase 1/2/3数据导入 |
| [启动指南](./STARTUP_GUIDE.md) | 项目快速启动 |
