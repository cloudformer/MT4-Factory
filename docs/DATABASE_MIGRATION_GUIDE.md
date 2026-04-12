# 数据库迁移指南：SQLite → PostgreSQL

## 🎯 为什么要切换到PostgreSQL？

```
✅ 优势：
1. 生产级数据库（并发、性能、稳定性）
2. 历史数据回测必需（索引优化、复杂查询）
3. 支持分区表、TimescaleDB（Phase 3）
4. 更好的并发支持（多服务访问）
5. 数据完整性约束更强

⏰ 最佳时机：
- 现在数据量小，迁移容易（<5分钟）
- 避免未来二次迁移
```

---

## 📋 完整迁移步骤

### **前置要求**

```bash
# 1. 确保Docker已安装
docker --version

# 2. 确保Python依赖已安装
pip install psycopg2-binary  # PostgreSQL驱动
```

---

### **步骤1：启动PostgreSQL容器** ⏱️ 1分钟

```bash
# 1. 启动PostgreSQL
cd /Users/frankzhang/repo-private/MT4-Factory
docker-compose up -d postgres

# 输出示例：
# [+] Running 2/2
#  ✔ Network mt4-factory-network     Created
#  ✔ Container mt4-factory-postgres  Started

# 2. 等待PostgreSQL就绪
docker-compose logs -f postgres

# 看到以下日志表示启动成功：
# database system is ready to accept connections

# 按Ctrl+C退出日志查看

# 3. 验证连接
docker exec -it mt4-factory-postgres psql -U evo_trade_user -d evo_trade -c "SELECT version();"

# 输出：
# PostgreSQL 16.x on x86_64-pc-linux-musl...
```

---

### **步骤2：迁移SQLite数据** ⏱️ 2-5分钟

```bash
# 1. 运行迁移脚本
python scripts/migrate_sqlite_to_postgres.py

# 输出示例：
# 🔄 开始数据迁移：SQLite → PostgreSQL
# ============================================================
# 
# 📂 SQLite数据库: /Users/frankzhang/repo-private/MT4-Factory/data/evo_trade.db
# 🐘 PostgreSQL: localhost:5432/evo_trade
#    ✅ PostgreSQL连接成功
# 
# 📊 创建PostgreSQL表结构...
#    ✅ 表结构创建完成
# 
# 📦 开始迁移数据...
# ------------------------------------------------------------
#    [账户] 迁移中... ✅ 2条
#    [策略] 迁移中... ✅ 10条
#    [信号] 迁移中... ✅ 15条
#    [交易] 迁移中... ✅ 19条
# 
# ------------------------------------------------------------
# 📊 验证迁移结果:
#    ✅ 账户: SQLite=2, PostgreSQL=2
#    ✅ 策略: SQLite=10, PostgreSQL=10
#    ✅ 信号: SQLite=15, PostgreSQL=15
#    ✅ 交易: SQLite=19, PostgreSQL=19
# 
# ============================================================
# ✅ 迁移完成！共迁移 46 条记录
```

---

### **步骤3：验证数据** ⏱️ 1分钟

```bash
# 1. 连接PostgreSQL
docker exec -it mt4-factory-postgres psql -U evo_trade_user -d evo_trade

# 2. 检查表和数据
\dt  -- 查看所有表

# 输出：
#              List of relations
#  Schema |       Name        | Type  |      Owner
# --------+-------------------+-------+-----------------
#  public | accounts          | table | evo_trade_user
#  public | signals           | table | evo_trade_user
#  public | strategies        | table | evo_trade_user
#  public | trades            | table | evo_trade_user

# 3. 查询数据量
SELECT 
    'strategies' as table_name, COUNT(*) as count FROM strategies
UNION ALL
SELECT 'signals', COUNT(*) FROM signals
UNION ALL
SELECT 'trades', COUNT(*) FROM trades
UNION ALL
SELECT 'accounts', COUNT(*) FROM accounts;

# 输出：
#  table_name  | count
# -------------+-------
#  strategies  |    10
#  signals     |    15
#  trades      |    19
#  accounts    |     2

# 4. 退出
\q
```

---

### **步骤4：备份SQLite并更新配置** ⏱️ 1分钟

```bash
# 1. 备份SQLite数据库
mv data/evo_trade.db data/evo_trade.db.backup

# 2. 配置文件已自动更新
# config/development.yaml 已切换到PostgreSQL配置

# 3. 验证配置
cat config/development.yaml | grep -A 10 "database:"

# 输出：
# database:
#   host: "localhost"
#   port: 5432
#   database: "evo_trade"
#   user: "evo_trade_user"
#   password: "evo_trade_pass_dev_2024"
#   ...
```

---

### **步骤5：重启所有服务** ⏱️ 30秒

```bash
# 1. 停止所有服务
# 按Ctrl+C停止所有运行中的Python进程

# 2. 重新启动服务
# Dashboard
python -m uvicorn src.services.dashboard.api.app:app --host 0.0.0.0 --port 8001 &

# Orchestrator
python -m uvicorn src.services.orchestrator.api.app:app --host 0.0.0.0 --port 8002 &

# 3. 访问Dashboard验证
open http://localhost:8001

# 4. 检查数据是否正常显示
# 查看策略列表、交易记录等
```

---

### **步骤6：验证功能** ⏱️ 2分钟

```bash
# 1. 测试生成策略
# 在Dashboard点击"生成策略"，检查是否成功

# 2. 检查PostgreSQL日志
docker-compose logs -f postgres

# 应该能看到SQL查询日志（如果echo=true）

# 3. 验证数据持久化
# 关闭所有服务，重启PostgreSQL
docker-compose restart postgres

# 重新启动服务，数据应该依然存在
```

---

## 🔧 故障排查

### **问题1：PostgreSQL连接失败**

```bash
# 症状：
# sqlalchemy.exc.OperationalError: could not connect to server

# 解决：
# 1. 检查容器是否运行
docker ps | grep postgres

# 2. 检查容器日志
docker-compose logs postgres

# 3. 重启容器
docker-compose restart postgres

# 4. 检查端口占用
lsof -i :5432
```

### **问题2：迁移脚本失败**

```bash
# 症状：
# ModuleNotFoundError: No module named 'psycopg2'

# 解决：
pip install psycopg2-binary

# 或
pip install -r requirements.txt
```

### **问题3：数据不一致**

```bash
# 重新迁移
# 1. 清空PostgreSQL
docker exec -it mt4-factory-postgres psql -U evo_trade_user -d evo_trade -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"

# 2. 重新运行迁移
python scripts/migrate_sqlite_to_postgres.py
```

---

## 📊 性能对比

### **SQLite vs PostgreSQL**

| 指标 | SQLite | PostgreSQL | 提升 |
|------|--------|------------|------|
| **并发连接** | 1个写入 | 多个写入 | ✅ 显著提升 |
| **查询速度** | 小数据快 | 大数据快 | ✅ 大数据优势 |
| **索引优化** | 基础 | 高级 | ✅ 更强大 |
| **数据完整性** | 基础 | 完整 | ✅ 更可靠 |
| **历史数据** | ❌ 不适合 | ✅ 适合 | ✅ Phase 1-3必需 |

---

## 🎯 迁移后的优势

### **1. 立即获得的优势**

```
✅ 生产级数据库
✅ 更好的并发支持
✅ 更强的数据完整性
✅ 更好的错误处理
✅ 支持复杂查询
```

### **2. 未来准备（历史数据回测）**

```
✅ 索引优化（查询加速100倍）
✅ 分区表支持（Phase 3）
✅ TimescaleDB扩展（可选）
✅ 支持50M+行数据
✅ 查询速度：<100ms（有索引）
```

### **3. 开发体验提升**

```
✅ pgAdmin可视化管理
✅ 更好的SQL调试
✅ 更丰富的数据类型
✅ 支持JSON/JSONB字段
```

---

## 🐘 PostgreSQL日常管理

### **启动/停止容器**

```bash
# 启动
docker-compose up -d postgres

# 停止
docker-compose stop postgres

# 重启
docker-compose restart postgres

# 查看日志
docker-compose logs -f postgres

# 查看状态
docker-compose ps
```

### **数据备份**

```bash
# 备份数据库
docker exec mt4-factory-postgres pg_dump -U evo_trade_user evo_trade > backup_$(date +%Y%m%d).sql

# 恢复数据库
cat backup_20260411.sql | docker exec -i mt4-factory-postgres psql -U evo_trade_user -d evo_trade
```

### **连接数据库**

```bash
# 命令行连接
docker exec -it mt4-factory-postgres psql -U evo_trade_user -d evo_trade

# 或使用pgAdmin（可选）
docker-compose --profile tools up -d pgadmin

# 访问: http://localhost:5050
# 邮箱: admin@mt4factory.local
# 密码: admin
```

---

## 📝 总结

### **迁移检查清单**

- [ ] ✅ 安装Docker
- [ ] ✅ 安装psycopg2-binary
- [ ] ✅ 启动PostgreSQL容器
- [ ] ✅ 运行迁移脚本
- [ ] ✅ 验证数据完整性
- [ ] ✅ 备份SQLite数据库
- [ ] ✅ 重启所有服务
- [ ] ✅ 测试功能正常

### **总耗时：5-10分钟** ⏱️

```
步骤1: 启动PostgreSQL  - 1分钟
步骤2: 迁移数据        - 2-5分钟
步骤3: 验证数据        - 1分钟
步骤4: 更新配置        - 1分钟
步骤5: 重启服务        - 30秒
步骤6: 验证功能        - 2分钟
──────────────────────────────────
总计:                   5-10分钟 ✅
```

### **下一步**

迁移完成后，你可以：

1. ✅ 继续正常开发（使用PostgreSQL）
2. ✅ 随时开始Phase 1历史数据回测
3. ✅ 享受更好的性能和稳定性
4. ✅ 数据库自动运行（Docker容器）

**PostgreSQL已经准备好支持未来的所有功能！** 🚀
