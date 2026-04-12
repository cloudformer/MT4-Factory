"""Validator数据源 - 多数据源支持"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any
from datetime import datetime, timedelta
import random

from src.common.config.settings import settings
from src.common.models.historical_bar import HistoricalBar
from src.common.database.connection import db
from src.common.logger import get_logger

logger = get_logger(__name__)


class DataSource(ABC):
    """数据源抽象基类"""

    @abstractmethod
    def get_bars(
        self,
        symbol: str,
        timeframe: str,
        count: int = 500
    ) -> List[Dict[str, Any]]:
        """
        获取K线数据

        Args:
            symbol: 交易品种
            timeframe: 时间周期
            count: 数量

        Returns:
            K线数据列表
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """检查数据源是否可用"""
        pass


class MockDataSource(DataSource):
    """
    模拟数据源

    生成随机K线数据，用于开发测试
    """

    def __init__(self):
        self.name = "Mock"
        logger.info("📊 Mock数据源初始化")

    def get_bars(
        self,
        symbol: str,
        timeframe: str,
        count: int = 500
    ) -> List[Dict[str, Any]]:
        """生成模拟K线数据"""
        bars = []
        base_price = 1.1000 if symbol == "EURUSD" else 1.2500

        for i in range(count):
            # 生成随机价格波动
            change = random.uniform(-0.0020, 0.0020)
            open_price = base_price + change
            high_price = open_price + random.uniform(0, 0.0010)
            low_price = open_price - random.uniform(0, 0.0010)
            close_price = random.uniform(low_price, high_price)

            bars.append({
                'time': int((datetime.now() - timedelta(minutes=5 * (count - i))).timestamp()),
                'open': round(open_price, 5),
                'high': round(high_price, 5),
                'low': round(low_price, 5),
                'close': round(close_price, 5),
                'tick_volume': random.randint(100, 500)
            })

            base_price = close_price

        logger.debug(f"✅ Mock数据源生成 {count} 根K线 | {symbol} {timeframe}")
        return bars

    def is_available(self) -> bool:
        """Mock数据源始终可用"""
        return True


class DatabaseDataSource(DataSource):
    """
    历史数据库数据源

    从 historical_bars 表读取历史K线
    """

    def __init__(self):
        self.name = "Database"
        logger.info("📊 历史数据库数据源初始化")

    def get_bars(
        self,
        symbol: str,
        timeframe: str,
        count: int = 3000
    ) -> List[Dict[str, Any]]:
        """从数据库查询历史K线"""
        try:
            with db.session_scope() as session:
                # 查询最近N根K线
                bars_orm = session.query(HistoricalBar).filter(
                    HistoricalBar.symbol == symbol,
                    HistoricalBar.timeframe == timeframe
                ).order_by(HistoricalBar.time.desc()).limit(count).all()

                if not bars_orm:
                    logger.warning(f"⚠️  数据库无 {symbol} {timeframe} 数据")
                    return []

                # 转换为字典列表（时间倒序）
                bars = []
                for bar in reversed(bars_orm):  # 反转为时间正序
                    bars.append({
                        'time': int(bar.time.timestamp()),
                        'open': float(bar.open),
                        'high': float(bar.high),
                        'low': float(bar.low),
                        'close': float(bar.close),
                        'tick_volume': bar.volume or 0
                    })

                logger.info(f"✅ 数据库查询到 {len(bars)} 根K线 | {symbol} {timeframe}")
                return bars

        except Exception as e:
            logger.error(f"❌ 数据库查询失败: {str(e)}")
            return []

    def is_available(self) -> bool:
        """检查数据库连接"""
        try:
            with db.session_scope() as session:
                # 简单查询测试连接
                session.execute("SELECT 1")
                return True
        except:
            return False


class RealtimeDataSource(DataSource):
    """
    实时MT5数据源

    从MT5实时获取最新K线数据
    """

    def __init__(self, mt5_host_id: str = None):
        self.name = "Realtime"
        self.mt5_client = None
        self.mt5_host_id = mt5_host_id
        logger.info(f"📊 实时MT5数据源初始化: host_id={mt5_host_id}")

        # 尝试连接MT5
        try:
            from src.common.mt5 import UnifiedMT5Client
            from src.common.models.mt5_host import MT5Host

            # 从数据库读取MT5主机配置
            host_config = None
            with db.session_scope() as session:
                if mt5_host_id:
                    # 通过ID查询
                    host_config = session.query(MT5Host).filter(
                        MT5Host.id == mt5_host_id,
                        MT5Host.enabled == True
                    ).first()
                else:
                    # 如果没有指定ID，使用第一个启用的demo主机
                    host_config = session.query(MT5Host).filter(
                        MT5Host.host_type == 'demo',
                        MT5Host.enabled == True
                    ).order_by(MT5Host.weight.desc()).first()

            if not host_config:
                logger.warning(f"⚠️  数据库中未找到可用的MT5主机配置")
                return

            # 尝试连接（即使在Mac上也会尝试）
            logger.info(f"🔌 尝试连接MT5: {host_config.name} ({host_config.host}:{host_config.port})")
            self.mt5_client = UnifiedMT5Client(
                host=host_config.host,
                port=host_config.port,
                api_key=host_config.api_key,
                timeout=host_config.timeout
            )
            logger.info(f"✅ MT5连接成功: {host_config.name} ({host_config.host})")

        except Exception as e:
            logger.warning(f"⚠️  MT5连接失败: {str(e)} | 将使用其他数据源")
            self.mt5_client = None

    def get_bars(
        self,
        symbol: str,
        timeframe: str,
        count: int = 500
    ) -> List[Dict[str, Any]]:
        """从MT5获取实时K线"""
        if not self.mt5_client:
            logger.warning("⚠️  MT5客户端未连接")
            return []

        try:
            result = self.mt5_client.get_bars(
                symbol=symbol,
                timeframe=timeframe,
                count=count
            )

            bars = result.get('bars', [])
            logger.info(f"✅ MT5获取 {len(bars)} 根K线 | {symbol} {timeframe}")
            return bars

        except Exception as e:
            logger.error(f"❌ MT5获取数据失败: {str(e)}")
            return []

    def is_available(self) -> bool:
        """检查MT5连接"""
        return self.mt5_client is not None


class MultiDataSource:
    """
    多数据源管理器

    根据配置权重选择数据源
    """

    def __init__(self):
        # 从配置读取数据源配置
        data_sources_config = settings.get('validator', {}).get('data_sources', [])

        # 解析配置并初始化数据源
        self.enabled_sources = []

        for config in data_sources_config:
            source_type = config.get('type')

            if not config.get('enabled', False):
                continue

            # 根据类型创建数据源实例
            source = None
            if source_type == 'mock':
                source = MockDataSource()
            elif source_type == 'database':
                source = DatabaseDataSource()
            elif source_type == 'realtime':
                # Realtime数据源需要传入mt5_host配置（数据库中的host_id）
                mt5_host_id = config.get('mt5_host')
                source = RealtimeDataSource(mt5_host_id=mt5_host_id)

            if source:
                self.enabled_sources.append({
                    'type': source_type,
                    'weight': config.get('weight', 0.33),
                    'source': source
                })

        # 如果没有配置，默认使用Mock
        if not self.enabled_sources:
            logger.warning("⚠️  未配置数据源，使用Mock数据源")
            self.enabled_sources = [{
                'type': 'mock',
                'weight': 1.0,
                'source': MockDataSource()
            }]

        logger.info(f"📊 数据源管理器初始化: {[s['type'] for s in self.enabled_sources]}")

    def get_bars(
        self,
        symbol: str,
        timeframe: str,
        count: int = 500,
        preferred_source: str = None
    ) -> List[Dict[str, Any]]:
        """
        获取K线数据

        Args:
            symbol: 交易品种
            timeframe: 时间周期
            count: 数量
            preferred_source: 首选数据源 ('mock', 'database', 'realtime')

        Returns:
            K线数据列表
        """
        # 如果指定了首选数据源
        if preferred_source:
            for s in self.enabled_sources:
                if s['type'] == preferred_source and s['source'].is_available():
                    logger.info(f"🎯 使用指定数据源: {preferred_source}")
                    return s['source'].get_bars(symbol, timeframe, count)

        # 按权重选择数据源（优先选择可用且权重高的）
        available_sources = [
            s for s in self.enabled_sources
            if s['source'].is_available()
        ]

        if not available_sources:
            logger.error("❌ 没有可用的数据源")
            return []

        # 按权重排序，选择权重最高的
        available_sources.sort(key=lambda x: x['weight'], reverse=True)
        selected = available_sources[0]

        logger.info(f"🎯 自动选择数据源: {selected['type']} (权重: {selected['weight']})")
        return selected['source'].get_bars(symbol, timeframe, count)

    def get_available_sources(self) -> List[str]:
        """获取当前可用的数据源列表"""
        return [
            s['type']
            for s in self.enabled_sources
            if s['source'].is_available()
        ]

    def get_stats(self) -> Dict[str, Any]:
        """获取数据源统计信息"""
        return {
            'enabled_sources': [
                {
                    'type': s['type'],
                    'weight': s['weight'],
                    'available': s['source'].is_available()
                }
                for s in self.enabled_sources
            ],
            'available_count': len(self.get_available_sources())
        }
