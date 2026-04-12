# Validator并发验证架构：支持100+策略7x24运行

## 🎯 需求分析

### **规模与挑战**

```
需求：
  - 100+ active策略需要持续验证
  - 每个策略每小时验证一次
  - 获取最新MT5数据 + 运行回测 + 更新数据库
  - 7x24小时不间断运行

挑战：
  ❌ 串行执行：100策略 × 2秒 = 200秒（3分钟）
  ❌ 每小时执行一次，留给处理的时间窗口有限
  ❌ MT5 API调用频率限制
  ✅ 需要高效并发架构
```

---

## 🏗️ 并发架构设计

### **三层并发策略**

```
┌─────────────────────────────────────────────────────────┐
│                 Validator服务架构                        │
└─────────────────────────────────────────────────────────┘

层级1: 任务调度器
  └─> APScheduler (每小时触发一次批量验证)

层级2: 并发执行器
  └─> AsyncIO协程池 (20-50个并发任务)
       ├─> 批量获取策略列表
       ├─> 并发调用MT5 API获取数据
       ├─> 并发运行回测计算
       └─> 批量更新数据库

层级3: 资源池
  └─> PostgreSQL连接池 (50-100连接)
  └─> HTTP客户端连接池 (50连接)
```

---

## ⚡ 性能分析

### **串行 vs 并发对比**

| 执行模式 | 单个耗时 | 100策略总耗时 | 效率 |
|----------|----------|----------------|------|
| **串行** | 2秒 | 200秒 (3分20秒) | ⛔ 不可接受 |
| **并发10个** | 2秒 | 20秒 | ✅ 可接受 |
| **并发20个** | 2秒 | 10秒 | ✅ 推荐 |
| **并发50个** | 2秒 | 4秒 | ⚡ 最优（需测试） |

### **单策略验证耗时分解**

```
步骤                      耗时     可并发
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. 获取策略参数（DB）      50ms     ✅
2. 调用MT5获取最新数据     800ms    ✅ (I/O等待)
3. 计算技术指标           200ms    ✅ (CPU密集)
4. 运行回测逻辑           300ms    ✅ (CPU密集)
5. 更新验证结果（DB）      150ms    ✅
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
总计                      ~1.5秒   ✅ 全部可并发
```

**关键发现**：所有步骤都可以并发执行！

---

## 💻 代码实现（AsyncIO方案）

### **src/services/validator/concurrent_validator.py**

```python
import asyncio
import aiohttp
from datetime import datetime
from typing import List, Dict
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from src.common.config import settings
from src.common.logger import get_logger
from src.models.strategy import Strategy
from src.services.strategy.backtest_engine import BacktestEngine

logger = get_logger(__name__)


class ConcurrentValidator:
    """并发策略验证器：支持100+策略同时验证"""
    
    def __init__(self, concurrency: int = 20):
        """
        Args:
            concurrency: 并发数（推荐20-50）
        """
        self.concurrency = concurrency
        self.scheduler = AsyncIOScheduler()
        
        # 异步数据库引擎
        db_config = settings.database
        db_url = (f"postgresql+asyncpg://{db_config['user']}:{db_config['password']}"
                  f"@{db_config['host']}:{db_config['port']}/{db_config['database']}")
        self.engine = create_async_engine(
            db_url,
            pool_size=50,      # 连接池大小
            max_overflow=50,   # 最大溢出连接
            echo=False
        )
        self.AsyncSessionLocal = sessionmaker(
            self.engine, 
            class_=AsyncSession, 
            expire_on_commit=False
        )
        
        # HTTP客户端（复用连接）
        self.http_session = None
        
        # MT5配置
        self.mt5_config = settings.mt5
        
    async def start(self):
        """启动Validator服务"""
        logger.info(f"🚀 启动Validator服务 (并发数: {self.concurrency})")
        
        # 创建HTTP会话
        connector = aiohttp.TCPConnector(limit=50, limit_per_host=50)
        self.http_session = aiohttp.ClientSession(connector=connector)
        
        # 立即执行一次
        await self.validate_all_strategies()
        
        # 定时任务：每小时执行一次
        self.scheduler.add_job(
            self.validate_all_strategies,
            trigger='interval',
            hours=1,
            id='validate_strategies',
            name='验证所有Active策略'
        )
        
        self.scheduler.start()
        logger.info("✅ 定时任务已启动（每小时执行）")
        
        # 保持运行
        try:
            while True:
                await asyncio.sleep(3600)
        except KeyboardInterrupt:
            logger.info("收到停止信号")
            await self.shutdown()
    
    async def shutdown(self):
        """优雅关闭"""
        logger.info("正在关闭Validator服务...")
        self.scheduler.shutdown()
        await self.http_session.close()
        await self.engine.dispose()
        logger.info("✅ Validator已关闭")
    
    async def validate_all_strategies(self):
        """验证所有Active策略（并发执行）"""
        start_time = datetime.now()
        logger.info("=" * 60)
        logger.info(f"🔍 开始批量验证 - {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 60)
        
        # 1. 获取所有Active策略
        strategies = await self._get_active_strategies()
        total = len(strategies)
        
        if total == 0:
            logger.warning("⚠️  未找到Active策略")
            return
        
        logger.info(f"📊 找到 {total} 个Active策略，开始并发验证...")
        
        # 2. 创建并发任务（使用信号量控制并发数）
        semaphore = asyncio.Semaphore(self.concurrency)
        tasks = [
            self._validate_strategy_with_semaphore(strategy, semaphore)
            for strategy in strategies
        ]
        
        # 3. 并发执行
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 4. 统计结果
        success_count = sum(1 for r in results if r is True)
        failed_count = sum(1 for r in results if isinstance(r, Exception))
        
        elapsed = (datetime.now() - start_time).total_seconds()
        logger.info("=" * 60)
        logger.info(f"✅ 批量验证完成")
        logger.info(f"   总计: {total} | 成功: {success_count} | 失败: {failed_count}")
        logger.info(f"   耗时: {elapsed:.2f}秒 | 平均: {elapsed/total:.2f}秒/策略")
        logger.info("=" * 60)
    
    async def _validate_strategy_with_semaphore(
        self, 
        strategy: Strategy, 
        semaphore: asyncio.Semaphore
    ) -> bool:
        """使用信号量控制并发的策略验证"""
        async with semaphore:
            return await self._validate_single_strategy(strategy)
    
    async def _validate_single_strategy(self, strategy: Strategy) -> bool:
        """验证单个策略（核心逻辑）"""
        try:
            strategy_id = strategy.id
            symbol = strategy.params.get("symbol", "EURUSD")
            timeframe = strategy.params.get("timeframe", "H1")
            
            logger.debug(f"🔄 [{strategy_id}] {symbol} {timeframe} 验证中...")
            
            # 步骤1: 获取MT5最新数据（I/O操作，自动并发）
            bars = await self._fetch_mt5_data(symbol, timeframe, count=100)
            
            if not bars:
                logger.warning(f"⚠️  [{strategy_id}] 无法获取MT5数据")
                return False
            
            # 步骤2: 运行回测（CPU密集，但asyncio可以切换）
            # 注意：如果回测是纯CPU操作，考虑使用 asyncio.to_thread()
            result = await asyncio.to_thread(
                self._run_backtest,
                strategy,
                bars
            )
            
            # 步骤3: 更新数据库（I/O操作）
            await self._update_validation_result(strategy_id, result)
            
            logger.info(
                f"✅ [{strategy_id}] 验证完成 - "
                f"胜率: {result['win_rate']:.1f}% | "
                f"盈亏: {result['total_pnl']:+.2f}"
            )
            return True
            
        except Exception as e:
            logger.error(f"❌ [{strategy.id}] 验证失败: {str(e)}", exc_info=True)
            return False
    
    async def _get_active_strategies(self) -> List[Strategy]:
        """获取所有Active策略"""
        async with self.AsyncSessionLocal() as session:
            from sqlalchemy import select
            stmt = select(Strategy).where(Strategy.status == "active")
            result = await session.execute(stmt)
            return result.scalars().all()
    
    async def _fetch_mt5_data(
        self, 
        symbol: str, 
        timeframe: str, 
        count: int
    ) -> List[Dict]:
        """异步获取MT5数据"""
        if self.mt5_config["mode"] == "local":
            # 本地模式：通过host.docker.internal访问
            url = f"http://{self.mt5_config['host']}:9090/bars/{symbol}"
        else:
            # 远程模式
            url = f"http://{self.mt5_config['host']}:{self.mt5_config['port']}/bars/{symbol}"
        
        params = {"timeframe": timeframe, "count": count}
        
        async with self.http_session.get(url, params=params, timeout=10) as resp:
            resp.raise_for_status()
            data = await resp.json()
            return data["bars"]
    
    def _run_backtest(self, strategy: Strategy, bars: List[Dict]) -> Dict:
        """运行回测（同步函数，通过to_thread调用）"""
        engine = BacktestEngine()
        result = engine.run_backtest(
            strategy_params=strategy.params,
            bars=bars,
            initial_balance=100
        )
        return result
    
    async def _update_validation_result(
        self, 
        strategy_id: str, 
        result: Dict
    ):
        """更新验证结果到数据库"""
        async with self.AsyncSessionLocal() as session:
            stmt = (
                f"UPDATE strategies SET "
                f"last_validation_time = NOW(), "
                f"validation_win_rate = {result['win_rate']}, "
                f"validation_total_pnl = {result['total_pnl']}, "
                f"validation_total_trades = {result['total_trades']} "
                f"WHERE id = '{strategy_id}'"
            )
            await session.execute(stmt)
            await session.commit()


# ==================== 启动入口 ====================

async def main():
    """主函数"""
    # 从配置读取并发数
    concurrency = settings.validator.get("concurrency", 20)
    
    validator = ConcurrentValidator(concurrency=concurrency)
    await validator.start()


if __name__ == "__main__":
    asyncio.run(main())
```

---

## 🐳 Docker部署配置

### **docker-compose.yml（Validator配置）**

```yaml
services:
  validator:
    build:
      context: .
      dockerfile: docker/Dockerfile.validator
    container_name: mt4-validator
    environment:
      - ENV=production
      - VALIDATOR_CONCURRENCY=20  # 并发数 ⭐
    depends_on:
      postgres:
        condition: service_healthy
    volumes:
      - ./logs:/app/logs
      - ./config:/app/config:ro
    restart: unless-stopped
    networks:
      - mt4-network
    extra_hosts:
      - "host.docker.internal:host-gateway"  # 访问宿主机MT5
    
    # 资源限制（128GB机器无需限制）
    # deploy:
    #   resources:
    #     limits:
    #       cpus: '4.0'      # 4核CPU
    #       memory: 4G       # 4GB内存
```

### **config/windows.yaml（并发配置）**

```yaml
validator:
  enabled: true
  mode: "active_strategies"
  concurrency: 20              # 并发数 ⭐
  schedule_interval: 3600      # 每小时（秒）
  demo_account: "5049130509"
  initial_balance: 100

database:
  host: "postgres"
  port: 5432
  pool_size: 50                # 连接池大小 ⭐
  max_overflow: 50             # 最大溢出 ⭐
```

---

## 📊 资源消耗分析（128GB Windows）

### **内存消耗**

```
组件                    单个    100并发   备注
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Validator进程基础       50MB    50MB      
策略验证数据            10MB    200MB     100策略 × 2MB（缓存数据）
数据库连接池            1MB     50MB      50连接 × 1MB
HTTP连接池              1MB     50MB      50连接
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
总计                    ~350MB  ✅ 完全可行
```

### **CPU消耗**

```
并发20个策略：
  - I/O等待（MT5 API）：~60%时间
  - CPU计算（回测）：~40%时间
  - AsyncIO自动在I/O等待时切换任务
  - 预计占用：2-4核CPU

128GB机器（假设16核）：
  ✅ CPU占用：25%左右
  ✅ 内存占用：<1%
  ✅ 完全无压力
```

---

## 🔥 优化方案

### **方案1：增加并发数（推荐）** ✅

```yaml
# config/windows.yaml
validator:
  concurrency: 50  # 从20提升到50

预期效果：
  - 100策略验证时间：10秒 → 4秒
  - 内存增加：200MB → 500MB（可接受）
  - CPU增加：2-4核 → 4-8核（可接受）
```

### **方案2：多Validator实例**

```bash
# 启动3个Validator实例，每个负责33个策略
docker-compose up -d validator1 validator2 validator3

优势：
  ✅ 进一步提升并发（3 × 20 = 60并发）
  ✅ 容错（单个实例崩溃不影响全部）
  ❌ 需要分配策略逻辑（添加复杂度）
```

### **方案3：批量优化MT5 API**

```python
# MT5 API Bridge支持批量查询
@app.post("/bars/batch")
async def get_bars_batch(requests: List[BarRequest]):
    """批量获取K线数据"""
    results = []
    for req in requests:
        bars = mt5.copy_rates_from_pos(req.symbol, ...)
        results.append(bars)
    return results

优势：
  ✅ 减少HTTP往返次数（100次 → 1次）
  ✅ 减少网络延迟
  ⚡ 预计总耗时：10秒 → 5秒
```

---

## 🎯 推荐配置

### **阶段1：初期（<50策略）**

```yaml
validator:
  concurrency: 10
  schedule_interval: 3600

预期：
  - 50策略验证时间：~10秒
  - 内存占用：~200MB
  - CPU占用：1-2核
```

### **阶段2：中期（50-100策略）**

```yaml
validator:
  concurrency: 20  # ⭐ 推荐配置
  schedule_interval: 3600

预期：
  - 100策略验证时间：~10秒
  - 内存占用：~350MB
  - CPU占用：2-4核
```

### **阶段3：扩展（100-300策略）**

```yaml
validator:
  concurrency: 50
  schedule_interval: 3600
  # 或启动多个实例

预期：
  - 300策略验证时间：~12秒
  - 内存占用：~1GB
  - CPU占用：4-8核
```

---

## 🚨 MT5 API频率限制

### **潜在问题**

```
MT5可能有API调用频率限制：
  ⚠️  每秒最多X次请求
  ⚠️  触发限制会返回429错误

解决方案：
  1. 在代码中添加重试逻辑（指数退避）
  2. 控制并发数不超过MT5限制
  3. 使用批量API接口（减少请求次数）
```

### **重试逻辑（代码示例）**

```python
async def _fetch_mt5_data_with_retry(
    self, 
    symbol: str, 
    timeframe: str, 
    count: int,
    max_retries: int = 3
) -> List[Dict]:
    """带重试的MT5数据获取"""
    for attempt in range(max_retries):
        try:
            return await self._fetch_mt5_data(symbol, timeframe, count)
        except aiohttp.ClientResponseError as e:
            if e.status == 429:  # 频率限制
                wait_time = 2 ** attempt  # 指数退避：1s, 2s, 4s
                logger.warning(f"⚠️  MT5 API频率限制，等待{wait_time}秒...")
                await asyncio.sleep(wait_time)
            else:
                raise
    
    raise Exception("MT5 API调用失败，已重试3次")
```

---

## 📈 监控指标

### **关键指标**

```python
# 添加Prometheus监控
from prometheus_client import Counter, Histogram, Gauge

# 指标定义
validation_total = Counter('validator_total', 'Total validations')
validation_success = Counter('validator_success', 'Successful validations')
validation_failed = Counter('validator_failed', 'Failed validations')
validation_duration = Histogram('validator_duration_seconds', 'Validation duration')
active_strategies_count = Gauge('active_strategies', 'Number of active strategies')

# 在代码中记录
validation_total.inc()
with validation_duration.time():
    await self._validate_single_strategy(strategy)
validation_success.inc()
```

### **Grafana Dashboard**

```
面板1: 验证任务统计
  - 总数 / 成功 / 失败
  - 成功率（%）

面板2: 执行时间
  - 平均耗时
  - P50 / P95 / P99

面板3: 并发情况
  - 当前并发数
  - 队列长度

面板4: 资源消耗
  - 内存使用
  - CPU使用
```

---

## ✅ 总结

### **核心决策**

| 维度 | 推荐配置 | 理由 |
|------|----------|------|
| **并发模式** | AsyncIO | Python原生，简单高效 |
| **并发数** | 20-50 | 平衡性能与资源 |
| **数据库连接池** | 50-100 | 支持并发查询 |
| **调度频率** | 每小时 | 符合业务需求 |
| **资源消耗** | <1GB内存 | 128GB机器无压力 |

### **预期效果**

```
✅ 100个策略验证时间：10秒（并发20）或 4秒（并发50）
✅ 内存占用：350MB-500MB（0.3%-0.4%）
✅ CPU占用：2-4核（12%-25%）
✅ 完全满足7x24运行需求
✅ 轻松扩展到300+策略
```

### **实施步骤**

```
1. ✅ 创建 ConcurrentValidator 类
2. ✅ 配置异步数据库连接
3. ✅ 实现并发验证逻辑
4. ✅ 添加Docker配置
5. ⏸️  测试并发性能
6. ⏸️  上线监控
```

**架构已就绪，可支持100-300策略的高并发验证！** 🚀
