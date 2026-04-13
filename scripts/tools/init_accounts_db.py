#!/usr/bin/env python3
"""初始化账户相关数据库表"""
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.common.database.connection import db
from src.common.models.account import Account
from src.common.models.account_allocation import AccountAllocation
from src.common.config.settings import settings
from src.common.utils.id_generator import generate_id
from datetime import datetime


def init_tables():
    """创建账户相关表"""
    print("=" * 60)
    print("初始化账户数据库表")
    print("=" * 60)

    # 创建表
    print("\n📋 创建表结构...")
    Account.__table__.create(db.engine, checkfirst=True)
    AccountAllocation.__table__.create(db.engine, checkfirst=True)
    print("✅ 表创建完成")

    # 检查是否已有账户
    with db.session_scope() as session:
        existing_count = session.query(Account).count()

    if existing_count > 0:
        print(f"\n⚠️  数据库中已有 {existing_count} 个账户，跳过初始化数据")
        return

    # 创建默认账户（从配置文件读取）
    print("\n📝 创建默认账户...")
    mt5_config = settings.get("mt5", {})
    orchestrator_config = settings.get("orchestrator", {})

    account = Account(
        id=generate_id("ACC"),
        login=mt5_config.get("login", 5049130509),
        server=mt5_config.get("server", "MetaQuotes-Demo"),
        company=mt5_config.get("company", "MetaQuotes Ltd."),
        name="默认账户",
        currency="USD",
        leverage=100,
        initial_balance=orchestrator_config.get("portfolio", {}).get("initial_balance", 10000.0),
        start_time=datetime.now(),
        current_balance=orchestrator_config.get("portfolio", {}).get("initial_balance", 10000.0),
        current_equity=orchestrator_config.get("portfolio", {}).get("initial_balance", 10000.0),
        last_sync_time=datetime.now(),
        is_active=True,
        trade_allowed=True,
        risk_config={
            "max_daily_loss": orchestrator_config.get("risk", {}).get("max_daily_loss", 0.05),
            "max_total_exposure": orchestrator_config.get("portfolio", {}).get("max_total_exposure", 0.30),
            "max_concurrent_trades": orchestrator_config.get("risk", {}).get("max_concurrent_trades", 10)
        },
        notes="系统自动创建的默认账户"
    )

    with db.session_scope() as session:
        session.add(account)
        session.commit()
        session.refresh(account)  # 刷新对象
        # 在session内保存需要的信息
        account_id = account.id
        login = account.login
        server = account.server
        initial_balance = account.initial_balance
        currency = account.currency
        name = account.name
        print(f"✅ 创建账户: {name} (Login: {login})")

    print("\n" + "=" * 60)
    print("初始化完成")
    print("=" * 60)
    print(f"\n账户ID: {account_id}")
    print(f"账号: {login}")
    print(f"服务器: {server}")
    print(f"初始资金: {initial_balance} {currency}")


if __name__ == "__main__":
    init_tables()
