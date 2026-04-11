# 平台检测与MT5自动同步

## 功能说明

系统会自动检测运行平台，并根据平台类型采取不同的行为：

### 🪟 Windows系统
- ✅ 自动连接真实MT5终端
- ✅ 自动同步账户余额和净值
- ✅ 显示同步成功提示和同步时间
- ✅ 实时显示MT5账户数据

### 🍎 macOS/Linux系统
- ℹ️ 使用Mock模式（模拟数据）
- ℹ️ 显示配置文件中的静态数据
- ⚠️ 明确提示"无法查看实时数据"
- ℹ️ 提示需要Windows系统才能查看真实数据

---

## Dashboard界面提示

### Windows - 同步成功
```
┌─────────────────────────────────────────────────────┐
│ ✅  MT5连接成功                                       │
│                                                      │
│ ✅ MT5连接成功，数据已同步                            │
│                                                      │
│ 余额: 10000.0 | 净值: 10000.0                        │
│ 同步时间: 2026-04-11 06:36:12                        │
└─────────────────────────────────────────────────────┘
```

### Windows - 同步失败
```
┌─────────────────────────────────────────────────────┐
│ ⚠️  MT5连接失败                                      │
│                                                      │
│ ⚠️ MT5连接失败，显示数据库缓存数据                    │
│                                                      │
│ 显示数据库缓存数据，请检查MT5是否运行                  │
└─────────────────────────────────────────────────────┘
```

### macOS/Linux - Mock模式
```
┌─────────────────────────────────────────────────────┐
│ ℹ️  Mock模式（开发环境）                             │
│                                                      │
│ 当前运行在 Darwin 系统，显示模拟数据                  │
│                                                      │
│ ⚠️ 无法查看实时MT5数据 - 真实数据需要在Windows系统上运行 │
└─────────────────────────────────────────────────────┘
```

---

## API返回格式

### GET /accounts-db

**Response (macOS):**
```json
{
  "code": 0,
  "message": "获取成功",
  "platform": {
    "system": "Darwin",
    "is_windows": false,
    "is_mock": true,
    "mt5_mode": "Mock",
    "sync_status": null
  },
  "data": [...]
}
```

**Response (Windows - 同步成功):**
```json
{
  "code": 0,
  "message": "获取成功",
  "platform": {
    "system": "Windows",
    "is_windows": true,
    "is_mock": false,
    "mt5_mode": "Real",
    "sync_status": {
      "success": true,
      "message": "✅ MT5连接成功，数据已同步",
      "balance": 10500.25,
      "equity": 10450.80
    }
  },
  "data": [...]
}
```

**Response (Windows - 同步失败):**
```json
{
  "code": 0,
  "message": "获取成功",
  "platform": {
    "system": "Windows",
    "is_windows": true,
    "is_mock": false,
    "mt5_mode": "Real",
    "sync_status": {
      "success": false,
      "message": "⚠️ MT5连接失败，显示数据库缓存数据"
    }
  },
  "data": [...]
}
```

---

## 工作流程

### Windows系统启动流程

```
用户打开Dashboard
    ↓
访问 GET /accounts-db
    ↓
后端检测: platform.system() == "Windows"
    ↓
自动连接MT5
    ↓
获取 account_info()
    ↓
同步到数据库
    ↓
返回最新数据 + 同步状态
    ↓
前端显示"✅ MT5连接成功"
    ↓
显示实时余额和同步时间
```

### macOS系统启动流程

```
用户打开Dashboard
    ↓
访问 GET /accounts-db
    ↓
后端检测: platform.system() == "Darwin"
    ↓
跳过MT5同步
    ↓
返回数据库数据 + Mock标识
    ↓
前端显示"ℹ️ Mock模式"
    ↓
提示"无法查看实时数据"
```

---

## 技术实现

### 1. 平台检测
```python
import platform

system = platform.system()
is_windows = system == "Windows"
is_mock = not is_windows
```

### 2. 自动同步（仅Windows）
```python
if is_windows:
    connected = mt5_manager.connect()
    if connected:
        account_info = client.account_info()
        account_service.sync_account_from_mt5(
            account_id=acc.id,
            balance=account_info.balance,
            equity=account_info.equity
        )
```

### 3. 前端提示
```javascript
if (platformInfo.is_windows && syncStatus.success) {
    // 显示绿色成功横幅
} else if (platformInfo.is_mock) {
    // 显示蓝色Mock提示
}
```

---

## 使用建议

### 开发环境（macOS）
- 使用Mock模式进行功能开发
- 不需要真实MT5连接
- 数据稳定可预测

### 生产环境（Windows）
- 自动同步真实MT5数据
- 实时显示账户状态
- 需确保MT5终端运行

### 测试建议
1. macOS上开发UI和逻辑
2. Windows上测试MT5集成
3. 验证同步功能正常
4. 检查错误处理

---

## 相关文件

- **后端API**: `src/services/orchestrator/api/routes/accounts_db.py`
- **平台检测**: `src/services/orchestrator/api/routes/platform.py`
- **前端UI**: `src/services/dashboard/templates/index.html`
- **MT5连接**: `src/common/mt5/connection.py`
- **账户服务**: `src/services/orchestrator/service/account_service.py`

---

## 常见问题

**Q: Windows上显示"MT5连接失败"怎么办？**
A: 检查：
1. MetaTrader5终端是否运行
2. 账号是否登录
3. 配置文件中的Login/Password是否正确

**Q: macOS可以连接真实MT5吗？**
A: 不行。MetaTrader5只支持Windows系统，macOS只能使用Mock模式。

**Q: 如何手动触发同步？**
A: Windows系统每次刷新Dashboard都会自动同步。也可以调用API：
```bash
curl -X POST http://localhost:8002/accounts-db/{account_id}/sync \
  -d '{"balance": xxx, "equity": xxx}'
```

**Q: 同步频率是多少？**
A: 每次访问账户管理Tab都会触发同步（Windows）。建议实现定时任务每分钟同步一次。
