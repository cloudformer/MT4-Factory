# Mac环境启动指南

## 快速启动

### 1. 一键启动所有服务（推荐）

```bash
cd /Users/frankzhang/repo-private/MT4-Factory
./scripts/mac/start_all_services.sh
```

启动后访问：
- **Dashboard**: http://localhost:8001

---

### 2. 停止所有服务

```bash
./scripts/mac/stop_all_services.sh
```

---

## 服务列表

启动后的服务：

| 服务 | 端口 | URL | 说明 |
|------|------|-----|------|
| Dashboard | 8001 | http://localhost:8001 | Web UI界面 |
| Strategy | 8000 | http://localhost:8000 | 策略生成API |
| Orchestrator | 8002 | http://localhost:8002 | 策略协调API |
| Execution | 8003 | http://localhost:8003 | 交易执行API |
| Validator | 8004 | http://localhost:8004 | 策略验证API |

---

## Mock数据说明

Mac环境使用**完全Mock数据**，用于UI开发和测试：

### MT5 Workers（假数据）

**Demo Workers（Validator使用）：**
- `demo_worker_1` - 192.168.1.101:9090 ✅ 已连接
  - 账户: 5049130509@MetaQuotes-Demo
  - 余额: $100,000.00
  - 持仓: 3个

- `demo_worker_2` - 192.168.1.102:9090 ⚪ 未启用

**Real Workers（Execution使用）：**
- `real_worker_icm_1` - 52.10.20.101:9090 ✅ 已连接
  - 账户: 8012345678@ICMarkets-Live
  - 余额: $10,000.00
  - 持仓: 5个

- `real_worker_icm_2` - 52.10.20.102:9090 ❌ 连接失败
  - 错误: Connection timeout

- `real_worker_pep_1` - 52.10.20.103:9090 ⚪ 未启用

### Validator数据源（假数据）

**✅ 模拟数据 (Synthetic)**
- 状态: Ready
- 权重: 20%
- 已生成: 1000条
- 更新时间: 2024-04-11 10:30:00

**⏳ 历史数据 (Historical)**
- 状态: Loading
- 权重: 60%
- 进度: 65% (33,800,000 / 52,000,000 bars)
- 品种: 28个货币对
- 时间范围: 2022-01-01 ~ 2024-04-11

**✅ 实时数据 (Realtime)**
- 状态: Connected
- 权重: 20%
- MT5主机: demo_worker_1
- 最后Tick: 2024-04-11 10:35:42
- 可用品种: EURUSD, GBPUSD, USDJPY, AUDUSD

### Execution状态（假数据）

- 总持仓: 8个
- 今日订单: 15个
- 今日盈亏: $234.56

### Orchestrator状态（假数据）

- Active策略: 12个
- 今日信号: 28个
- 待处理信号: 5个

### Strategy生成（假数据）

- 总生成策略: 156个
- 今日生成: 8个
- 成功率: 87%

---

## UI展示内容

### Dashboard首页

可以看到：
- ✅ 所有服务状态（绿色/红色）
- ✅ MT5 Workers连接状态
- ✅ 模拟策略列表
- ✅ 模拟信号列表
- ✅ 模拟交易列表

### Execution页面

可以看到：
- ✅ Real Workers列表和状态
- ✅ 每个Worker的账户信息
- ✅ 持仓列表
- ✅ 测试连接按钮
- ✅ 配置按钮

### Validator页面

可以看到：
- ✅ 三个数据源状态（Synthetic/Historical/Realtime）
- ✅ 历史数据加载进度条
- ✅ Demo Workers列表和状态
- ✅ 切换Worker按钮
- ✅ 测试连接按钮

### Orchestrator页面

可以看到：
- ✅ Active策略列表
- ✅ 今日信号统计
- ✅ MT5机器连接状态
- ✅ 风险控制状态

---

## 查看日志

### 实时查看某个服务日志

```bash
# Dashboard日志
tail -f logs/dashboard.log

# Execution日志
tail -f logs/execution.log

# Validator日志
tail -f logs/validator.log
```

### 查看所有服务日志

```bash
tail -f logs/*.log
```

---

## 手动启动单个服务

如果只想启动某个服务：

```bash
# Dashboard
python3 -m src.services.dashboard.api.app

# Strategy
python3 -m src.services.strategy.main

# Orchestrator
python3 -m src.services.orchestrator.main

# Execution
python3 -m src.services.execution.main

# Validator
python3 -m src.services.validator.main
```

---

## 配置文件

Mac环境配置文件：`config/mac.yaml`

关键配置：
```yaml
env: mac

services:
  use_containers: false  # Mac不使用Docker容器
  dashboard:
    enabled: true
    port: 5000

dev_tools:
  enabled: true
  mock_mt5: true  # ← 关键：启用Mock模式
```

---

## 常见问题

### Q1: 端口被占用

```bash
# 查看端口占用
lsof -i :5000
lsof -i :8001

# 杀死进程
kill -9 <PID>
```

### Q2: 服务启动失败

检查日志文件：
```bash
cat logs/dashboard.log
cat logs/execution.log
```

### Q3: 想看真实MT5连接

在Mac上无法连接真实MT5，需要在Windows环境下运行：
```bash
# Windows环境
docker-compose --profile dev up -d
scripts\windows_mt5_script\start_mt5_bridge.bat
```

---

## 开发建议

1. **UI开发**: 使用Mac环境，Mock数据足够
2. **功能测试**: 切换到Windows环境，连接真实MT5
3. **生产部署**: 使用Cloud环境配置

---

## 总结

Mac环境特点：
- ✅ 所有服务都可以启动
- ✅ 使用Mock数据，UI完整展示
- ✅ 轻量级SQLite数据库
- ✅ 适合UI开发和演示
- ❌ 无法连接真实MT5（需要Windows）
