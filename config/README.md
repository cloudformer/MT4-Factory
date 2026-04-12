# 配置文件说明

## 配置文件列表

```
config/
├── mac.yaml                    # Mac本地开发（UI测试）
├── windows.yaml                # Windows完整测试
├── cloud.yaml                  # 云端生产环境
├── README.md                   # 本文档
└── CONFIGURATION_GUIDE.md      # 详细配置指南
```

---

## 三个环境定位

| 环境 | 配置文件 | 数据库 | 用途 | Validator | 历史数据 |
|------|---------|--------|------|-----------|---------|
| **Mac** | `mac.yaml` | SQLite | UI开发测试 | ❌ disabled | ❌ disabled |
| **Windows** | `windows.yaml` | PostgreSQL | 完整功能测试 | ✅ enabled | ✅ Phase 1 |
| **Cloud** | `cloud.yaml` | PostgreSQL RDS | 生产部署 | ✅ enabled | ✅ Phase 3 |

---

## 配置注释约定 ⭐

所有配置文件使用**统一的注释标记**来说明适用环境：

### 注释标记

| 标记 | 含义 |
|------|------|
| `Mac only` | 仅Mac环境使用 |
| `Windows only` | 仅Windows环境使用 |
| `Cloud only` | 仅Cloud生产环境使用 |
| `Windows and Cloud` | Windows和Cloud都使用，Mac不用 |
| `All` | 所有环境都使用 |

### 配置示例

```yaml
# ==================== 历史数据配置 ====================
# Windows and Cloud: 导入历史K线数据用于策略验证
# Mac: disabled（Mac不使用历史数据）
historical_data:
  enabled: true           # Mac: false | Windows: true (Phase 1) | Cloud: true (Phase 3)
  phase: 1                # Windows: 1 | Cloud: 3

  # 自动更新配置 (Cloud only)
  auto_update: false      # Mac/Windows: false | Cloud: true
  update_schedule: "0 2 * * *"  # Cloud only: 凌晨2点更新
  update_days: 1          # Cloud only: 更新最近N天数据

  # 数据库优化 (Cloud only - Phase 3)
  use_partitioning: false # Mac/Windows: false | Cloud: true
  partition_by: "year"    # Cloud only: 按年分区
```

**关键**：
1. 每个配置块顶部注释说明适用范围
2. 配置项注释中说明每个环境的值
3. 子配置块标注特定环境（如 `Cloud only`）

---

## 环境切换

### 通过DEVICE环境变量

```bash
# Mac环境
export DEVICE=mac
python app.py

# Windows环境
set DEVICE=windows
python app.py

# Cloud环境
export DEVICE=cloud
python app.py
```

系统自动加载对应配置：
- `DEVICE=mac` → `config/mac.yaml`
- `DEVICE=windows` → `config/windows.yaml`
- `DEVICE=cloud` → `config/cloud.yaml`

### 默认环境

不设置`DEVICE`时，默认使用`windows`配置：

```python
# src/common/config/settings.py
self.env = env or os.getenv('DEVICE', 'windows')
```

---

## 核心配置差异

### 数据库

| 环境 | 类型 | 连接方式 |
|------|------|---------|
| Mac | SQLite | `sqlite:///./data/evo_trade.db` |
| Windows | PostgreSQL | Docker服务名：`postgres` |
| Cloud | PostgreSQL RDS | 远程：`your-rds.amazonaws.com` |

### Validator

| 环境 | 启用 | 数据来源 | 并发数 |
|------|------|---------|--------|
| Mac | ❌ | - | - |
| Windows | ✅ | `realtime` (实时MT5) | 20 |
| Cloud | ✅ | `database` (历史数据库) | 50 |

### 历史数据

| 环境 | 启用 | Phase | 自动更新 | 分区表 |
|------|------|-------|---------|--------|
| Mac | ❌ | - | - | - |
| Windows | ✅ | 1 (67K行) | ❌ | ❌ |
| Cloud | ✅ | 3 (50M行) | ✅ | ✅ |

### MT5连接

所有MT5主机在`mt5_hosts`中配置，Validator和Execution通过`mt5_host`参数选择使用哪个主机：

```yaml
mt5_hosts:
  demo_1:                  # MT5主机1
    host: "..."
    login: "..."
    # ...
  real_1:                  # MT5主机2
    host: "..."
    login: "..."
    # ...

validator:
  mt5_host: "demo_1"      # 选择使用demo_1

execution:
  mt5_host: "real_1"      # 选择使用real_1（可自由切换）
```

详见：[MT5主机配置指南](./MT5_HOSTS_GUIDE.md)

---

## 配置验证

### 检查当前配置

```bash
export DEVICE=windows
python -c "
from src.common.config.settings import settings
print(f'环境: {settings.env}')
print(f'数据库: {settings.database}')
print(f'Validator: {settings.get(\"validator\", {}).get(\"enabled\")}')
print(f'历史数据: {settings.get(\"historical_data\", {}).get(\"enabled\")}')
"
```

### 查找特定环境配置

```bash
# 查找Cloud专用配置
grep -n "Cloud only" config/*.yaml

# 查找Windows和Cloud共用配置
grep -n "Windows and Cloud" config/*.yaml
```

---

## 配置最佳实践

### 1. 保持结构一致

所有三个配置文件**必须包含相同的配置项**，即使某些环境不使用：

✅ **正确**：
```yaml
# mac.yaml
historical_data:
  enabled: false      # Mac不使用，但配置项保留
  phase: 1
  auto_update: false
```

❌ **错误**：
```yaml
# mac.yaml
# 完全删除historical_data配置
```

### 2. 使用环境变量（生产环境）

```yaml
# Cloud配置使用环境变量
database:
  password: "${POSTGRES_PASSWORD}"    # ✅ 环境变量

# 不要硬编码密码
database:
  password: "my_password_123"         # ❌ 不安全
```

### 3. 清晰的注释

```yaml
# ✅ 好的注释
concurrency: 20     # Mac: N/A | Windows: 20 | Cloud: 50

# ❌ 不清楚的注释
concurrency: 20     # 并发数
```

---

## 常见问题

### Q: 为什么所有配置文件都要包含相同的配置项？

A: 便于对比和维护。可以并排查看三个文件，快速找到差异。防止遗漏某个环境的配置。

### Q: Mac环境为什么有那么多disabled的配置？

A: Mac只用于UI开发测试，不需要完整功能。保留配置项是为了结构统一。

### Q: Windows和Cloud的PostgreSQL配置一样吗？

A: 是的！除了连接地址（Docker vs RDS），其他配置（索引、分区表）完全一致。

### Q: 如何从Windows迁移到Cloud？

A: 复制`windows.yaml`为基础，修改：
1. `database.host` → RDS地址
2. `mt5.host` → 远程VPS IP
3. `historical_data.phase` → 3
4. `historical_data.auto_update` → true
5. 密码改为环境变量

---

## 相关文档

- [配置详细指南](./CONFIGURATION_GUIDE.md) - 详细的配置说明
- [环境配置说明](../docs/ENVIRONMENT_SETUP.md) - 环境定位和使用
- [历史数据指南](../docs/HISTORICAL_DATA_GUIDE.md) - Phase 1/2/3详解
- [启动指南](../docs/STARTUP_GUIDE.md) - 快速启动
