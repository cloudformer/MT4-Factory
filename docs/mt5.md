# MT5主机管理文档

## 概述

MT5主机是MT4-Factory系统中负责执行真实交易和数据获取的核心组件。每个MT5主机运行MT5 API Bridge，提供HTTP接口供服务调用。

---

## MT5主机类型

### Demo主机
- **用途**：策略验证、回测、数据获取
- **特点**：使用Demo账户，无真实资金风险
- **配置**：`host_type: demo`

### Real主机
- **用途**：实盘交易执行
- **特点**：使用真实账户，执行真实订单
- **配置**：`host_type: real`

---

## 连接测试诊断

### 测试层级

MT5主机连接测试分为**3个层级**，逐层诊断网络、服务、应用状态：

```
┌─────────────────────────────────────────────────────────┐
│ Level 1: TCP端口测试                                     │
│ - 测试目标：网络连通性                                   │
│ - 协议：TCP Socket                                       │
│ - 判断：端口是否开放                                     │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│ Level 2: HTTP服务测试                                    │
│ - 测试目标：HTTP服务运行状态                             │
│ - 协议：HTTP GET /health                                 │
│ - 判断：服务是否响应                                     │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│ Level 3: MT5协议测试                                     │
│ - 测试目标：MT5 Terminal连接状态                         │
│ - 协议：MT5 API (解析health响应)                         │
│ - 判断：MT5是否已登录                                    │
└─────────────────────────────────────────────────────────┘
```

### 故障诊断表

| 场景 | Level 1 (TCP) | Level 2 (HTTP) | Level 3 (MT5) | 说明 | 解决方案 |
|------|---------------|----------------|---------------|------|----------|
| ✅ **完全正常** | ✅ 端口可达 | ✅ HTTP正常 | ✅ MT5已连接 | 可以使用 | - |
| ⚠️ **API未启动** | ✅ 端口可达 | ❌ 连接被拒绝 | ⏭️ 未测试 | MT5 API Bridge未运行 | 启动API Bridge服务 |
| ❌ **网络不通** | ❌ 端口不可达 | ⏭️ 未测试 | ⏭️ 未测试 | 网络无法到达 | 检查IP、防火墙、路由 |
| ⚠️ **端口占用** | ✅ 端口可达 | ❌ 不是HTTP | ⏭️ 未测试 | 其他服务占用端口 | 检查端口配置，修改或停止占用服务 |
| ⚠️ **MT5未连接** | ✅ 端口可达 | ✅ HTTP正常 | ❌ MT5未连接 | API运行但MT5未登录 | 打开MT5 Terminal并登录 |
| ⚠️ **配置错误** | ✅ 端口可达 | ✅ HTTP正常 | ⚠️ 非MT5 API | 端口指向其他服务 | 检查host和port配置 |
| ⏱️ **超时** | ✅ 端口可达 | ⏱️ HTTP超时 | ⏭️ 未测试 | 服务响应过慢 | 检查服务负载，调整timeout |

### 测试结果示例

**成功案例：**
```
📡 Demo Worker 1
🌐 192.168.1.101:9090

✅ Level 1 (TCP): 端口可达 (15ms)
✅ Level 2 (HTTP): 服务响应正常 (20ms)
✅ Level 3 (MT5): MT5 Terminal已连接
```

**故障案例：DNS服务器（错误配置）**
```
📡 Test Server
🌐 8.8.8.8:53

✅ Level 1 (TCP): 端口可达 (12ms)
❌ Level 2 (HTTP): 端口开放但不是HTTP服务 (可能是其他协议)
⏭️ Level 3 (MT5): 未测试（HTTP未成功）

诊断：8.8.8.8:53是Google DNS服务器，不是MT5 API Bridge
解决：修改host为正确的MT5主机IP地址
```

**故障案例：API未启动**
```
📡 ICMarkets Real Worker 1
🌐 192.168.1.101:9090

✅ Level 1 (TCP): 端口可达 (10ms)
❌ Level 2 (HTTP): 端口开放但不是HTTP服务
⏭️ Level 3 (MT5): 未测试（HTTP未成功）

诊断：端口开放但HTTP请求失败，可能API未启动
解决：在Windows机器上启动MT5 API Bridge服务
```

**故障案例：MT5未登录**
```
📡 Demo Worker 1
🌐 192.168.1.101:9090

✅ Level 1 (TCP): 端口可达 (12ms)
✅ Level 2 (HTTP): 服务响应正常 (18ms)
❌ Level 3 (MT5): MT5 API Bridge运行但MT5 Terminal未连接

诊断：API服务正常运行，但MT5 Terminal未启动或未登录
解决：打开MT5 Terminal并使用配置的账号登录
```

---

## MT5主机配置

### 数据库表结构

```sql
CREATE TABLE mt5_hosts (
    id VARCHAR(32) PRIMARY KEY,           -- 主机唯一标识
    name VARCHAR(255) NOT NULL,           -- 显示名称
    host_type VARCHAR(20) NOT NULL,       -- 类型: demo/real
    host VARCHAR(255) NOT NULL,           -- IP地址或域名
    port INTEGER NOT NULL DEFAULT 9090,   -- API端口
    api_key VARCHAR(255),                 -- API认证密钥
    timeout INTEGER DEFAULT 10,           -- 连接超时(秒)
    login INTEGER,                        -- MT5账号
    password VARCHAR(255),                -- MT5密码
    server VARCHAR(255),                  -- MT5服务器
    use_investor BOOLEAN DEFAULT TRUE,    -- 是否使用只读账户
    enabled BOOLEAN DEFAULT TRUE,         -- 是否启用
    tags TEXT,                            -- 标签(JSON数组)
    notes VARCHAR(500),                   -- 备注
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

### 配置示例

**局域网Demo主机：**
```yaml
id: demo_1
name: "Demo Worker 1"
host_type: demo
host: 192.168.1.101        # Windows机器局域网IP
port: 9090
login: 5049130509
password: "demo_password"
server: "MetaQuotes-Demo"
api_key: "demo_key_secure"
timeout: 10
use_investor: true
enabled: true
tags: ["demo", "validation"]
```

**云服务器Real主机：**
```yaml
id: real_icm_1
name: "ICMarkets Real Worker 1"
host_type: real
host: 52.10.20.101         # 云服务器公网IP
port: 9090
login: 8012345678
password: "real_password"
server: "ICMarkets-Live"
api_key: "real_key_secure"
timeout: 15
use_investor: false
enabled: true
tags: ["real", "icmarkets", "primary"]
```

---

## 策略绑定MT5主机

### 绑定流程

```
1. 生成策略 (candidate状态)
   ↓
2. 点击"绑定MT5主机"
   ↓
3. 选择MT5主机 (demo_1 / real_icm_1)
   ↓
4. 策略保存 mt5_host_id
   ↓
5. 激活策略 → 策略运行在指定主机
```

### API端点

**绑定MT5主机：**
```bash
POST /api/registration/bind-mt5/{strategy_id}
Content-Type: application/json

{
  "mt5_host_id": "demo_1"  # 绑定到demo_1
}
```

**解绑MT5主机：**
```bash
POST /api/registration/bind-mt5/{strategy_id}
Content-Type: application/json

{
  "mt5_host_id": null  # 解绑
}
```

### 数据库关联

```sql
-- strategies表添加mt5_host_id外键
ALTER TABLE strategies 
ADD COLUMN mt5_host_id VARCHAR(32),
ADD FOREIGN KEY (mt5_host_id) REFERENCES mt5_hosts(id);
```

---

## 网络架构

### Mac开发环境
```
┌─────────────────────────┐
│ Mac (Dashboard)         │
│ localhost:8001          │
└──────────┬──────────────┘
           │ 
           │ ❌ 无法连接MT5
           │   (Mac不支持MT5)
           │
           ↓
    使用Mock/Database数据源
```

### Windows本地环境
```
┌─────────────────────────┐
│ Windows机器              │
│ - Dashboard: :8001      │
│ - MT5 Terminal          │
│ - MT5 API Bridge: :9090 │
└─────────────────────────┘
           ↕
    localhost连接
```

### 局域网环境
```
┌─────────────────┐       ┌─────────────────┐
│ Mac (Dashboard) │       │ Windows机器      │
│ 192.168.1.100   │◄─────►│ 192.168.1.101   │
│ :8001           │  WiFi │ - MT5 Terminal  │
└─────────────────┘       │ - API: :9090    │
                          └─────────────────┘
```

### 云部署环境
```
┌─────────────────┐       ┌─────────────────┐
│ Mac/浏览器       │       │ AWS/阿里云       │
│                 │◄─────►│ 52.10.20.101    │
└─────────────────┘ HTTPS │ - Dashboard     │
                          │ - MT5 Bridge    │
                          └─────────────────┘
```

---

## 安全建议

1. **生产环境必须使用API Key**
   - 在`api_key`字段配置强随机密钥
   - API Bridge验证`Authorization: Bearer {api_key}`

2. **不要在公网暴露Demo主机**
   - Demo主机仅用于内网验证
   - 使用VPN或防火墙限制访问

3. **Real主机使用只读账户验证**
   - 设置`use_investor: true`
   - 使用MT5 Investor账户（只读权限）
   - 实际交易时才使用完整权限账户

4. **密码加密存储**
   - 生产环境应加密存储`password`字段
   - 使用环境变量或密钥管理服务

---

## 故障排查清单

### 连接失败排查步骤

1. **验证IP和端口**
   ```bash
   # 在Mac/Linux上测试端口
   nc -zv 192.168.1.101 9090
   
   # 或使用telnet
   telnet 192.168.1.101 9090
   ```

2. **检查Windows防火墙**
   ```powershell
   # Windows PowerShell
   # 查看9090端口规则
   Get-NetFirewallRule | Where-Object {$_.DisplayName -like "*9090*"}
   
   # 添加防火墙规则
   New-NetFirewallRule -DisplayName "MT5 API Bridge" -Direction Inbound -Protocol TCP -LocalPort 9090 -Action Allow
   ```

3. **验证API Bridge运行状态**
   ```cmd
   # Windows命令行
   netstat -an | findstr :9090
   
   # 应该看到：
   # TCP    0.0.0.0:9090           0.0.0.0:0              LISTENING
   ```

4. **测试HTTP响应**
   ```bash
   # 使用curl测试
   curl http://192.168.1.101:9090/health
   
   # 期望响应：
   # {"status": "healthy", "mt5_connected": true}
   ```

5. **检查MT5 Terminal状态**
   - MT5 Terminal是否运行？
   - 是否已登录账户？
   - 账户类型是否匹配（Demo/Real）？

---

## 参考文档

- [MT5 API Bridge开发文档](./mt5-api-bridge.md)
- [系统架构设计](./architecture.md)
- [新功能测试指南](./NEW_FEATURES_TEST.md)
