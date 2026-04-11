# Changelog

## 2026-04-10 - MT5连接服务配置和管理

### 变更说明
完善MT5对接服务（Execution Service），支持完整的连接配置、代理设置和连接管理。

### 新增功能

#### 1. MT5连接配置
**新增配置项** (`config/development.yaml` 和 `config/production.yaml`):
```yaml
mt5:
  company: "MetaQuotes Ltd."       # 经纪商公司名
  server: "MetaQuotes-Demo"        # 服务器名称  
  login: 5049130509                # 账号
  password: "-ySbKy4z"             # 主密码（交易模式）
  investor_password: "Fn@4ElKo"    # 投资者密码（只读模式）
  
  # 高级配置（Windows）
  path: ""         # MT5终端路径
  timeout: 60000   # 连接超时
  portable: false  # 便携模式
  
  # 代理配置
  proxy:
    enabled: false
    host: ""
    port: 0
    type: "HTTP"
```

#### 2. 连接管理器
**新增文件**: `src/common/mt5/connection.py`
- `MT5ConnectionManager` - 单例连接管理器
- 自动根据平台选择实现（Windows使用真实MT5，macOS/Linux使用Mock）
- 支持交易模式和投资者模式切换
- 连接状态管理和健康检查

#### 3. 接口增强
**更新**: `src/common/mt5/interface.py`, `real_client.py`, `mock_client.py`
- `initialize()` 方法支持可选登录参数
- `RealMT5Client` 构造函数支持 path、timeout、portable 参数
- `MockMT5Client` 匹配真实客户端接口

#### 4. Execution服务集成
**更新**: `src/services/execution/api/app.py`
- 添加生命周期管理（启动时自动连接MT5）
- 使用全局 `mt5_manager` 单例
- 增强健康检查接口，返回完整MT5状态

**更新**: `src/services/execution/service/order_service.py`
- 使用全局连接管理器
- 连接状态检查

#### 5. 测试工具
**新增**: `scripts/test_mt5_connection.py`
- 测试交易模式连接
- 测试投资者模式连接
- 测试实时报价获取
- 显示账户详细信息

### 测试验证
- ✅ MT5连接管理器正常工作
- ✅ Execution服务启动时自动连接MT5
- ✅ 健康检查返回完整账户信息
- ✅ Mock模式（macOS开发）正常工作
- ✅ 支持交易模式和投资者模式切换

### 使用方式

**启动Execution服务**:
```bash
python -m uvicorn src.services.execution.api.app:app --host 0.0.0.0 --port 8003
```

**测试连接**:
```bash
python scripts/test_mt5_connection.py
curl http://localhost:8003/health
```

**代码中使用**:
```python
from src.common.mt5 import mt5_manager

# 连接MT5（交易模式）
mt5_manager.connect(use_investor=False)

# 获取客户端
client = mt5_manager.get_client()
account = client.account_info()
```

### 生产环境部署
1. 在Windows服务器上部署
2. 设置环境变量：`MT5_LOGIN`, `MT5_PASSWORD`, `MT5_SERVER` 等
3. 如需代理，配置 `mt5.proxy` 节
4. Execution服务会自动连接并保持连接

---

## 2026-04-10 - 服务URL配置统一管理

### 变更说明
所有服务间调用的URL已从硬编码改为配置文件管理，提升系统的灵活性和可维护性。

### 修改内容

#### 1. 配置文件
- **新增**: `config/development.yaml` 添加 `service_urls` 配置节
- **新增**: `config/production.yaml` 生产环境配置示例
- **新增**: `config/README.md` 配置使用说明文档

配置结构：
```yaml
service_urls:
  strategy: "http://127.0.0.1:8001"
  orchestrator: "http://127.0.0.1:8002"
  execution: "http://127.0.0.1:8003"
  dashboard: "http://127.0.0.1:8000"
```

#### 2. 代码修改
- **修改**: `src/services/dashboard/api/routes/data.py`
  - 移除硬编码: `STRATEGY_URL`, `ORCHESTRATOR_URL`, `EXECUTION_URL`
  - 改用配置读取: `settings.get("service_urls", {})`

- **修改**: `src/services/dashboard/api/routes/registration.py`
  - 移除硬编码: `ORCHESTRATOR_URL = "http://localhost:8002"`
  - 改用配置读取

- **修改**: `scripts/manage_registration.py`
  - 移除硬编码: `ORCHESTRATOR_URL = "http://localhost:8002"`
  - 改用配置读取

#### 3. 部署灵活性提升

**支持的部署方式**:
1. ✅ 本地开发 (`http://127.0.0.1:800X`)
2. ✅ 独立域名 (`https://service.domain.com`)
3. ✅ API网关+路径 (`https://api.domain.com/service`)
4. ✅ K8s服务发现 (`http://service-name:port`)

### 向后兼容性
所有配置读取都提供了默认值，确保即使配置缺失也能正常运行。

### 测试验证
- ✅ Dashboard → Orchestrator 代理调用正常
- ✅ CLI脚本读取配置正常
- ✅ 服务健康检查通过
- ✅ 注册管理功能正常

### 下一步
未来可通过修改配置文件轻松实现：
- 多环境部署（dev/staging/production）
- 负载均衡配置
- 灰度发布
- 跨区域部署
