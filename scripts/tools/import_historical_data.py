#!/usr/bin/env python3
"""
历史K线数据导入工具

支持三个阶段：
- Phase 1: 3品种 × 3周期 × 2年 = 67K行 (15MB)
- Phase 2: 10品种 × 5周期 × 5年 = 3.2M行 (500MB)
- Phase 3: 30品种 × 7周期 × 10年 = 50M行 (3-4GB)

Usage:
    python scripts/tools/import_historical_data.py --phase 1
    python scripts/tools/import_historical_data.py --phase 2
    python scripts/tools/import_historical_data.py --symbols EURUSD,GBPUSD --timeframes H1,H4 --years 2
"""
import sys
import os
import argparse
from datetime import datetime, timedelta
from typing import List, Dict
import time

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.common.database.connection import db
from src.common.models.historical_bar import HistoricalBar
from src.common.mt5.unified_client import UnifiedMT5Client
from src.common.config.settings import settings


# Phase预设配置
PHASE_CONFIGS = {
    '1': {
        'name': 'Phase 1 - 保守起步',
        'symbols': ['EURUSD', 'GBPUSD', 'USDJPY'],
        'timeframes': ['H1', 'H4', 'D1'],
        'years': 2,
        'expected_rows': 67890,
        'expected_size': '15MB'
    },
    '2': {
        'name': 'Phase 2 - 中等扩展',
        'symbols': ['EURUSD', 'GBPUSD', 'USDJPY', 'AUDUSD', 'NZDUSD',
                    'USDCAD', 'USDCHF', 'EURJPY', 'GBPJPY', 'AUDJPY'],
        'timeframes': ['M15', 'M30', 'H1', 'H4', 'D1'],
        'years': 5,
        'expected_rows': 3193750,
        'expected_size': '500MB'
    },
    '3': {
        'name': 'Phase 3 - 大规模',
        'symbols': [
            # 主流货币对
            'EURUSD', 'GBPUSD', 'USDJPY', 'AUDUSD', 'NZDUSD', 'USDCAD', 'USDCHF',
            # 交叉盘
            'EURJPY', 'GBPJPY', 'AUDJPY', 'EURAUD', 'EURGBP', 'EURCHF', 'GBPAUD',
            'GBPCHF', 'AUDCAD', 'AUDCHF', 'NZDJPY', 'CADJPY', 'CHFJPY',
            # 贵金属
            'XAUUSD', 'XAGUSD',
            # 指数
            'US30', 'US100', 'US500', 'UK100', 'GER40', 'FRA40', 'JPN225', 'AUS200'
        ],
        'timeframes': ['M5', 'M15', 'M30', 'H1', 'H4', 'D1', 'W1'],
        'years': 10,
        'expected_rows': 50714100,
        'expected_size': '3-4GB'
    }
}


class HistoricalDataImporter:
    """历史数据导入器"""

    def __init__(self, mt5_config: Dict = None):
        """初始化导入器"""
        self.mt5_config = mt5_config or settings.mt5
        self.mt5_client = None
        self.stats = {
            'total_bars': 0,
            'successful_symbols': 0,
            'failed_symbols': 0,
            'start_time': None,
            'end_time': None
        }

    def connect_mt5(self):
        """连接MT5"""
        print("🔌 连接MT5...")
        try:
            self.mt5_client = UnifiedMT5Client(
                host=self.mt5_config.get('host', 'localhost'),
                port=self.mt5_config.get('port', 9090),
                api_key=self.mt5_config.get('api_key'),
                timeout=self.mt5_config.get('timeout', 10)
            )
            print("✅ MT5连接成功")
            return True
        except Exception as e:
            print(f"❌ MT5连接失败: {e}")
            return False

    def import_phase(self, phase: str):
        """导入指定Phase的数据"""
        config = PHASE_CONFIGS.get(phase)
        if not config:
            print(f"❌ 无效的Phase: {phase}")
            return False

        print(f"\n{'='*60}")
        print(f"📦 {config['name']}")
        print(f"{'='*60}")
        print(f"品种数: {len(config['symbols'])}")
        print(f"周期数: {len(config['timeframes'])}")
        print(f"历史年数: {config['years']}")
        print(f"预计数据量: {config['expected_rows']:,} 行 ({config['expected_size']})")
        print(f"{'='*60}\n")

        return self.import_data(
            symbols=config['symbols'],
            timeframes=config['timeframes'],
            years=config['years']
        )

    def import_data(self, symbols: List[str], timeframes: List[str], years: int):
        """导入数据"""
        self.stats['start_time'] = time.time()

        # 连接MT5
        if not self.connect_mt5():
            return False

        # 计算时间范围
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=years * 365)

        print(f"⏰ 时间范围: {start_date.date()} 到 {end_date.date()}\n")

        # 遍历所有品种
        for i, symbol in enumerate(symbols, 1):
            print(f"\n[{i}/{len(symbols)}] 导入 {symbol}...")

            try:
                self._import_symbol(symbol, timeframes, start_date, end_date)
                self.stats['successful_symbols'] += 1
                print(f"✅ {symbol} 导入完成")
            except Exception as e:
                self.stats['failed_symbols'] += 1
                print(f"❌ {symbol} 导入失败: {e}")

        self.stats['end_time'] = time.time()
        self._print_summary()

        return True

    def _import_symbol(self, symbol: str, timeframes: List[str], start_date: datetime, end_date: datetime):
        """导入单个品种的所有周期数据"""
        for timeframe in timeframes:
            bars_count = self._estimate_bars_count(timeframe, start_date, end_date)
            print(f"  - {timeframe}: 预计 {bars_count:,} 根...")

            # 从MT5获取数据
            bars = self._fetch_bars_from_mt5(symbol, timeframe, bars_count)

            if not bars:
                print(f"    ⚠️ 无数据")
                continue

            # 写入数据库
            self._save_bars_to_db(symbol, timeframe, bars)
            self.stats['total_bars'] += len(bars)
            print(f"    ✅ 导入 {len(bars):,} 根")

    def _fetch_bars_from_mt5(self, symbol: str, timeframe: str, count: int) -> List[Dict]:
        """从MT5获取K线数据"""
        try:
            result = self.mt5_client.get_bars(
                symbol=symbol,
                timeframe=timeframe,
                count=min(count, 100000)  # MT5单次最多10万根
            )
            return result.get('bars', [])
        except Exception as e:
            print(f"    ❌ MT5获取失败: {e}")
            return []

    def _save_bars_to_db(self, symbol: str, timeframe: str, bars: List[Dict]):
        """批量保存K线到数据库"""
        with db.session_scope() as session:
            # 批量插入（每次1000根）
            batch_size = 1000
            for i in range(0, len(bars), batch_size):
                batch = bars[i:i+batch_size]

                bar_objects = [
                    {
                        'symbol': symbol,
                        'timeframe': timeframe,
                        'time': datetime.fromtimestamp(bar['time']),
                        'open': bar['open'],
                        'high': bar['high'],
                        'low': bar['low'],
                        'close': bar['close'],
                        'volume': bar.get('tick_volume', 0)
                    }
                    for bar in batch
                ]

                session.bulk_insert_mappings(HistoricalBar, bar_objects)

    def _estimate_bars_count(self, timeframe: str, start_date: datetime, end_date: datetime) -> int:
        """估算K线数量"""
        days = (end_date - start_date).days

        bars_per_day = {
            'M5': 288,
            'M15': 96,
            'M30': 48,
            'H1': 24,
            'H4': 6,
            'D1': 1,
            'W1': 0.14
        }

        per_day = bars_per_day.get(timeframe, 24)
        return int(days * per_day)

    def _print_summary(self):
        """打印导入摘要"""
        duration = self.stats['end_time'] - self.stats['start_time']

        print(f"\n{'='*60}")
        print(f"📊 导入完成")
        print(f"{'='*60}")
        print(f"✅ 成功品种: {self.stats['successful_symbols']}")
        print(f"❌ 失败品种: {self.stats['failed_symbols']}")
        print(f"📈 总K线数: {self.stats['total_bars']:,} 根")
        print(f"⏱️  总耗时: {duration:.1f} 秒 ({duration/60:.1f} 分钟)")
        print(f"{'='*60}\n")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='历史K线数据导入工具')
    parser.add_argument('--phase', type=str, choices=['1', '2', '3'],
                        help='Phase阶段 (1/2/3)')
    parser.add_argument('--symbols', type=str,
                        help='品种列表（逗号分隔），如: EURUSD,GBPUSD')
    parser.add_argument('--timeframes', type=str,
                        help='周期列表（逗号分隔），如: H1,H4,D1')
    parser.add_argument('--years', type=int,
                        help='历史年数')

    args = parser.parse_args()

    importer = HistoricalDataImporter()

    # Phase模式
    if args.phase:
        importer.import_phase(args.phase)
    # 自定义模式
    elif args.symbols and args.timeframes and args.years:
        symbols = args.symbols.split(',')
        timeframes = args.timeframes.split(',')
        importer.import_data(symbols, timeframes, args.years)
    else:
        parser.print_help()
        print("\n示例：")
        print("  python scripts/tools/import_historical_data.py --phase 1")
        print("  python scripts/tools/import_historical_data.py --symbols EURUSD,GBPUSD --timeframes H1,H4 --years 2")


if __name__ == '__main__':
    main()
