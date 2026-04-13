# Scripts 目录说明

脚本文件按照运行环境分类管理。

## 目录结构

```
scripts/
├── mac/                # Mac本地开发脚本
├── windows/            # Windows本地/Docker脚本
├── cloud/              # 云端生产环境脚本
├── database/           # 数据库相关脚本
└── tools/              # 工具脚本
```

---

## Mac本地开发脚本 (`mac/`)

**环境**: Mac + SQLite + 无Docker

### 启动脚本

| 脚本 | 用途 | 命令 |
|------|------|------|
| `start_mac.sh` | 启动Dashboard | `./scripts/mac/start_mac.sh` |
| `start_orchestrator.sh` | 启动Orchestrator | `./scripts/mac/start_orchestrator.sh` |
| `start_all.sh` | 启动所有服务（后台） | `./scripts/mac/start_all.sh` |
| `stop_all.sh` | 停止所有服务 | `./scripts/mac/stop_all.sh` |

### 使用示例

```bash
# 启动所有服务
./scripts/mac/start_all.sh

# 停止所有服务
./scripts/mac/stop_all.sh

# 单独启动Dashboard
./scripts/mac/start_mac.sh
```

---

## Windows本地脚本 (`windows/`)

**环境**: Windows + PostgreSQL (Docker) + MT5

### 启动脚本

| 脚本 | 用途 | 命令 |
|------|------|------|
| `start_windows.bat` | 启动Dashboard | `scripts\windows\start_windows.bat` |
| `start_orchestrator.bat` | 启动Orchestrator | `scripts\windows\start_orchestrator.bat` |
| `start_mt5_api_bridge.bat` | 启动MT5 API Bridge | `scripts\windows\start_mt5_api_bridge.bat` |
| `start_all.bat` | 启动所有服务 | `scripts\windows\start_all.bat` |
| `stop_all.bat` | 停止所有服务 | `scripts\windows\stop_all.bat` |

### 使用示例

```bat
REM 启动所有服务（包括Docker）
scripts\windows\start_all.bat

REM 启动MT5 API Bridge（需要先打开MT5）
scripts\windows\start_mt5_api_bridge.bat

REM 停止所有服务
scripts\windows\stop_all.bat
```

### 完整启动流程（Windows）

1. **启动MT5**
   - 打开MetaTrader 5
   - 登录账户

2. **启动MT5 API Bridge**
   ```bat
   scripts\windows\start_mt5_api_bridge.bat
   ```

3. **启动其他服务**
   ```bat
   scripts\windows\start_all.bat
   ```

4. **访问Dashboard**
   - http://localhost:8001

---

## 云端生产脚本 (`cloud/`)

**环境**: Linux + PostgreSQL (Cloud) + 远程MT5

目前为空，生产环境使用Docker Compose或systemd服务管理。

---

## 数据库脚本 (`database/`)

**按数据库类型分类**：
- `postgres/` - PostgreSQL脚本（Docker + RDS）
- `sqlite/` - SQLite脚本（Mac本地）
- `migrate_sqlite_to_postgres.py` - 迁移工具

详细说明请查看：[database/README.md](database/README.md)

### 快速使用

**PostgreSQL初始化（Windows Docker）**：
```bash
docker exec -i mt4-factory-postgres psql -U evo_trade_user -d evo_trade < scripts/database/postgres/init_db.sql
docker exec -i mt4-factory-postgres psql -U evo_trade_user -d evo_trade < scripts/database/postgres/add_validator_fields.sql
```

**SQLite添加字段（Mac）**：
```bash
sqlite3 data/evo_trade.db < scripts/database/sqlite/add_validator_fields.sql
```

**数据迁移**：
```bash
python scripts/database/migrate_sqlite_to_postgres.py
```

---

## 工具脚本 (`tools/`)

### 测试和管理工具

| 脚本 | 用途 |
|------|------|
| `test_mt5_connection.py` | 测试MT5连接 |
| `generate_fake_trades.py` | 生成测试交易数据 |
| `init_accounts_db.py` | 初始化账户数据 |
| `manage_registration.py` | 策略注册管理CLI |

### 使用示例

```bash
# 测试MT5连接
python scripts/tools/test_mt5_connection.py

# 生成测试数据
python scripts/tools/generate_fake_trades.py

# 管理策略注册
python scripts/tools/manage_registration.py
```

---

## 常见问题

### Mac: 脚本无法执行

```bash
# 添加执行权限
chmod +x scripts/mac/*.sh
```

### Windows: 找不到命令

```bat
REM 确保从项目根目录运行
cd MT4-Factory
scripts\windows\start_all.bat
```

### 端口被占用

```bash
# Mac查看端口占用
lsof -i :8001

# Windows查看端口占用
netstat -ano | findstr :8001
```

---

## 快速参考

| 需求 | Mac命令 | Windows命令 |
|------|---------|------------|
| 启动Dashboard | `./scripts/mac/start_mac.sh` | `scripts\windows\start_windows.bat` |
| 启动所有服务 | `./scripts/mac/start_all.sh` | `scripts\windows\start_all.bat` |
| 停止所有服务 | `./scripts/mac/stop_all.sh` | `scripts\windows\stop_all.bat` |
| 测试MT5连接 | `python scripts/tools/test_mt5_connection.py` | `python scripts\tools\test_mt5_connection.py` |
