#!/usr/bin/env python3
"""
Windows Worker历史数据下载
用法: python scripts/tools/update_historical_data.py --days 7
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import argparse
from datetime import datetime, timedelta
import requests
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.common.config.settings import settings
from src.common.models.historical_bar import HistoricalBar


def download_historical_data(days=7):
    """从MT5下载历史数据"""
    print(f"\n{'='*60}")
    print(f"历史数据下载 - 最近{days}天")
    print(f"{'='*60}\n")

    # 连接数据库
    db_config = settings.database
    if db_config.get('type') == 'sqlite':
        db_url = f"sqlite:///{db_config['sqlite_path']}"
    else:
        db_url = f"postgresql+psycopg2://{db_config['user']}:{db_config['password']}@{db_config['host']}:{db_config['port']}/{db_config['database']}"

    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)

    # MT5 Bridge地址
    mt5_url = "http://localhost:9090"

    # 默认品种和周期
    symbols = ["EURUSD", "GBPUSD", "USDJPY"]
    timeframes = ["H1", "H4", "D1"]

    print(f"数据源: {mt5_url}")
    print(f"品种: {', '.join(symbols)}")
    print(f"周期: {', '.join(timeframes)}")
    print(f"\n开始下载...\n")

    total_bars = 0

    for symbol in symbols:
        for timeframe in timeframes:
            try:
                print(f"[{symbol}] {timeframe} ...", end=" ", flush=True)

                # 从MT5获取数据
                response = requests.get(
                    f"{mt5_url}/bars",
                    params={
                        "symbol": symbol,
                        "timeframe": timeframe,
                        "count": days * 24  # 估算K线数量
                    },
                    timeout=30
                )

                if response.status_code != 200:
                    print(f"❌ 失败 ({response.status_code})")
                    continue

                data = response.json()
                bars = data.get('bars', [])

                if not bars:
                    print("⚠️  无数据")
                    continue

                # 保存到数据库
                session = Session()
                count = 0

                for bar in bars:
                    bar_time = datetime.fromtimestamp(bar['time'])

                    # 检查是否已存在
                    existing = session.query(HistoricalBar).filter(
                        HistoricalBar.symbol == symbol,
                        HistoricalBar.timeframe == timeframe,
                        HistoricalBar.time == bar_time
                    ).first()

                    if not existing:
                        new_bar = HistoricalBar(
                            symbol=symbol,
                            timeframe=timeframe,
                            time=bar_time,
                            open=bar['open'],
                            high=bar['high'],
                            low=bar['low'],
                            close=bar['close'],
                            volume=bar.get('tick_volume', 0)
                        )
                        session.add(new_bar)
                        count += 1

                session.commit()
                session.close()

                print(f"✅ {len(bars)}根 (新增{count})")
                total_bars += count

            except Exception as e:
                print(f"❌ 错误: {e}")
                continue

    print(f"\n{'='*60}")
    print(f"下载完成！共新增 {total_bars} 根K线")
    print(f"{'='*60}\n")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='下载历史数据')
    parser.add_argument('--days', type=int, default=7, help='下载最近N天')
    args = parser.parse_args()

    try:
        download_historical_data(days=args.days)
    except Exception as e:
        print(f"\n❌ 下载失败: {e}\n")
        sys.exit(1)
