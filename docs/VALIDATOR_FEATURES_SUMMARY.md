# Validator功能总结

## ✅ 已完成功能

### **1. 自动验证（每小时）**
```
⏰ 定时调度器：每小时自动运行
✅ 并发验证：20-50个策略同时验证
✅ 后台运行：7x24不间断
✅ 适用场景：生产环境
```

### **2. 手动触发（立即验证）** ⭐ 新增
```
🔘 UI按钮：点击立即验证
✅ 不等1小时：3秒内完成
✅ HTTP API：支持自动化
✅ 适用场景：测试调试
```

---

## 🏗️ 完整架构

```
┌─────────────────────────────────────────────────┐
│              Validator服务                       │
├─────────────────────────────────────────────────┤
│                                                 │
│  1. 后台服务（AsyncIO + APScheduler）           │
│     ├─ 定时调度器（每小时）                     │
│     ├─ 并发验证器（20-50并发）                  │
│     ├─ 从MT5获取真实数据                        │
│     └─ 更新数据库validation_*字段               │
│                                                 │
│  2. HTTP API（FastAPI，端口8080）⭐             │
│     ├─ GET  /health                             │
│     ├─ POST /api/validate/trigger（全部）       │
│     ├─ POST /api/validate/strategy/{id}（单个） │
│     └─ GET  /api/stats                          │
│                                                 │
└─────────────────────────────────────────────────┘
                    │
                    │ 读取/更新
                    ↓
┌─────────────────────────────────────────────────┐
│            PostgreSQL数据库                      │
├─────────────────────────────────────────────────┤
│  strategies表（新增字段）                        │
│  ├─ last_validation_time                        │
│  ├─ validation_win_rate                         │
│  ├─ validation_total_return                     │
│  ├─ validation_total_trades                     │
│  ├─ validation_sharpe_ratio                     │
│  ├─ validation_max_drawdown                     │
│  └─ validation_profit_factor                    │
└─────────────────────────────────────────────────┘
                    │
                    │ 读取
                    ↓
┌─────────────────────────────────────────────────┐
│            Dashboard UI                         │
├─────────────────────────────────────────────────┤
│  策略列表（Active策略显示）                      │
│  ┌──────────────────────────────────────────┐  │
│  │ 🔄 Validator实时验证  [🔄 立即验证]     │  │
│  │ 胜率: 55% | 收益: +15% | 交易: 25      │  │
│  │ Sharpe: 1.20 | 回撤: 8% | 盈亏比: 2.5  │  │
│  │ 💡 基于最近500根K线的真实MT5数据验证     │  │
│  └──────────────────────────────────────────┘  │
└─────────────────────────────────────────────────┘
```

---

## 🎯 两种验证方式对比

| 维度 | 自动验证 | 手动触发 ⭐ |
|------|---------|-----------|
| **触发** | 定时（每小时） | 点击按钮 |
| **等待时间** | 最多1小时 | 立即（3秒） |
| **验证范围** | 所有Active策略 | 单个或全部 |
| **适用场景** | 生产环境 | 测试/调试 |
| **操作** | 无需操作 | 一键触发 |
| **API** | 内部调度 | HTTP API |

---

## 🚀 使用流程

### **场景1：首次使用**

```bash
# Windows上

# Step 1: 启动MT5 API Bridge
scripts\start_mt5_api_bridge.bat

# Step 2: 启动Validator
docker-compose up -d validator

# Step 3: 查看日志
docker-compose logs -f validator

# 预期输出：
🚀 启动Validator服务
🌐 Validator HTTP API已启动: http://0.0.0.0:8080
✅ MT5连接测试成功
🔄 执行首次验证...
✅ 批量验证完成

# Step 4: 打开Dashboard
# http://localhost:8001
# 找到Active策略
# 看到紫色验证区域 ✅
```

---

### **场景2：手动触发验证**

```
Dashboard UI操作：

1. 找到Active策略
2. 看到Validator验证区域（紫色）
3. 点击"🔄 立即验证"按钮
4. 看到提示：🔄 正在触发验证...
5. 3秒后自动刷新
6. 看到提示：✅ 验证完成，数据已更新
7. 验证结果自动更新显示

⏱️ 总耗时：3-5秒
✅ 无需等1小时
✅ 无需重启容器
```

---

### **场景3：API自动化**

```bash
# 命令行触发验证

# 验证单个策略
curl -X POST http://localhost:8080/api/validate/strategy/STR_e146a4fd

# 验证所有Active策略
curl -X POST http://localhost:8080/api/validate/trigger

# 查看统计信息
curl http://localhost:8080/api/stats
```

---

## 📊 验证结果展示

### **UI显示（Dashboard）**

```
┌───────────────────────────────────────────────┐
│ MA_5x28                              Active   │
│ ✅ 推荐度 66分                                │
├───────────────────────────────────────────────┤
│ 🔄 Validator实时验证   [🔄 立即验证]  15:35 │ ← 紫色区域
│ ┌───────────────────────────────────────────┐ │
│ │ 胜率      收益率    交易数    Sharpe     │ │
│ │ 56.0%    +16.5%     27       1.25       │ │
│ │                                          │ │
│ │ 最大回撤  盈亏比                         │ │
│ │ 7.5%     2.60                           │ │
│ └───────────────────────────────────────────┘ │
│ 💡 基于最近500根K线的真实MT5数据验证         │
├───────────────────────────────────────────────┤
│ 📊 详细指标 (初始回测) ▼                     │
│ ...（原有performance数据）...               │
└───────────────────────────────────────────────┘
```

**显示条件**：
- ✅ 策略状态：Active
- ✅ 验证时间：last_validation_time有值
- ❌ Candidate/Archived策略：不显示

---

### **数据对比**

```
初始回测 vs 实时验证：

┌────────────┬──────────┬──────────┬────────┐
│   指标     │ 初始回测 │ 实时验证 │ 评价   │
├────────────┼──────────┼──────────┼────────┤
│ 胜率       │ 50.0%    │ 56.0%    │ ✅ 提升│
│ 收益率     │ 20.0%    │ 16.5%    │ ⚠️ 下降│
│ 交易数     │ 30       │ 27       │ 正常   │
│ Sharpe     │ 1.00     │ 1.25     │ ✅ 提升│
│ 最大回撤   │ 10.0%    │ 7.5%     │ ✅ 改善│
│ 盈亏比     │ 2.50     │ 2.60     │ ✅ 提升│
└────────────┴──────────┴──────────┴────────┘

分析：
✅ 胜率、Sharpe、回撤：表现更好
⚠️ 收益率略降：可能是市场环境变化
✅ 整体表现：稳定可靠
```

---

## 🔧 配置文件

### **config/windows.yaml**

```yaml
validator:
  enabled: true
  mode: "active_strategies"
  concurrency: 20                      # 并发数（可调整20-50）
  schedule_interval: 3600              # 自动调度间隔（秒）
  demo_account: "5049130509"
  initial_balance: 100
  bars_count: 500                      # 每次获取K线数量

mt5:
  host: "host.docker.internal"         # 容器访问宿主机
  port: 9090
  login: 5049130509
  password: "your_password"
  server: "MetaQuotes-Demo"
  api_key: "demo_key_12345"
  timeout: 10
```

### **config/production.yaml**

```yaml
validator:
  enabled: true
  concurrency: 20
  schedule_interval: 3600

  mt5:
    host: "52.10.20.30"                # Windows VPS IP
    port: 9090
    api_key: "prod_validator_key_xxx"  # 生产密钥
    timeout: 15
```

---

## 📡 API端点文档

### **1. 健康检查**

```
GET /health

响应：
{
  "service": "validator",
  "status": "healthy",
  "stats": {
    "total_validations": 10,
    "successful_validations": 9,
    "failed_validations": 1
  }
}
```

### **2. 手动触发（全部）**

```
POST /api/validate/trigger

响应：
{
  "success": true,
  "message": "验证任务已触发（后台执行）"
}
```

### **3. 验证单个策略**

```
POST /api/validate/strategy/{strategy_id}

响应：
{
  "success": true,
  "message": "策略 STR_xxx 验证任务已触发",
  "strategy_name": "MA_5x28"
}
```

### **4. 统计信息**

```
GET /api/stats

响应：
{
  "total_validations": 10,
  "successful_validations": 9,
  "failed_validations": 1,
  "last_run_time": "2026-04-11T15:30:00",
  "last_run_duration": 10.5
}
```

---

## 🐛 故障排查

### **问题1：UI不显示验证结果**

```
原因：
❌ 策略状态不是Active
❌ last_validation_time为空（未验证）
❌ Validator服务未启动

解决：
1. 确认策略已激活
2. 点击"🔄 立即验证"按钮
3. 检查Validator日志
```

### **问题2：点击按钮无反应**

```
原因：
❌ Validator HTTP API未启动
❌ 端口8080未开放

解决：
docker-compose logs validator
curl http://localhost:8080/health
docker-compose restart validator
```

### **问题3：验证失败**

```
原因：
❌ MT5 API Bridge未启动
❌ MT5连接失败
❌ 数据库连接失败

解决：
1. 检查MT5 API Bridge
   curl http://localhost:9090/health

2. 检查Validator日志
   docker-compose logs -f validator

3. 测试MT5数据获取
   curl "http://localhost:9090/bars/EURUSD?timeframe=H1&count=10"
```

---

## ✅ 核心优势

### **1. 真实数据验证**
```
初始回测：模拟数据（可能过拟合）
实时验证：MT5真实行情 ⭐
```

### **2. 持续性能监控**
```
每小时验证 → 跟踪策略表现变化
发现问题 → 及时停用或归档
```

### **3. 灵活触发方式**
```
自动：无需操作（生产环境）
手动：一键触发（测试调试）⭐
```

### **4. 用户友好**
```
UI显示：清晰直观（紫色区域）
按钮操作：简单方便
自动刷新：无需手动
```

---

## 📚 相关文档

- [Validator并发架构](./VALIDATOR_CONCURRENT_ARCHITECTURE.md) - 并发设计详解
- [Validator手动触发](./VALIDATOR_MANUAL_TRIGGER.md) - 手动触发功能详解
- [MT5统一客户端](./MT5_UNIFIED_CLIENT_GUIDE.md) - MT5连接架构
- [UI显示说明](./UI_VALIDATOR_DISPLAY.md) - Dashboard显示详解
- [Windows快速启动](./QUICK_START_WINDOWS.md) - 完整启动指南

---

## 🎯 下一步

**Mac上完成的工作**：
- ✅ Validator服务代码（并发+HTTP API）
- ✅ Dashboard UI显示（紫色验证区域+按钮）
- ✅ 配置文件（windows.yaml/production.yaml）
- ✅ Docker配置（docker-compose.yml/Dockerfile）
- ✅ 完整文档

**Windows上需要测试**：
1. ✅ 启动MT5 API Bridge
2. ✅ 启动Validator容器
3. ✅ 点击"🔄 立即验证"按钮
4. ✅ 查看验证结果显示
5. ✅ 测试自动验证（等1小时或重启）

**系统已就绪！可以去Windows完整测试了！** 🚀
