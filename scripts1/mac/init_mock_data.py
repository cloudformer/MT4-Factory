#!/usr/bin/env python3
"""
Mac环境 - 初始化SQLite数据库假数据
在数据库中插入Mock数据，供Dashboard显示
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# 设置环境变量
os.environ['DEVICE'] = 'mac'

from datetime import datetime, timedelta
import random
from src.common.database.connection import db
from src.common.database.base import Base
from src.common.models.strategy import Strategy, StrategyStatus
from src.common.models.signal import Signal, Direction, SignalStatus
from src.common.models.trade import Trade
from src.common.models.account import Account


def init_mock_data():
    """初始化Mock数据到数据库"""

    print("=" * 50)
    print("  Mac环境 - 初始化数据库Mock数据")
    print("=" * 50)
    print()

    # 1. 创建表结构
    print("[1/5] 创建数据库表结构...")
    Base.metadata.create_all(db.engine)
    print("  ✓ 表结构创建完成")
    print()

    with db.session_scope() as session:
        # 2. 清空旧数据
        print("[2/5] 清空旧数据...")
        session.query(Trade).delete()
        session.query(Signal).delete()
        session.query(Strategy).delete()
        session.query(Account).delete()
        session.commit()
        print("  ✓ 旧数据已清空")
        print()

        # 3. 插入Account数据
        print("[3/5] 插入账户数据...")
        accounts = [
            Account(
                id="ACC_001",
                login="8012345678",
                server="ICMarkets-Live",
                password="dummy_pass",
                account_type="real",
                status="active"
            ),
            Account(
                id="ACC_002",
                login="5049130509",
                server="MetaQuotes-Demo",
                password="dummy_pass",
                account_type="demo",
                status="active"
            )
        ]
        session.add_all(accounts)
        session.commit()
        print(f"  ✓ 插入 {len(accounts)} 个账户")
        print()

        # 4. 插入Strategy数据
        print("[4/5] 插入策略数据...")
        strategies = []
        statuses = [StrategyStatus.ACTIVE, StrategyStatus.ACTIVE, StrategyStatus.ACTIVE,
                   StrategyStatus.CANDIDATE, StrategyStatus.ARCHIVED]

        for i in range(1, 16):
            status = random.choice(statuses)
            symbol = random.choice(["EURUSD", "GBPUSD", "USDJPY"])
            timeframe = random.choice(["M15", "H1", "H4"])
            rec_score = round(random.uniform(60, 95), 2)
            total_return = round(random.uniform(-0.05, 0.25), 4)
            sharpe = round(random.uniform(0.3, 1.5), 2)
            drawdown = round(random.uniform(0.05, 0.20), 4)
            win_rate = round(random.uniform(0.30, 0.65), 2)
            profit_factor = round(random.uniform(1.0, 2.5), 2)

            # Emoji
            if rec_score >= 80:
                emoji = "🌟"
            elif rec_score >= 70:
                emoji = "✨"
            elif rec_score >= 60:
                emoji = "⭐"
            else:
                emoji = "💫"

            code = f"""import pandas as pd
import numpy as np

def generate_signal(data: pd.DataFrame) -> dict:
    # {symbol} {timeframe} Strategy {i}
    sma_fast = data['close'].rolling(window=10).mean()
    sma_slow = data['close'].rolling(window=30).mean()

    if sma_fast.iloc[-1] > sma_slow.iloc[-1]:
        return {{"signal": "buy", "confidence": {round(random.uniform(0.6, 0.9), 2)}}}
    elif sma_fast.iloc[-1] < sma_slow.iloc[-1]:
        return {{"signal": "sell", "confidence": {round(random.uniform(0.6, 0.9), 2)}}}

    return {{"signal": "hold", "confidence": 0.5}}
"""

            recommendation_summary = {
                "recommendation_score": rec_score,
                "recommendation_emoji": emoji,
                "one_line_summary": f"这是一个基于{timeframe}时间框架的{symbol}趋势跟踪策略，适合中等风险偏好的交易者。",
                "suitable_for": "中等风险偏好的趋势交易者" if rec_score > 70 else "保守型交易者",
                "account_requirement": f"建议账户余额 ${'10,000' if rec_score > 80 else '5,000'}+ (风险控制：每笔交易不超过2%)",
                "key_strengths": f"夏普比率{sharpe}表现良好，胜率{win_rate*100:.0f}%在可接受范围内" if sharpe > 1.0 else f"风险控制良好，最大回撤仅{drawdown*100:.1f}%",
                "key_weaknesses": f"最大回撤{drawdown*100:.1f}%偏高，需注意资金管理" if drawdown > 0.15 else "胜率略低，可能存在连续亏损期",
                "key_warnings": "策略表现受市场环境影响较大，建议定期监控和调整" if rec_score < 75 else "无特殊提示"
            }

            strategy = Strategy(
                id=f"STR_{i:03d}",
                name=f"Strategy {i}",
                code=code,
                status=status,
                performance={
                    "backtested_symbol": symbol,
                    "sharpe_ratio": sharpe,
                    "win_rate": win_rate,
                    "total_return": total_return,
                    "max_drawdown": drawdown,
                    "profit_factor": profit_factor,
                    "total_trades": random.randint(50, 200),
                    "avg_win": round(random.uniform(20, 50), 2),
                    "avg_loss": round(random.uniform(-15, -30), 2),
                    "recommendation_summary": recommendation_summary
                },
                params={
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "fast_period": 10,
                    "slow_period": 30
                },
                created_at=datetime.now() - timedelta(days=random.randint(1, 90)),
                updated_at=datetime.now()
            )
            strategies.append(strategy)

        session.add_all(strategies)
        session.commit()
        print(f"  ✓ 插入 {len(strategies)} 个策略")
        print()

        # 5. 插入Signal和Trade数据
        print("[5/5] 插入信号和交易数据...")

        signals = []
        for i in range(1, 11):
            signal_type = random.choice([Direction.BUY, Direction.SELL])
            signal = Signal(
                id=f"SIG_{i:05d}",
                strategy_id=random.choice([s.id for s in strategies]),
                symbol=random.choice(["EURUSD", "GBPUSD", "USDJPY"]),
                direction=signal_type,
                volume=round(random.uniform(0.01, 0.5), 2),
                entry_price=round(random.uniform(1.0, 1.5), 5),
                sl=round(random.uniform(0.9, 1.0), 5),
                tp=round(random.uniform(1.5, 1.6), 5),
                status=random.choice([SignalStatus.PENDING, SignalStatus.EXECUTED, SignalStatus.CANCELLED]),
                created_at=datetime.now() - timedelta(hours=random.randint(0, 24))
            )
            signals.append(signal)

        session.add_all(signals)
        session.commit()
        print(f"  ✓ 插入 {len(signals)} 个信号")

        trades = []
        for i in range(1, 21):
            trade_type = random.choice(["buy", "sell"])
            pnl = round(random.uniform(-50, 200), 2)
            open_time = datetime.now() - timedelta(hours=random.randint(1, 72))
            close_time = datetime.now() - timedelta(hours=random.randint(0, 48))

            trade = Trade(
                id=f"TRD_{i:06d}",
                ticket=str(10000000 + i),
                strategy_id=random.choice([s.id for s in strategies]),
                signal_id=random.choice([sig.id for sig in signals]),
                account_id=random.choice([acc.id for acc in accounts]),
                symbol=random.choice(["EURUSD", "GBPUSD", "USDJPY"]),
                action=trade_type,
                volume=round(random.uniform(0.01, 0.5), 2),
                open_price=round(random.uniform(1.0, 1.5), 5),
                close_price=round(random.uniform(1.0, 1.5), 5),
                sl=round(random.uniform(0.9, 1.0), 5),
                tp=round(random.uniform(1.5, 1.6), 5),
                profit=pnl,
                swap=round(random.uniform(-2, 2), 2),
                commission=round(random.uniform(-1, -0.1), 2),
                open_time=open_time,
                close_time=close_time,
                status="closed"
            )
            trades.append(trade)

        session.add_all(trades)
        session.commit()
        print(f"  ✓ 插入 {len(trades)} 个交易")
        print()

    print("=" * 50)
    print("  Mock数据初始化完成！")
    print("=" * 50)
    print()
    print("数据统计:")
    print(f"  - 策略: 15个")
    print(f"  - 账户: 2个")
    print(f"  - 信号: 10个")
    print(f"  - 交易: 20个")
    print()
    print("现在可以启动Dashboard查看数据:")
    print("  ./scripts/mac/start_all_services.sh")
    print()


if __name__ == "__main__":
    init_mock_data()
