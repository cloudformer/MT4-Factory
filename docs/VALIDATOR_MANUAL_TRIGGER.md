# Validator手动触发功能

## 🎯 功能说明

**两种验证方式**：

### **1. 自动验证（保持）**
```
⏰ 每小时自动运行一次
✅ 无需任何操作
✅ 适合生产环境
```

### **2. 手动触发（新增）** ⭐
```
🔘 点击按钮立即验证
✅ 不需要等1小时
✅ 不需要重启容器
✅ 适合测试和调试
```

---

## 🏗️ 架构设计

### **Validator服务增强**

```python
# src/services/validator/concurrent_validator.py

1. 后台服务（AsyncIO）
   └─> 定时调度器（每小时）
   └─> 并发验证策略

2. HTTP API（FastAPI）⭐ 新增
   └─> 端口：8080
   └─> 提供手动触发接口
```

---

## 📡 API接口

### **1. 健康检查**

```bash
GET http://localhost:8080/health

# 响应
{
  "service": "validator",
  "status": "healthy",
  "stats": {
    "total_validations": 10,
    "successful_validations": 9,
    "failed_validations": 1,
    "last_run_time": "2026-04-11T15:30:00",
    "last_run_duration": 10.5
  }
}
```

---

### **2. 手动触发验证（全部Active策略）**

```bash
POST http://localhost:8080/api/validate/trigger

# 响应
{
  "success": true,
  "message": "验证任务已触发（后台执行）",
  "tip": "验证完成后刷新页面查看结果"
}
```

**说明**：
- 异步触发，不阻塞HTTP响应
- 立即返回，验证在后台执行
- 2-10秒后完成（取决于策略数量）

---

### **3. 验证单个策略**

```bash
POST http://localhost:8080/api/validate/strategy/{strategy_id}

# 示例
POST http://localhost:8080/api/validate/strategy/STR_e146a4fd

# 响应
{
  "success": true,
  "message": "策略 STR_e146a4fd 验证任务已触发",
  "strategy_name": "MA_5x28"
}
```

**说明**：
- 仅验证单个策略
- 必须是Active状态
- 速度更快（约2-3秒）

---

### **4. 获取统计信息**

```bash
GET http://localhost:8080/api/stats

# 响应
{
  "total_validations": 10,
  "successful_validations": 9,
  "failed_validations": 1,
  "last_run_time": "2026-04-11T15:30:00",
  "last_run_duration": 10.5
}
```

---

## 🎨 UI显示

### **手动触发按钮位置**

```
策略卡片（Active状态）：

┌───────────────────────────────────────────────┐
│ MA_5x28                              Active   │
│ ✅ 推荐度 66分                                │
├───────────────────────────────────────────────┤
│ 🔄 Validator实时验证   [🔄 立即验证]  15:30 │ ← 按钮
│ ┌───────────────────────────────────────────┐ │
│ │ 胜率: 55% | 收益: +15% | ...             │ │
│ └───────────────────────────────────────────┘ │
│ 💡 基于最近500根K线的真实MT5数据验证         │
└───────────────────────────────────────────────┘
```

**按钮特点**：
- 🟣 紫色背景（与Validator主题一致）
- 📍 位于验证结果区域右上角
- ⏱️ 点击后立即触发，3秒后自动刷新

---

## 🚀 完整使用流程

### **Step 1：启动Validator服务（Windows）**

```bash
# 启动PostgreSQL和Validator
docker-compose up -d postgres validator

# 查看Validator日志
docker-compose logs -f validator

# 预期输出：
🚀 启动Validator服务
🌐 Validator HTTP API已启动: http://0.0.0.0:8080
✅ MT5连接测试成功
🔄 执行首次验证...
```

---

### **Step 2：验证API可用**

```bash
# 健康检查
curl http://localhost:8080/health

# 预期响应：
{
  "service": "validator",
  "status": "healthy"
}
```

---

### **Step 3：在Dashboard UI手动触发**

```
1. 打开Dashboard: http://localhost:8001
2. 找到一个Active策略
3. 在Validator验证区域点击"🔄 立即验证"按钮
4. 看到提示：🔄 正在触发验证...
5. 3秒后自动刷新
6. 看到提示：✅ 验证完成，数据已更新
```

**点击按钮效果**：
```
⏱️ T+0秒：点击按钮
   └─> 提示：🔄 正在触发验证...

⏱️ T+1秒：调用Validator API
   └─> POST http://localhost:8080/api/validate/strategy/STR_xxx

⏱️ T+2秒：Validator后台执行
   └─> 获取MT5数据 → 运行回测 → 更新数据库

⏱️ T+3秒：自动刷新Dashboard
   └─> 提示：✅ 验证完成，数据已更新
   └─> 验证结果自动更新显示
```

---

### **Step 4：查看验证结果**

```
验证区域自动更新：

🔄 Validator实时验证   2026-04-11 15:35  ← 时间更新
胜率: 56.0%  ← 数据更新
收益: +16.5% ← 数据更新
交易数: 27   ← 数据更新
```

---

## 🔧 命令行测试（可选）

### **测试单个策略验证**

```bash
# 方式1：使用curl
curl -X POST http://localhost:8080/api/validate/strategy/STR_e146a4fd

# 方式2：使用Python
python -c "
import requests
response = requests.post('http://localhost:8080/api/validate/strategy/STR_e146a4fd')
print(response.json())
"

# 预期响应：
{
  "success": true,
  "message": "策略 STR_e146a4fd 验证任务已触发",
  "strategy_name": "MA_5x28"
}

# 查看数据库验证结果（3秒后）
docker exec -it mt4-factory-postgres psql -U evo_trade_user -d evo_trade -c "
SELECT 
  id, 
  name,
  last_validation_time,
  validation_win_rate,
  validation_total_return
FROM strategies 
WHERE id = 'STR_e146a4fd';
"
```

---

### **测试全部策略验证**

```bash
# 触发验证
curl -X POST http://localhost:8080/api/validate/trigger

# 查看Validator日志
docker-compose logs -f validator

# 预期日志：
🔘 收到手动触发验证请求
🔍 开始批量验证
📊 找到 5 个Active策略，开始并发验证...
✅ [STR_xxx1] 验证完成
✅ [STR_xxx2] 验证完成
✅ [STR_xxx3] 验证完成
✅ 批量验证完成
   总计: 5 | 成功: 5 | 失败: 0
   耗时: 8.50秒
```

---

## 🎯 使用场景

### **场景1：刚激活新策略**
```
1. 在Dashboard点击"✅ 激活策略"
2. 策略状态变为Active
3. 立即点击"🔄 立即验证"
4. 3秒后看到验证结果

✅ 不需要等1小时
✅ 立即获得真实数据验证
```

---

### **场景2：测试Validator功能**
```
1. 修改Validator代码
2. 重启Validator容器
3. 点击"🔄 立即验证"测试
4. 查看日志和结果

✅ 快速迭代测试
✅ 无需等待自动调度
```

---

### **场景3：市场波动后验证**
```
1. 重大经济数据公布
2. 市场波动剧烈
3. 立即验证策略表现
4. 观察指标变化

✅ 及时掌握策略状态
✅ 快速决策是否停用
```

---

## 📊 对比总结

| 维度 | 自动验证 | 手动触发 |
|------|---------|---------|
| **触发方式** | 定时调度（每小时） | 点击按钮 ⭐ |
| **等待时间** | 最多1小时 | 立即（3秒）⭐ |
| **适用场景** | 生产环境 | 测试/调试 ⭐ |
| **操作复杂度** | 无需操作 | 一键触发 ⭐ |
| **验证范围** | 所有Active策略 | 单个或全部 ⭐ |

---

## ⚠️ 注意事项

### **1. Validator服务必须启动**
```bash
# 检查Validator是否运行
docker-compose ps validator

# 如果未运行，启动它
docker-compose up -d validator
```

### **2. MT5 API Bridge必须可用**
```bash
# 检查MT5 API Bridge
curl http://localhost:9090/health

# 如果失败，启动它
scripts\start_mt5_api_bridge.bat
```

### **3. 策略必须是Active状态**
```
❌ Candidate策略：按钮不显示
✅ Active策略：按钮显示，可点击
```

### **4. 频率限制（建议）**
```
建议间隔：至少10秒
原因：避免频繁触发，浪费资源

系统会自动去重：
- 如果正在验证，不会重复触发
- 可以安全多次点击
```

---

## 🐛 故障排查

### **问题1：点击按钮无反应**

```bash
# 检查：Validator服务是否运行
docker-compose ps validator

# 检查：API端口是否开放
curl http://localhost:8080/health

# 解决：重启Validator
docker-compose restart validator
```

---

### **问题2：提示"无法连接Validator服务"**

```bash
# 原因：Validator API未启动

# 解决方法1：检查容器日志
docker-compose logs validator

# 解决方法2：检查端口映射
docker-compose ps

# 应该看到：0.0.0.0:8080->8080/tcp

# 解决方法3：重新构建容器
docker-compose up -d --build validator
```

---

### **问题3：验证结果未更新**

```bash
# 原因1：验证失败

# 查看Validator日志
docker-compose logs -f validator

# 查找错误信息
❌ [STR_xxx] 验证失败: ...

# 原因2：MT5连接失败

# 测试MT5 API Bridge
curl "http://localhost:9090/bars/EURUSD?timeframe=H1&count=10"

# 原因3：数据库连接失败

# 测试PostgreSQL
docker exec -it mt4-factory-postgres psql -U evo_trade_user -d evo_trade -c "SELECT 1;"
```

---

## ✅ 总结

### **核心优势**

```
✅ 自动 + 手动双模式
   - 自动：每小时验证（生产环境）
   - 手动：立即验证（测试调试）

✅ 一键触发
   - UI按钮：用户友好
   - HTTP API：脚本自动化

✅ 异步执行
   - 不阻塞UI
   - 后台自动完成
   - 自动刷新结果

✅ 灵活验证
   - 单个策略：快速（2-3秒）
   - 全部策略：批量（5-15秒）
```

### **典型工作流**

```
1. 激活策略（Dashboard UI）
2. 点击"🔄 立即验证"（不等1小时）
3. 等待3秒（自动刷新）
4. 查看验证结果（紫色区域）
5. 根据结果决策（继续/停用/归档）
```

**现在有了手动触发功能，测试和调试更方便了！** 🚀
