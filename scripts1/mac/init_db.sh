#!/bin/bash

# Mac环境 - SQLite数据库初始化脚本

echo "🔧 Mac环境 - SQLite数据库初始化"

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$PROJECT_ROOT"

# 数据库文件路径
DB_PATH="./data/evo_trade.db"

# 创建data目录
mkdir -p ./data

# 检查数据库是否已存在
if [ -f "$DB_PATH" ]; then
    echo "⚠️  数据库已存在: $DB_PATH"
    read -p "是否要重新初始化? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "❌ 取消初始化"
        exit 0
    fi
    rm "$DB_PATH"
    echo "🗑️  已删除旧数据库"
fi

# 使用Python和SQLAlchemy创建表
echo "📦 创建数据库表..."
python3 << EOF
import sys
sys.path.insert(0, '.')

from sqlalchemy import create_engine
from src.common.models.strategy import Base as StrategyBase
from src.common.models.signal import Base as SignalBase
from src.common.models.trade import Base as TradeBase
from src.common.models.account import Base as AccountBase
from src.common.models.account_allocation import Base as AccountAllocationBase
from src.common.models.historical_bar import Base as HistoricalBarBase
from src.common.models.mt5_host import Base as MT5HostBase

# 创建SQLite引擎
engine = create_engine('sqlite:///$DB_PATH')

# 创建所有表
StrategyBase.metadata.create_all(engine)
SignalBase.metadata.create_all(engine)
TradeBase.metadata.create_all(engine)
AccountBase.metadata.create_all(engine)
AccountAllocationBase.metadata.create_all(engine)
HistoricalBarBase.metadata.create_all(engine)
MT5HostBase.metadata.create_all(engine)

print("✅ 数据库表创建完成")
EOF

# 初始化MT5主机配置
echo "🌱 初始化MT5主机配置..."
python3 scripts/seed_mt5_hosts.py

echo ""
echo "🎉 SQLite数据库初始化完成！"
echo "   数据库文件: $DB_PATH"
echo ""
echo "📊 可以运行以下命令查看数据库："
echo "   sqlite3 $DB_PATH"
echo "   sqlite> .tables"
echo "   sqlite> .schema mt5_hosts"
