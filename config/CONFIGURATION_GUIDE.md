# 配置文件使用指南

## 配置文件注释约定

所有配置项的注释中会标注适用环境：

### 注释标记说明

| 标记 | 含义 | 示例 |
|------|------|------|
| `Mac only` | 仅Mac环境使用 | SQLite配置 |
| `Windows only` | 仅Windows环境使用 | Docker特定配置 |
| `Cloud only` | 仅Cloud生产环境使用 | 自动更新、分区表 |
| `Windows and Cloud` | Windows和Cloud都使用 | PostgreSQL、MT5连接 |
| `All` | 所有环境都使用 | 服务端口配置 |

---

## 配置示例

### 历史数据配置

```yaml
# ==================== 历史数据配置 ====================
# Windows and Cloud: 导入历史K线数据用于策略验证
# Mac: disabled（Mac不使用历史数据）
historical_data:
  enabled: true           # Mac: false | Windows: true (Phase 1) | Cloud: true (Phase 3)
  phase: 1                # Windows: 1 | Cloud: 3

  # 自动更新配置 (Cloud only)
  auto_update: false      # Mac/Windows: false | Cloud: true
  update_schedule: "0 2 * * *"  # Cloud only
  update_days: 1          # Cloud only

  # 数据库优化 (Cloud only - Phase 3)
  use_partitioning: false # Mac/Windows: false | Cloud: true
  partition_by: "year"    # Cloud only
```

### 如何阅读

1. **第一行总注释**：说明这个配置块的适用范围
   ```yaml
   # Windows and Cloud: 导入历史K线数据用于策略验证
   # Mac: disabled
   ```

2. **配置项注释**：说明每个环境的具体值
   ```yaml
   enabled: true  # Mac: false | Windows: true | Cloud: true
   ```

3. **子配置块标记**：某些配置只在特定环境使用
   ```yaml
   # 自动更新配置 (Cloud only)
   auto_update: true
   ```

---

## 三个环境快速对比

### Mac环境
```yaml
# 用途：UI开发和测试
database: SQLite
mt5: disabled
validator: disabled
historical_data: disabled
```

### Windows环境
```yaml
# 用途：完整功能测试
database: PostgreSQL (Docker)
mt5: enabled (本地MT5)
validator: enabled (realtime)
historical_data: enabled (Phase 1)
auto_update: false
use_partitioning: false
```

### Cloud环境
```yaml
# 用途：生产部署
database: PostgreSQL (RDS)
mt5: enabled (远程MT5)
validator: enabled (database)
historical_data: enabled (Phase 3)
auto_update: true              # Cloud only
use_partitioning: true         # Cloud only
```

---

## 配置文件结构

### 完全相同的结构

所有三个配置文件（mac.yaml, windows.yaml, cloud.yaml）都包含**完全相同的配置项**，只是：
- 值不同（enabled: true/false）
- 注释中标注适用环境

### 为什么这样设计？

1. **易于对比**：可以并排查看三个文件，快速找到差异
2. **防止遗漏**：所有配置项都在，不会遗漏某个环境的配置
3. **便于迁移**：从Windows迁移到Cloud时，知道哪些配置需要调整

---

## 快速查找配置

### 查找特定环境的配置

```bash
# 查找Mac专用配置
grep -n "Mac only" config/*.yaml

# 查找Cloud专用配置
grep -n "Cloud only" config/*.yaml

# 查找所有环境共用配置
grep -n "All" config/*.yaml
```

### 查看配置差异

```bash
# 对比Windows和Cloud配置
diff config/windows.yaml config/cloud.yaml

# 关键差异：
# - phase: 1 vs 3
# - auto_update: false vs true
# - use_partitioning: false vs true
# - concurrency: 20 vs 50
```

---

## 配置验证

### 检查配置正确性

```bash
# 加载并验证配置
export DEVICE=windows
python -c "
from src.common.config.settings import settings
print(f'环境: {settings.env}')
print(f'历史数据启用: {settings.get(\"historical_data\", {}).get(\"enabled\")}')
print(f'Phase: {settings.get(\"historical_data\", {}).get(\"phase\")}')
print(f'自动更新: {settings.get(\"historical_data\", {}).get(\"auto_update\")}')
"

# 预期输出 (Windows):
# 环境: windows
# 历史数据启用: True
# Phase: 1
# 自动更新: False
```

---

## 常见配置场景

### 1. 在Windows上启用Phase 2

```yaml
# config/windows.yaml
historical_data:
  enabled: true
  phase: 2              # 改为Phase 2（3.2M行）
  auto_update: false    # 保持false
```

### 2. 在Windows上启用自动更新

```yaml
# config/windows.yaml
historical_data:
  enabled: true
  phase: 1
  auto_update: true     # 改为true（测试自动更新功能）
  update_schedule: "0 2 * * *"
  update_days: 1
```

### 3. 在Cloud上临时禁用分区表

```yaml
# config/cloud.yaml
historical_data:
  enabled: true
  phase: 3
  use_partitioning: false  # 临时禁用（调试时）
  partition_by: "year"
```

---

## 相关文档

- [环境配置说明](../docs/ENVIRONMENT_SETUP.md) - 环境定位
- [历史数据指南](../docs/HISTORICAL_DATA_GUIDE.md) - Phase 1/2/3详解
- [启动指南](../docs/STARTUP_GUIDE.md) - 快速启动
