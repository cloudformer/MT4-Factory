#!/usr/bin/env python3
"""
SQLite → MySQL 迁移脚本
用于：Mac开发环境数据迁移到生产环境
"""
import sys
import os
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import sqlite3
import pymysql
from tqdm import tqdm
from datetime import datetime

def migrate_sqlite_to_mysql(
    sqlite_path: str = "data/evo_trade.db",
    mysql_host: str = "localhost",
    mysql_port: int = 3306,
    mysql_user: str = "root",
    mysql_password: str = "",
    mysql_database: str = "evo_trade",
    batch_size: int = 1000
):
    """迁移SQLite数据到MySQL"""

    print("=" * 60)
    print("SQLite → MySQL 数据迁移")
    print("=" * 60)
    print()

    # 1. 连接SQLite
    print(f"[1/5] 连接SQLite: {sqlite_path}")
    sqlite_conn = sqlite3.connect(sqlite_path)
    sqlite_cursor = sqlite_conn.cursor()

    # 检查数据量
    sqlite_cursor.execute("SELECT COUNT(*) FROM historical_bars")
    total_rows = sqlite_cursor.fetchone()[0]
    print(f"  ✓ SQLite数据量: {total_rows:,} 行")
    print()

    # 2. 连接MySQL
    print(f"[2/5] 连接MySQL: {mysql_host}:{mysql_port}")
    mysql_conn = pymysql.connect(
        host=mysql_host,
        port=mysql_port,
        user=mysql_user,
        password=mysql_password,
        database=mysql_database,
        charset='utf8mb4'
    )
    mysql_cursor = mysql_conn.cursor()
    print("  ✓ MySQL连接成功")
    print()

    # 3. 检查MySQL表是否存在
    print("[3/5] 检查MySQL表结构")
    mysql_cursor.execute("SHOW TABLES LIKE 'historical_bars'")
    if not mysql_cursor.fetchone():
        print("  ⚠️  表不存在，自动创建...")
        create_table_sql = """
        CREATE TABLE historical_bars (
            id BIGINT AUTO_INCREMENT PRIMARY KEY,
            symbol VARCHAR(20) NOT NULL,
            timeframe VARCHAR(10) NOT NULL,
            time DATETIME NOT NULL,
            open DECIMAL(10, 5) NOT NULL,
            high DECIMAL(10, 5) NOT NULL,
            low DECIMAL(10, 5) NOT NULL,
            close DECIMAL(10, 5) NOT NULL,
            volume BIGINT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_symbol_timeframe_time (symbol, timeframe, time DESC),
            INDEX idx_time (time),
            UNIQUE KEY uk_symbol_timeframe_time (symbol, timeframe, time)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 ROW_FORMAT=COMPRESSED;
        """
        mysql_cursor.execute(create_table_sql)
        mysql_conn.commit()
        print("  ✓ 表创建成功")
    else:
        print("  ✓ 表已存在")

    # 检查是否有数据
    mysql_cursor.execute("SELECT COUNT(*) FROM historical_bars")
    existing_rows = mysql_cursor.fetchone()[0]
    if existing_rows > 0:
        print(f"  ⚠️  MySQL已有 {existing_rows:,} 行数据")
        print("  ⚠️  建议先清空表：TRUNCATE TABLE historical_bars;")
        response = input("  是否继续（可能重复）？[y/N]: ")
        if response.lower() != 'y':
            print("  取消迁移")
            return
    print()

    # 4. 迁移数据
    print(f"[4/5] 迁移数据（批量大小: {batch_size}）")

    # 读取SQLite数据
    sqlite_cursor.execute("""
        SELECT symbol, timeframe, time, open, high, low, close, volume, created_at
        FROM historical_bars
        ORDER BY time
    """)

    # 批量插入MySQL
    insert_sql = """
        INSERT INTO historical_bars
        (symbol, timeframe, time, open, high, low, close, volume, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            open = VALUES(open),
            high = VALUES(high),
            low = VALUES(low),
            close = VALUES(close),
            volume = VALUES(volume)
    """

    batch = []
    success_count = 0
    error_count = 0

    with tqdm(total=total_rows, desc="  迁移进度") as pbar:
        for row in sqlite_cursor:
            batch.append(row)

            if len(batch) >= batch_size:
                try:
                    mysql_cursor.executemany(insert_sql, batch)
                    mysql_conn.commit()
                    success_count += len(batch)
                    pbar.update(len(batch))
                    batch = []
                except Exception as e:
                    print(f"\n  ❌ 批量插入失败: {e}")
                    error_count += len(batch)
                    batch = []

        # 插入剩余数据
        if batch:
            try:
                mysql_cursor.executemany(insert_sql, batch)
                mysql_conn.commit()
                success_count += len(batch)
                pbar.update(len(batch))
            except Exception as e:
                print(f"\n  ❌ 最后一批插入失败: {e}")
                error_count += len(batch)

    print()
    print(f"  ✓ 成功: {success_count:,} 行")
    if error_count > 0:
        print(f"  ❌ 失败: {error_count:,} 行")
    print()

    # 5. 验证数据
    print("[5/5] 验证数据完整性")
    mysql_cursor.execute("SELECT COUNT(*) FROM historical_bars")
    mysql_rows = mysql_cursor.fetchone()[0]
    print(f"  SQLite: {total_rows:,} 行")
    print(f"  MySQL:  {mysql_rows:,} 行")

    if mysql_rows == total_rows:
        print("  ✅ 数据完整！")
    else:
        print(f"  ⚠️  差异: {abs(mysql_rows - total_rows)} 行")

    # 关闭连接
    sqlite_conn.close()
    mysql_conn.close()

    print()
    print("=" * 60)
    print("迁移完成！")
    print("=" * 60)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='SQLite → MySQL 迁移')
    parser.add_argument('--sqlite', default='data/evo_trade.db', help='SQLite数据库路径')
    parser.add_argument('--mysql-host', default='localhost', help='MySQL主机')
    parser.add_argument('--mysql-port', type=int, default=3306, help='MySQL端口')
    parser.add_argument('--mysql-user', default='root', help='MySQL用户')
    parser.add_argument('--mysql-password', default='', help='MySQL密码')
    parser.add_argument('--mysql-database', default='evo_trade', help='MySQL数据库')
    parser.add_argument('--batch-size', type=int, default=1000, help='批量大小')

    args = parser.parse_args()

    migrate_sqlite_to_mysql(
        sqlite_path=args.sqlite,
        mysql_host=args.mysql_host,
        mysql_port=args.mysql_port,
        mysql_user=args.mysql_user,
        mysql_password=args.mysql_password,
        mysql_database=args.mysql_database,
        batch_size=args.batch_size
    )
