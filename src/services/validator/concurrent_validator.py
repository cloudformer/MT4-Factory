"""并发策略验证器 - 支持100+策略同时验证"""
import asyncio
from datetime import datetime
from typing import List, Dict, Optional
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import select, update
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from src.common.config import settings
from src.common.logger import get_logger
from src.common.mt5 import UnifiedMT5Client
from src.common.models.strategy import Strategy
from src.services.strategy.service.backtester import SimpleBacktester
from .data_sources import MultiDataSource

logger = get_logger(__name__)

# FastAPI应用（提供HTTP API）
app = FastAPI(title="Validator Service", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ConcurrentValidator:
    """
    并发策略验证器

    功能：
    1. 每小时自动验证所有Active策略
    2. AsyncIO并发执行（默认20个并发）
    3. 从MT5获取最新数据进行回测
    4. 更新策略验证结果到数据库

    用途：
    - 7x24运行在Windows本地（容器）
    - 或运行在云端（容器）
    - 通过UnifiedMT5Client访问MT5（本地或远程）
    """

    def __init__(self, concurrency: int = 20):
        """
        初始化并发验证器

        Args:
            concurrency: 并发数（推荐20-50）
        """
        self.concurrency = concurrency
        self.scheduler = AsyncIOScheduler()

        # 异步数据库引擎
        db_config = settings.database

        # 判断数据库类型
        if 'url' in db_config:
            # SQLite模式
            db_url = db_config['url'].replace('sqlite:///', 'sqlite+aiosqlite:///')
        else:
            # PostgreSQL模式
            db_url = (
                f"postgresql+asyncpg://{db_config['user']}:{db_config['password']}"
                f"@{db_config['host']}:{db_config['port']}/{db_config['database']}"
            )

        self.engine = create_async_engine(
            db_url,
            pool_size=50,      # 连接池大小
            max_overflow=50,   # 最大溢出连接
            echo=False
        )

        self.AsyncSessionLocal = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )

        # MT5客户端配置
        mt5_config = settings.mt5
        self.mt5_config = mt5_config

        # 创建MT5客户端（会在运行时创建，因为可能需要在不同的线程中）
        self.mt5_client = None

        # 多数据源管理器
        self.data_source = MultiDataSource()
        logger.info(f"📊 数据源: {self.data_source.get_available_sources()}")

        # 统计信息
        self.stats = {
            'total_validations': 0,
            'successful_validations': 0,
            'failed_validations': 0,
            'last_run_time': None,
            'last_run_duration': 0
        }

    def _create_mt5_client(self) -> UnifiedMT5Client:
        """创建MT5客户端"""
        return UnifiedMT5Client(
            host=self.mt5_config.get("host", "localhost"),
            port=self.mt5_config.get("port", 9090),
            login=self.mt5_config.get("login"),
            password=self.mt5_config.get("password"),
            server=self.mt5_config.get("server"),
            api_key=self.mt5_config.get("api_key"),
            timeout=self.mt5_config.get("timeout", 10)
        )

    async def start(self):
        """启动Validator服务"""
        logger.info("=" * 60)
        logger.info(f"🚀 启动Validator服务")
        logger.info(f"   并发数: {self.concurrency}")
        logger.info(f"   MT5: {self.mt5_config.get('host')}:{self.mt5_config.get('port', 'N/A')}")
        logger.info("=" * 60)

        # 测试MT5连接
        await self._test_mt5_connection()

        # 立即执行一次
        logger.info("🔄 执行首次验证...")
        await self.validate_all_strategies()

        # 定时任务：根据配置执行
        schedule_interval = settings.validator.get("schedule_interval", 3600)

        self.scheduler.add_job(
            self.validate_all_strategies,
            trigger='interval',
            seconds=schedule_interval,
            id='validate_strategies',
            name='验证所有Active策略'
        )

        self.scheduler.start()
        logger.info(f"✅ 定时任务已启动（每{schedule_interval}秒执行一次）")

        # 保持运行
        try:
            while True:
                await asyncio.sleep(3600)
        except (KeyboardInterrupt, asyncio.CancelledError):
            logger.info("收到停止信号")
            await self.shutdown()

    async def _test_mt5_connection(self):
        """测试MT5连接"""
        try:
            client = self._create_mt5_client()
            if client.initialize():
                logger.info("✅ MT5连接测试成功")

                # 测试获取数据
                df = client.get_bars("EURUSD", "H1", 10)
                if not df.empty:
                    logger.info(f"✅ MT5数据获取成功（测试获取{len(df)}根K线）")
                else:
                    logger.warning("⚠️  MT5数据为空，请检查品种和连接")

                client.shutdown()
            else:
                logger.error("❌ MT5连接失败")
                raise RuntimeError("MT5连接失败")
        except Exception as e:
            logger.error(f"❌ MT5连接测试失败: {str(e)}")
            raise

    async def shutdown(self):
        """优雅关闭"""
        logger.info("正在关闭Validator服务...")

        if self.scheduler.running:
            self.scheduler.shutdown()

        await self.engine.dispose()

        logger.info("✅ Validator已关闭")

    async def validate_all_strategies(self):
        """验证所有Active策略（并发执行）"""
        start_time = datetime.now()
        logger.info("=" * 60)
        logger.info(f"🔍 开始批量验证 - {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 60)

        try:
            # 1. 获取所有Active策略
            strategies = await self._get_active_strategies()
            total = len(strategies)

            if total == 0:
                logger.warning("⚠️  未找到Active策略")
                return

            logger.info(f"📊 找到 {total} 个Active策略，开始并发验证（并发数：{self.concurrency}）...")

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
            failed_count = sum(1 for r in results if isinstance(r, Exception) or r is False)

            elapsed = (datetime.now() - start_time).total_seconds()

            # 5. 更新统计信息
            self.stats['total_validations'] += total
            self.stats['successful_validations'] += success_count
            self.stats['failed_validations'] += failed_count
            self.stats['last_run_time'] = start_time
            self.stats['last_run_duration'] = elapsed

            logger.info("=" * 60)
            logger.info(f"✅ 批量验证完成")
            logger.info(f"   总计: {total} | 成功: {success_count} | 失败: {failed_count}")
            logger.info(f"   耗时: {elapsed:.2f}秒 | 平均: {elapsed/total:.2f}秒/策略")
            logger.info("=" * 60)

        except Exception as e:
            logger.error(f"❌ 批量验证失败: {str(e)}", exc_info=True)

    async def _validate_strategy_with_semaphore(
        self,
        strategy: Strategy,
        semaphore: asyncio.Semaphore
    ) -> bool:
        """使用信号量控制并发的策略验证"""
        async with semaphore:
            return await self._validate_single_strategy(strategy)

    async def _validate_single_strategy(self, strategy: Strategy) -> bool:
        """
        验证单个策略（核心逻辑）

        流程：
        1. 从MT5获取最新K线数据
        2. 运行回测
        3. 更新数据库
        """
        try:
            strategy_id = strategy.id
            symbol = strategy.params.get("symbol", "EURUSD")
            timeframe = strategy.params.get("timeframe", "H1")

            logger.debug(f"🔄 [{strategy_id}] {symbol} {timeframe} 验证中...")

            # 步骤1: 获取MT5最新数据
            # 注意：MT5客户端操作可能是同步的，使用to_thread
            bars_df = await asyncio.to_thread(
                self._fetch_mt5_data,
                symbol,
                timeframe,
                count=500  # 获取500根K线用于回测
            )

            if bars_df is None or bars_df.empty:
                logger.warning(f"⚠️  [{strategy_id}] 无法获取MT5数据")
                return False

            # 步骤2: 运行回测（CPU密集，使用to_thread）
            result = await asyncio.to_thread(
                self._run_backtest,
                strategy,
                bars_df
            )

            # 步骤3: 更新数据库
            await self._update_validation_result(strategy_id, result)

            logger.info(
                f"✅ [{strategy_id}] 验证完成 - "
                f"胜率: {result['win_rate']*100:.1f}% | "
                f"总交易: {result['total_trades']} | "
                f"收益: {result['total_return']*100:+.1f}%"
            )
            return True

        except Exception as e:
            logger.error(f"❌ [{strategy.id}] 验证失败: {str(e)}", exc_info=True)
            return False

    def _fetch_mt5_data(self, symbol: str, timeframe: str, count: int):
        """
        获取MT5数据（同步方法）

        注意：此方法在线程池中执行
        """
        try:
            client = self._create_mt5_client()

            # 初始化
            if not client.initialize():
                logger.error("MT5初始化失败")
                return None

            # 获取数据
            df = client.get_bars(symbol, timeframe, count)

            # 关闭
            client.shutdown()

            return df

        except Exception as e:
            logger.error(f"获取MT5数据失败: {str(e)}")
            return None

    def _run_backtest(self, strategy: Strategy, bars_df) -> Dict:
        """
        运行回测（同步方法）

        注意：此方法在线程池中执行
        """
        try:
            # 使用现有的SimpleBacktester
            initial_balance = settings.validator.get("initial_balance", 100)
            backtester = SimpleBacktester(initial_balance=initial_balance)

            # 运行回测
            result = backtester.run(strategy.code, bars_df)

            return result

        except Exception as e:
            logger.error(f"回测执行失败: {str(e)}")
            # 返回默认结果
            return {
                'total_return': 0.0,
                'win_rate': 0.0,
                'total_trades': 0,
                'sharpe_ratio': 0.0,
                'max_drawdown': 0.0,
                'profit_factor': 0.0
            }

    async def _get_active_strategies(self) -> List[Strategy]:
        """获取所有Active策略"""
        async with self.AsyncSessionLocal() as session:
            stmt = select(Strategy).where(Strategy.status == "active")
            result = await session.execute(stmt)
            strategies = result.scalars().all()

            # 需要将ORM对象的属性加载到内存（避免detached状态）
            loaded_strategies = []
            for s in strategies:
                # 访问所有需要的属性，触发加载
                _ = s.id, s.code, s.params, s.status
                loaded_strategies.append(s)

            return loaded_strategies

    async def _update_validation_result(self, strategy_id: str, result: Dict):
        """更新验证结果到数据库"""
        try:
            async with self.AsyncSessionLocal() as session:
                # 更新策略验证字段
                stmt = (
                    update(Strategy)
                    .where(Strategy.id == strategy_id)
                    .values(
                        last_validation_time=datetime.now(),
                        validation_win_rate=result.get('win_rate', 0.0),
                        validation_total_return=result.get('total_return', 0.0),
                        validation_total_trades=result.get('total_trades', 0),
                        validation_sharpe_ratio=result.get('sharpe_ratio', 0.0),
                        validation_max_drawdown=result.get('max_drawdown', 0.0),
                        validation_profit_factor=result.get('profit_factor', 0.0)
                    )
                )

                await session.execute(stmt)
                await session.commit()

        except Exception as e:
            logger.error(f"更新验证结果失败: {str(e)}", exc_info=True)

    def get_stats(self) -> Dict:
        """获取统计信息"""
        return self.stats.copy()


# ==================== 全局Validator实例 ====================
validator_instance: Optional[ConcurrentValidator] = None


# ==================== HTTP API端点 ====================

@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "service": "validator",
        "status": "healthy",
        "stats": validator_instance.get_stats() if validator_instance else {}
    }


@app.post("/api/validate/trigger")
async def trigger_validation():
    """
    手动触发验证（立即执行）

    用途：
    - Dashboard UI点击按钮立即验证
    - 不需要等待自动调度（每小时）
    """
    if validator_instance is None:
        raise HTTPException(status_code=503, detail="Validator服务未就绪")

    logger.info("🔘 收到手动触发验证请求")

    # 异步触发验证（不阻塞HTTP响应）
    asyncio.create_task(validator_instance.validate_all_strategies())

    return {
        "success": True,
        "message": "验证任务已触发（后台执行）",
        "tip": "验证完成后刷新页面查看结果"
    }


@app.post("/api/validate/strategy/{strategy_id}")
async def validate_single_strategy_api(strategy_id: str):
    """
    验证单个策略（立即执行）

    Args:
        strategy_id: 策略ID
    """
    if validator_instance is None:
        raise HTTPException(status_code=503, detail="Validator服务未就绪")

    logger.info(f"🔘 收到单策略验证请求: {strategy_id}")

    # 获取策略
    async with validator_instance.AsyncSessionLocal() as session:
        stmt = select(Strategy).where(Strategy.id == strategy_id)
        result = await session.execute(stmt)
        strategy = result.scalar_one_or_none()

        if not strategy:
            raise HTTPException(status_code=404, detail=f"策略不存在: {strategy_id}")

        if strategy.status != "active":
            raise HTTPException(
                status_code=400,
                detail=f"只能验证Active策略，当前状态: {strategy.status}"
            )

    # 异步触发验证
    async def validate_task():
        semaphore = asyncio.Semaphore(1)
        await validator_instance._validate_strategy_with_semaphore(strategy, semaphore)

    asyncio.create_task(validate_task())

    return {
        "success": True,
        "message": f"策略 {strategy_id} 验证任务已触发",
        "strategy_name": strategy.name
    }


@app.get("/api/stats")
async def get_validator_stats():
    """获取Validator统计信息"""
    if validator_instance is None:
        raise HTTPException(status_code=503, detail="Validator服务未就绪")

    return validator_instance.get_stats()


@app.get("/api/data_sources")
async def get_data_sources():
    """
    获取数据源信息

    返回：
    - enabled_sources: 启用的数据源列表
    - available_count: 可用数据源数量
    """
    if validator_instance is None:
        raise HTTPException(status_code=503, detail="Validator服务未就绪")

    return validator_instance.data_source.get_stats()


@app.get("/api/data_sources/test")
async def test_data_sources(
    symbol: str = "EURUSD",
    timeframe: str = "H1",
    count: int = 100
):
    """
    测试数据源

    查询指定品种和周期的K线数据
    """
    if validator_instance is None:
        raise HTTPException(status_code=503, detail="Validator服务未就绪")

    try:
        bars = validator_instance.data_source.get_bars(symbol, timeframe, count)

        return {
            "success": True,
            "symbol": symbol,
            "timeframe": timeframe,
            "requested_count": count,
            "actual_count": len(bars),
            "first_bar": bars[0] if bars else None,
            "last_bar": bars[-1] if bars else None,
            "data_source": validator_instance.data_source.get_available_sources()
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"数据源测试失败: {str(e)}"
        )


# ==================== 启动入口 ====================

async def start_validator_service():
    """启动Validator后台服务"""
    global validator_instance

    concurrency = settings.validator.get("concurrency", 20)
    logger.info(f"Validator配置: 并发数={concurrency}")

    validator_instance = ConcurrentValidator(concurrency=concurrency)
    await validator_instance.start()


async def main():
    """主函数：同时运行FastAPI和Validator"""
    import threading

    # 启动FastAPI服务（在新线程）
    def run_api():
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8080,  # Validator API端口
            log_level="info"
        )

    api_thread = threading.Thread(target=run_api, daemon=True)
    api_thread.start()

    logger.info("🌐 Validator HTTP API已启动: http://0.0.0.0:8080")

    # 等待1秒让API启动
    await asyncio.sleep(1)

    # 启动Validator服务（主线程）
    await start_validator_service()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Validator已停止")
