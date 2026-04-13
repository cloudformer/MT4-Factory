#!/usr/bin/env python3
"""
将SQLite数据迁移到PostgreSQL

使用方法:
    python scripts/migrate_sqlite_to_postgres.py
"""
import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import sessionmaker

from src.common.models.base import Base
from src.common.models.strategy import Strategy
from src.common.models.signal import Signal
from src.common.models.trade import Trade
from src.common.models.account import Account


def migrate_data():
    """迁移数据从SQLite到PostgreSQL"""

    print("🔄 开始数据迁移：SQLite → PostgreSQL")
    print("=" * 60)

    # ========== 1. 连接SQLite（源数据库）==========
    sqlite_path = project_root / "data" / "evo_trade.db"

    if not sqlite_path.exists():
        print(f"⚠️  SQLite数据库不存在: {sqlite_path}")
        print("   可能是首次使用，无需迁移。")
        return

    print(f"\n📂 SQLite数据库: {sqlite_path}")
    sqlite_engine = create_engine(f"sqlite:///{sqlite_path}")
    SQLiteSession = sessionmaker(bind=sqlite_engine)
    sqlite_session = SQLiteSession()

    # ========== 2. 连接PostgreSQL（目标数据库）==========
    postgres_url = (
        "postgresql+psycopg2://evo_trade_user:evo_trade_pass_dev_2024"
        "@localhost:5432/evo_trade"
    )
    print(f"🐘 PostgreSQL: localhost:5432/evo_trade")

    try:
        postgres_engine = create_engine(postgres_url)
        # 测试连接
        with postgres_engine.connect() as conn:
            print("   ✅ PostgreSQL连接成功")
    except Exception as e:
        print(f"   ❌ PostgreSQL连接失败: {e}")
        print("\n💡 请先启动PostgreSQL容器:")
        print("   docker-compose up -d postgres")
        return

    # ========== 3. 创建表结构 ==========
    print("\n📊 创建PostgreSQL表结构...")
    Base.metadata.create_all(postgres_engine)
    print("   ✅ 表结构创建完成")

    PostgresSession = sessionmaker(bind=postgres_engine)
    postgres_session = PostgresSession()

    # ========== 4. 迁移数据 ==========
    models = [
        (Account, "账户"),
        (Strategy, "策略"),
        (Signal, "信号"),
        (Trade, "交易"),
    ]

    total_migrated = 0

    print("\n📦 开始迁移数据...")
    print("-" * 60)

    for Model, name in models:
        try:
            # 从SQLite读取
            records = sqlite_session.query(Model).all()
            count = len(records)

            if count == 0:
                print(f"   [{name}] 无数据，跳过")
                continue

            print(f"   [{name}] 迁移中... ", end="", flush=True)

            # 写入PostgreSQL
            for record in records:
                # 将对象转换为字典（排除关系属性）
                record_dict = {
                    c.name: getattr(record, c.name)
                    for c in record.__table__.columns
                }

                # 创建新对象
                new_record = Model(**record_dict)
                postgres_session.merge(new_record)

            postgres_session.commit()
            total_migrated += count

            print(f"✅ {count}条")

        except Exception as e:
            print(f"❌ 失败: {e}")
            postgres_session.rollback()

    # ========== 5. 验证 ==========
    print("\n" + "-" * 60)
    print("📊 验证迁移结果:")

    for Model, name in models:
        sqlite_count = sqlite_session.query(Model).count()
        postgres_count = postgres_session.query(Model).count()

        status = "✅" if sqlite_count == postgres_count else "⚠️"
        print(f"   {status} {name}: SQLite={sqlite_count}, PostgreSQL={postgres_count}")

    # ========== 6. 完成 ==========
    print("\n" + "=" * 60)
    print(f"✅ 迁移完成！共迁移 {total_migrated} 条记录")

    # 关闭连接
    sqlite_session.close()
    postgres_session.close()

    print("\n💡 下一步:")
    print("   1. 检查PostgreSQL数据: docker exec -it mt4-factory-postgres psql -U evo_trade_user -d evo_trade")
    print("   2. 备份SQLite数据库: mv data/evo_trade.db data/evo_trade.db.backup")
    print("   3. 重启服务: 停止所有服务，再启动")


if __name__ == "__main__":
    try:
        migrate_data()
    except KeyboardInterrupt:
        print("\n\n⏹️  迁移已取消")
    except Exception as e:
        print(f"\n❌ 迁移失败: {e}")
        import traceback
        traceback.print_exc()
