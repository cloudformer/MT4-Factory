# MT4-Factory

自动化交易策略工厂 - 策略生成、验证、编排、执行的完整系统。

## 快速启动

### Mac本地开发
```bash
./scripts/mac/start_all.sh
```

### Windows本地/Docker
```bash
scripts\windows\start_all.bat
```

### 详细启动指南
查看 [启动指南文档](./docs/STARTUP_GUIDE.md)

---

## 系统架构

```
┌─────────────────────────────────────────────────────────┐
│                     Dashboard (8001)                    │
│                    Web UI 可视化界面                      │
└─────────────────────────────────────────────────────────┘
                            │
                            ↓
┌─────────────────────────────────────────────────────────┐
│                  Orchestrator (8002)                    │
│         策略注册、编排调度、资金分配、风险管理              │
└─────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        ↓                   ↓                   ↓
┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│  Strategy    │   │   Signal     │   │  Execution   │
│   Service    │   │   Service    │   │   Service    │
│   (8003)     │   │   (8004)     │   │   (8005)     │
│              │   │              │   │              │
│ 策略生成      │   │ 信号生成      │   │ 订单执行      │
└──────────────┘   └──────────────┘   └──────────────┘
                                               │
                                               ↓
                                      ┌──────────────┐
                                      │ MT5 API      │
                                      │ Bridge       │
                                      │ (9090)       │
                                      └──────────────┘
                                               │
                                               ↓
                                      ┌──────────────┐
                                      │ MetaTrader 5 │
                                      │ (Windows)    │
                                      └──────────────┘

        ┌───────────────────┐
        │   Validator       │
        │   (8080)          │
        │                   │
        │ 策略实时验证       │
        └───────────────────┘
                │
                ↓
        ┌───────────────────┐
        │   PostgreSQL      │
        │   (5432)          │
        │                   │
        │   数据存储         │
        └───────────────────┘
```

---

## 核心功能

### 1. **策略工厂（Strategy Service）**
- 自动生成交易策略
- 支持多种策略类型（趋势、均值回归、突破等）
- 参数优化和回测

### 2. **策略验证（Validator Service）**
- 实时验证策略表现
- 支持实时MT5数据 + 历史数据库
- 自动验证（每小时）+ 手动触发
- 并发验证（20-50个策略）
- 历史数据支持Phase 1/2/3递进扩展

### 3. **策略编排（Orchestrator Service）**
- 策略激活管理
- 资金分配
- 风险控制
- 信号评估和优先级排序

### 4. **信号生成（Signal Service）**
- 基于激活策略生成交易信号
- 多维度信号评分
- 信号聚合和去重

### 5. **订单执行（Execution Service）**
- 连接MT5执行订单
- 仓位管理
- 订单跟踪

### 6. **可视化界面（Dashboard）**
- 策略管理
- 实时监控
- 交易记录
- 性能分析

---

## 环境配置

系统支持三种运行环境：

| 环境 | 配置文件 | 数据库 | 用途 |
|------|---------|--------|------|
| Mac本地 | `config/mac.yaml` | SQLite | 开发调试 |
| Windows本地 | `config/windows.yaml` | PostgreSQL (Docker) | 完整测试 |
| 云端生产 | `config/cloud.yaml` | PostgreSQL (Cloud) | 生产部署 |

通过 `DEVICE` 环境变量切换：
```bash
export DEVICE=mac      # Mac本地
export DEVICE=windows  # Windows本地（默认）
export DEVICE=cloud    # 云端生产
```

---

## 快速开始

### 1. 安装依赖

```bash
# 创建虚拟环境
python3 -m venv venv

# 激活虚拟环境
source venv/bin/activate  # Mac/Linux
venv\Scripts\activate     # Windows

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置数据库

**Mac本地（SQLite）**：
```bash
mkdir -p data
export DEVICE=mac
```

**Windows本地（PostgreSQL）**：
```bash
# 启动PostgreSQL容器
docker-compose up -d postgres
```

### 3. 启动服务

**Mac本地**：
```bash
./scripts/start_mac.sh
```

**Windows本地**：
```bash
scripts\start_windows.bat
```

### 4. 访问Dashboard

打开浏览器访问：http://localhost:8001

---

## 目录结构

```
MT4-Factory/
├── config/                  # 配置文件
│   ├── mac.yaml            # Mac本地配置
│   ├── windows.yaml        # Windows本地配置
│   └── cloud.yaml          # 云端生产配置
├── src/
│   ├── common/             # 公共模块
│   │   ├── config/         # 配置管理
│   │   ├── database/       # 数据库连接
│   │   ├── models/         # 数据模型
│   │   └── mt5/           # MT5客户端
│   └── services/           # 微服务
│       ├── dashboard/      # Dashboard服务
│       ├── orchestrator/   # 编排服务
│       ├── strategy/       # 策略服务
│       ├── signal/         # 信号服务
│       ├── execution/      # 执行服务
│       ├── validator/      # 验证服务
│       └── mt5_api_bridge/ # MT5 API桥接
├── scripts/                # 启动脚本
│   ├── start_mac.sh       # Mac启动脚本
│   └── start_windows.bat  # Windows启动脚本
├── docs/                   # 文档
│   ├── STARTUP_GUIDE.md   # 启动指南
│   ├── VALIDATOR_FEATURES_SUMMARY.md
│   └── ...
├── data/                   # 数据目录（SQLite）
├── logs/                   # 日志目录
├── docker-compose.yml      # Docker配置
└── requirements.txt        # Python依赖
```

---

## 主要文档

### 快速开始
- [启动指南](./docs/STARTUP_GUIDE.md) - 详细的启动说明
- [历史数据快速开始](./docs/QUICK_START_HISTORICAL_DATA.md) - 5分钟导入历史数据

### 核心功能
- [Validator功能总结](./docs/VALIDATOR_FEATURES_SUMMARY.md) - 策略验证功能
- [Validator手动触发](./docs/VALIDATOR_MANUAL_TRIGGER.md) - 手动验证功能
- [历史数据完整指南](./docs/HISTORICAL_DATA_GUIDE.md) - Phase 1/2/3导入指南
- [性能与成本分析](./docs/STRATEGY_VALIDATION_PERFORMANCE_COST.md) - 历史数据性能评估

### 技术架构
- [环境配置说明](./docs/ENVIRONMENT_SETUP.md) - Mac/Windows/Cloud环境定位
- [MT5统一客户端](./docs/MT5_UNIFIED_CLIENT_GUIDE.md) - MT5连接架构
- [配置文件说明](./config/README.md) - 配置文件详解
- [Database脚本说明](./scripts/database/README.md) - 数据库管理

---

## 开发指南

### 添加新策略类型
1. 在 `src/services/strategy/generators/` 添加新的策略生成器
2. 在 `StrategyConfig` 注册新策略类型
3. 测试并验证策略性能

### 扩展信号评估
1. 在 `src/services/orchestrator/service/signal_evaluation.py` 添加评估维度
2. 调整权重配置
3. 更新Dashboard显示

### 添加新的交易平台
1. 实现 `MT5Interface` 接口
2. 在 `src/common/mt5/` 添加客户端实现
3. 更新配置文件

---

## 技术栈

- **后端**: Python 3.11+ / FastAPI / SQLAlchemy
- **数据库**: PostgreSQL / SQLite
- **前端**: Alpine.js / Tailwind CSS
- **容器**: Docker / Docker Compose
- **交易平台**: MetaTrader 5
- **并发**: AsyncIO / APScheduler

---

## 许可证

私有项目

---

## 联系方式

项目负责人：Frank Zhang
