# MT5错误处理文档

## 概述

系统会自动检测Windows环境下MT5的安装和连接状态，并提供详细的错误信息和解决方案。

---

## 错误类型与处理

### 1️⃣ MT5终端未安装

**错误类型**: `mt5_not_installed`

**提示消息**: ❌ MT5未安装：找不到MetaTrader5终端

**解决方案**:
```
1. 下载并安装MetaTrader5终端：
   https://www.metatrader5.com/zh/download

2. 安装后重新启动应用

3. 确保MT5终端安装在默认路径：
   C:\Program Files\MetaTrader 5
```

**Dashboard显示**:
```
┌──────────────────────────────────────────────┐
│ ❌  MT5未安装：找不到MetaTrader5终端         │
│                                              │
│ ImportError: DLL load failed...              │
│                                              │
│ 解决方法：                                    │
│   1. 下载并安装MetaTrader5终端：             │
│      https://www.metatrader5.com/zh/download │
│   2. 安装后重新启动应用                       │
│   3. 确保MT5终端安装在默认路径：              │
│      C:\Program Files\MetaTrader 5          │
└──────────────────────────────────────────────┘
```

---

### 2️⃣ MT5 Python包未安装

**错误类型**: `module_not_found`

**提示消息**: ❌ MT5未安装：MetaTrader5 Python包未找到

**解决方案**:
```
1. 安装MetaTrader5 Python包：
   pip install MetaTrader5

2. 如果已安装但仍报错，重新安装：
   pip uninstall MetaTrader5
   pip install MetaTrader5
```

**Dashboard显示**:
```
┌──────────────────────────────────────────────┐
│ ❌  MT5未安装：MetaTrader5 Python包未找到    │
│                                              │
│ ModuleNotFoundError: No module named 'Meta...│
│                                              │
│ 解决方法：                                    │
│   1. 安装MetaTrader5 Python包：              │
│      pip install MetaTrader5                 │
│   2. 如果已安装但仍报错，重新安装             │
└──────────────────────────────────────────────┘
```

---

### 3️⃣ MT5初始化失败

**错误类型**: `initialization_failed`

**提示消息**: ❌ MT5初始化失败：可能未安装MT5终端

**解决方案**:
```
1. 安装MetaTrader5终端：
   https://www.metatrader5.com/zh/download

2. 确保MT5终端已完全安装并可正常启动

3. 重启应用重试
```

---

### 4️⃣ MT5连接失败

**错误类型**: `connection_failed`

**提示消息**: ⚠️ MT5连接失败，显示数据库缓存数据

**解决方案**:
```
1. 确认MetaTrader5终端是否正在运行
2. 检查MT5账号是否已登录
3. 验证配置文件中的Login/Password是否正确
```

**Dashboard显示**:
```
┌──────────────────────────────────────────────┐
│ ⚠️  MT5连接失败，显示数据库缓存数据          │
│                                              │
│ 解决方法：                                    │
│   1. 确认MetaTrader5终端是否正在运行          │
│   2. 检查MT5账号是否已登录                    │
│   3. 验证配置文件中的Login/Password是否正确   │
└──────────────────────────────────────────────┘
```

---

### 5️⃣ MT5登录失败

**错误类型**: `login_failed`

**提示消息**: ❌ MT5登录失败：账号或密码错误

**解决方案**:
```
1. 检查配置文件中的MT5账号（Login）
2. 验证MT5密码（Password）是否正确
3. 确认服务器地址（Server）是否正确
```

---

### 6️⃣ 其他未知错误

**错误类型**: `unknown_error`

**提示消息**: ⚠️ MT5同步失败: {详细错误}

**解决方案**:
```
1. 查看详细错误信息
2. 检查MT5终端是否正常运行
3. 联系技术支持
```

---

## API返回格式

### 成功情况
```json
{
  "code": 0,
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
  }
}
```

### 失败情况（MT5未安装）
```json
{
  "code": 0,
  "platform": {
    "system": "Windows",
    "is_windows": true,
    "is_mock": false,
    "mt5_mode": "Real",
    "sync_status": {
      "success": false,
      "message": "❌ MT5未安装：找不到MetaTrader5终端",
      "error_type": "mt5_not_installed",
      "error_detail": "ImportError: DLL load failed while importing...",
      "solutions": [
        "1. 下载并安装MetaTrader5终端：",
        "   https://www.metatrader5.com/zh/download",
        "",
        "2. 安装后重新启动应用",
        "",
        "3. 确保MT5终端安装在默认路径：",
        "   C:\\Program Files\\MetaTrader 5"
      ]
    }
  }
}
```

### 失败情况（Python包未安装）
```json
{
  "sync_status": {
    "success": false,
    "message": "❌ MT5未安装：MetaTrader5 Python包未找到",
    "error_type": "module_not_found",
    "error_detail": "ModuleNotFoundError: No module named 'MetaTrader5'",
    "solutions": [
      "1. 安装MetaTrader5 Python包：",
      "   pip install MetaTrader5",
      "",
      "2. 如果已安装但仍报错，重新安装：",
      "   pip uninstall MetaTrader5",
      "   pip install MetaTrader5"
    ]
  }
}
```

---

## 前端展示逻辑

### 错误严重性

| 错误类型 | 图标 | 颜色 | 描述 |
|---------|------|------|------|
| `mt5_not_installed` | ❌ | 红色 | 严重错误，MT5终端未安装 |
| `module_not_found` | ❌ | 红色 | 严重错误，Python包未安装 |
| `initialization_failed` | ❌ | 红色 | 严重错误，无法初始化 |
| `connection_failed` | ⚠️ | 黄色 | 警告，连接失败但可查看缓存 |
| `login_failed` | ❌ | 红色 | 错误，登录凭证问题 |
| `unknown_error` | ⚠️ | 黄色 | 未知问题 |

### UI组件

**错误横幅结构**:
```html
<div class="error-banner">
  <icon>  <!-- ❌ 或 ⚠️ -->
  <content>
    <title>  <!-- 错误标题 -->
    <error_detail>  <!-- 详细错误（灰色代码块）-->
    <solutions>  <!-- 解决方案列表 -->
      <solution_item>
      <solution_item>
      ...
    </solutions>
  </content>
</div>
```

---

## 测试场景

### 场景1：正常运行
```
条件：Windows + MT5已安装 + 已登录
结果：✅ 绿色横幅，显示余额和同步时间
```

### 场景2：MT5终端未运行
```
条件：Windows + MT5已安装 + 终端未启动
结果：⚠️ 黄色横幅，提示启动MT5终端
```

### 场景3：MT5终端未安装
```
条件：Windows + MT5未安装
结果：❌ 红色横幅，提供下载链接和安装步骤
```

### 场景4：Python包未安装
```
条件：Windows + MT5已安装 + Python包未装
结果：❌ 红色横幅，提供pip install命令
```

### 场景5：macOS开发环境
```
条件：macOS
结果：ℹ️ 蓝色横幅，说明Mock模式
```

---

## 相关文件

- **后端错误处理**: `src/services/orchestrator/api/routes/accounts_db.py`
- **前端展示**: `src/services/dashboard/templates/index.html`
- **MT5连接**: `src/common/mt5/connection.py`
- **Real客户端**: `src/common/mt5/real_client.py`
- **Mock客户端**: `src/common/mt5/mock_client.py`

---

## 常见问题

**Q: Windows上显示"MT5未安装"，但我已经安装了？**

A: 可能原因：
1. MT5安装路径不是默认路径
2. Python包未安装（`pip install MetaTrader5`）
3. 需要重启应用

**Q: 安装后仍然无法连接？**

A: 检查：
1. MT5终端是否正常启动
2. 账号是否已登录
3. config/development.yaml中的配置是否正确

**Q: 如何手动测试MT5连接？**

A: 运行测试脚本：
```bash
python scripts/test_mt5_connection.py
```

**Q: 错误信息太长，看不清？**

A: 错误详情显示在灰色代码块中，可以滚动查看完整信息。
