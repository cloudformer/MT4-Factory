#!/usr/bin/env python3
"""
MySQL → PostgreSQL 迁移脚本
用于：数据量超过30GB后的迁移
"""
import sys
import os
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pymysql
import psycopg2
from psycopg2.extras import execute_batch
from tqdm import tqdm
from datetime import datetime

def migrate_mysql_to_postgres(
    mysql_host: str = "localhost",
    mysql_port: int = 3306,
    mysql_user: str = "root",
    mysql_password: str = "",
    mysql_database: str = "evo_trade",
    postgres_host: str = "localhost",
    postgres_port: int = 5432,
    postgres_user: str = "evo_trade_user",
    postgres_password: str = "",
    postgres_database: str = "evo_trade",
    batch_size: int = 5000
):
    """迁移MySQL数据到PostgreSQL"""

    print("=" * 60)
    print("MySQL → PostgreSQL 数据迁移")
    print("=" * 60)
    print()

    # 1. 连接MySQL
    print(f"[1/5] 连接MySQL: {mysql_host}:{mysql_port}")
    mysql_conn = pymysql.connect(
        host=mysql_host,
        port=mysql_port,
        user=mysql_user,
        password=mysql_password,
        database=mysql_database,
        charset='utf8mb4'
    )
    mysql_cursor = mysql_conn.cursor()

    # 检查数据量
    mysql_cursor.execute("SELECT COUNT(*) FROM historical_bars")
    total_rows = mysql_cursor.fetchone()[0]
    print(f"  ✓ MySQL数据量: {total_rows:,} 行")

    # 检查数据大小
    mysql_cursor.execute("""
        SELECT
            ROUND(SUM(data_length + index_length) / 1024 / 1024, 2) as size_mb
        FROM information_schema.tables
        WHERE table_schema = %s AND table_name = 'historical_bars'
    """, (mysql_database,))
    size_mb = mysql_cursor.fetchone()[0]
    print(f"  ✓ 数据大小: {size_mb:,.2f} MB ({size_mb/1024:.2f} GB)")
    print()

    # 2. 连接PostgreSQL
    print(f"[2/5] 连接PostgreSQL: {postgres_host}:{postgres_port}")
    postgres_conn = psycopg2.connect(
        host=postgres_host,
        port=postgres_port,
        user=postgres_user,
        password=postgres_password,
        database=postgres_database
    )
    postgres_cursor = postgres_conn.cursor()
    print("  ✓ PostgreSQL连接成功")
    print()

    # 3. 检查PostgreSQL表是否存在
    print("[3/5] 检查PostgreSQL表结构")
    postgres_cursor.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_name = 'historical_bars'
        )
    """)
    table_exists = postgres_cursor.fetchone()[0]

    if not table_exists:
        print("  ⚠️  表不存在，创建分区表...")

        # 创建分区表
        create_table_sql = """
        CREATE TABLE historical_bars (
            id BIGSERIAL,
            symbol VARCHAR(20) NOT NULL,
            timeframe VARCHAR(10) NOT NULL,
            time TIMESTAMP NOT NULL,
            open DECIMAL(10, 5) NOT NULL,
            high DECIMAL(10, 5) NOT NULL,
            low DECIMAL(10, 5) NOT NULL,
            close DECIMAL(10, 5) NOT NULL,
            volume BIGINT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (time, symbol, timeframe)
        ) PARTITION BY RANGE (time);
        """
        postgres_cursor.execute(create_table_sql)

        # 创建年度分区（2020-2030）
        for year in range(2020, 2031):
            partition_sql = f"""
            CREATE TABLE historical_bars_{year} PARTITION OF historical_bars
                FOR VALUES FROM ('{year}-01-01') TO ('{year+1}-01-01');
            """
            postgres_cursor.execute(partition_sql)

        # 创建索引
        index_sql = """
        CREATE INDEX idx_symbol_timeframe_time
            ON historical_bars(symbol, timeframe, time DESC);
        """
        postgres_cursor.execute(index_sql)

        postgres_conn.commit()
        print("  ✓ 分区表创建成功")
    else:
        print("  ✓ 表已存在")

    # 检查是否有数据
    postgres_cursor.execute("SELECT COUNT(*) FROM historical_bars")
    existing_rows = postgres_cursor.fetchone()[0]
    if existing_rows > 0:
        print(f"  ⚠️  PostgreSQL已有 {existing_rows:,} 行数据")
        response = input("  是否清空后继续？[y/N]: ")
        if response.lower() == 'y':
            print("  清空数据...")
            postgres_cursor.execute("TRUNCATE TABLE historical_bars")
            postgres_conn.commit()
        else:
            print("  取消迁移")
            return
    print()

    # 4. 迁移数据
    print(f"[4/5] 迁移数据（批量大小: {batch_size}）")
    print("  ⚠️  大数据迁移，预计耗时较长...")

    # 读取MySQL数据（分批）
    mysql_cursor.execute("""
        SELECT symbol, timeframe, time, open, high, low, close, volume, created_at
        FROM historical_bars
        ORDER BY time
    """)

    # 批量插入PostgreSQL
    insert_sql = """
        INSERT INTO historical_bars
        (symbol, timeframe, time, open, high, low, close, volume, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (time, symbol, timeframe) DO UPDATE SET
            open = EXCLUDED.open,
            high = EXCLUDED.high,
            low = EXCLUDED.low,
            close = EXCLUDED.close,
            volume = EXCLUDED.volume
    """

    batch = []
    success_count = 0
    error_count = 0

    with tqdm(total=total_rows, desc="  迁移进度") as pbar:
        for row in mysql_cursor:
            batch.append(row)

            if len(batch) >= batch_size:
                try:
                    execute_batch(postgres_cursor, insert_sql, batch, page_size=1000)
                    postgres_conn.commit()
                    success_count += len(batch)
                    pbar.update(len(batch))
                    batch = []
                except Exception as e:
                    print(f"\n  ❌ 批量插入失败: {e}")
                    postgres_conn.rollback()
                    error_count += len(batch)
                    batch = []

        # 插入剩余数据
        if batch:
            try:
                execute_batch(postgres_cursor, insert_sql, batch, page_size=1000)
                postgres_conn.commit()
                success_count += len(batch)
                pbar.update(len(batch))
            except Exception as e:
                print(f"\n  ❌ 最后一批插入失败: {e}")
                postgres_conn.rollback()
                error_count += len(batch)

    print()
    print(f"  ✓ 成功: {success_count:,} 行")
    if error_count > 0:
        print(f"  ❌ 失败: {error_count:,} 行")
    print()

    # 5. 验证数据并优化
    print("[5/5] 验证数据并优化")
    postgres_cursor.execute("SELECT COUNT(*) FROM historical_bars")
    postgres_rows = postgres_cursor.fetchone()[0]
    print(f"  MySQL:      {total_rows:,} 行")
    print(f"  PostgreSQL: {postgres_rows:,} 行")

    if postgres_rows == total_rows:
        print("  ✅ 数据完整！")
    else:
        print(f"  ⚠️  差异: {abs(postgres_rows - total_rows)} 行")

    # VACUUM ANALYZE优化
    print("\n  执行VACUUM ANALYZE优化...")
    postgres_conn.set_isolation_level(0)  # autocommit模式
    postgres_cursor.execute("VACUUM ANALYZE historical_bars")
    print("  ✓ 优化完成")

    # 关闭连接
    mysql_conn.close()
    postgres_conn.close()

    print()
    print("=" * 60)
    print("迁移完成！")
    print("=" * 60)
    print()
    print("后续优化建议（可选）：")
    print("1. 安装TimescaleDB扩展：CREATE EXTENSION timescaledb;")
    print("2. 转换为Hypertable：SELECT create_hypertable('historical_bars', 'time');")
    print("3. 启用压缩：ALTER TABLE historical_bars SET (timescaledb.compress);")
    print()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='MySQL → PostgreSQL 迁移')
    parser.add_argument('--mysql-host', default='localhost', help='MySQL主机')
    parser.add_argument('--mysql-port', type=int, default=3306, help='MySQL端口')
    parser.add_argument('--mysql-user', default='root', help='MySQL用户')
    parser.add_argument('--mysql-password', default='', help='MySQL密码')
    parser.add_argument('--mysql-database', default='evo_trade', help='MySQL数据库')
    parser.add_argument('--postgres-host', default='localhost', help='PostgreSQL主机')
    parser.add_argument('--postgres-port', type=int, default=5432, help='PostgreSQL端口')
    parser.add_argument('--postgres-user', default='evo_trade_user', help='PostgreSQL用户')
    parser.add_argument('--postgres-password', default='', help='PostgreSQL密码')
    parser.add_argument('--postgres-database', default='evo_trade', help='PostgreSQL数据库')
    parser.add_argument('--batch-size', type=int, default=5000, help='批量大小')

    args = parser.parse_args()

    migrate_mysql_to_postgres(
        mysql_host=args.mysql_host,
        mysql_port=args.mysql_port,
        mysql_user=args.mysql_user,
        mysql_password=args.mysql_password,
        mysql_database=args.mysql_database,
        postgres_host=args.postgres_host,
        postgres_port=args.postgres_port,
        postgres_user=args.postgres_user,
        postgres_password=args.postgres_password,
        postgres_database=args.postgres_database,
        batch_size=args.batch_size
    )
