#!/usr/bin/env python3
"""生成假交易数据用于测试"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from datetime import datetime, timedelta
import random
from src.common.database.connection import db
from src.common.models.trade import Trade
from src.common.models.signal import Direction
from src.common.utils.id_generator import generate_trade_id


def generate_fake_trades():
    """生成假交易数据"""

    # 现有数据
    account_id = "ACC_6d638a3c"
    account_login = 5049130509

    # 先从数据库查询ACTIVE状态的策略（只有激活的策略才能产生交易！）
    with db.session_scope() as session:
        from src.common.models.strategy import Strategy, StrategyStatus

        active_strategies = session.query(Strategy).filter(
            Strategy.status == StrategyStatus.ACTIVE
        ).all()

        if len(active_strategies) == 0:
            print("❌ 错误：数据库中没有ACTIVE状态的策略！")
            print("   只有ACTIVE策略才能产生交易，CANDIDATE策略不会参与交易。")
            print("\n💡 解决方法：")
            print("   1. 先激活一些策略")
            print("   2. 在Dashboard中点击'✅ 激活策略'按钮")
            return

        strategy_ids = [s.id for s in active_strategies]
        print(f"✅ 找到 {len(strategy_ids)} 个ACTIVE策略：")
        for s in active_strategies:
            print(f"   - {s.id} ({s.name})")

    symbols = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCHF"]

    trades = []
    base_ticket = 1234567890

    # 生成30条交易记录
    for i in range(30):
        # 70%的交易有策略ID（来自ACTIVE策略），30%是手动交易（无策略ID）
        if random.random() < 0.7 and len(strategy_ids) > 0:
            strategy_id = random.choice(strategy_ids)  # 只使用ACTIVE策略
        else:
            strategy_id = None  # 手动交易（无策略ID）

        symbol = random.choice(symbols)
        direction = random.choice([Direction.BUY, Direction.SELL])
        volume = round(random.uniform(0.01, 1.0), 2)

        # 生成价格
        if symbol == "EURUSD":
            open_price = round(random.uniform(1.08, 1.10), 5)
        elif symbol == "GBPUSD":
            open_price = round(random.uniform(1.26, 1.28), 5)
        elif symbol == "USDJPY":
            open_price = round(random.uniform(149, 151), 3)
        elif symbol == "AUDUSD":
            open_price = round(random.uniform(0.65, 0.67), 5)
        else:  # USDCHF
            open_price = round(random.uniform(0.88, 0.90), 5)

        # 生成盈亏（60%盈利，40%亏损）
        if random.random() < 0.6:
            profit = round(random.uniform(5.0, 200.0), 2)
        else:
            profit = -round(random.uniform(5.0, 150.0), 2)

        # 生成开仓时间（最近30天内）
        days_ago = random.randint(0, 30)
        open_time = datetime.now() - timedelta(days=days_ago, hours=random.randint(0, 23))

        trade = Trade(
            id=generate_trade_id(),
            account_id=account_id,
            signal_id=None,
            strategy_id=strategy_id,
            ticket=base_ticket + i,
            symbol=symbol,
            direction=direction,
            volume=volume,
            open_price=open_price,
            close_price=None,
            profit=profit,
            open_time=open_time,
            close_time=None
        )

        trades.append(trade)

    # 保存到数据库
    with db.session_scope() as session:
        # 先检查是否已有交易记录，如果有就删除旧的
        existing = session.query(Trade).count()
        if existing > 0:
            print(f"⚠️  数据库中已有 {existing} 条交易记录")
            confirm = input("是否删除旧数据并生成新数据？(y/n): ")
            if confirm.lower() != 'y':
                print("❌ 已取消")
                return
            session.query(Trade).delete()
            print(f"✅ 已删除 {existing} 条旧记录")

        # 插入新数据
        for trade in trades:
            session.add(trade)

        session.commit()
        print(f"\n✅ 成功生成 {len(trades)} 条假交易数据！")

        # 统计信息
        with_strategy = sum(1 for t in trades if t.strategy_id)
        without_strategy = sum(1 for t in trades if not t.strategy_id)
        total_profit = sum(t.profit or 0 for t in trades)

        print(f"\n📊 统计信息：")
        print(f"   总交易数: {len(trades)}")
        print(f"   有策略ID: {with_strategy} 条")
        print(f"   无策略ID: {without_strategy} 条")
        print(f"   总盈亏: {total_profit:.2f} USD")
        print(f"   账号Login: {account_login}")
        print(f"\n🎯 测试提示：")
        print(f"   - 账号ID筛选: 输入 '{account_login}' 查看所有交易")
        print(f"   - 策略ID筛选: 输入 'STR_8a12e1ad' 查看该策略的交易")
        print(f"   - 策略ID为空: 留空策略ID输入框，查看所有交易（包括无策略的）")


if __name__ == "__main__":
    generate_fake_trades()
