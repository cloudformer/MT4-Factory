#!/bin/bash
# Mac环境 - 验证SQLite数据库状态

echo "🔍 验证SQLite数据库..."
echo ""

# 检查数据库文件
if [ ! -f "data/evo_trade.db" ]; then
    echo "❌ 数据库文件不存在: data/evo_trade.db"
    exit 1
fi

echo "✅ 数据库文件存在"
echo ""

# 查看表列表
echo "📊 数据库表列表："
sqlite3 data/evo_trade.db ".tables"
echo ""

# 查看表记录统计
echo "📈 表记录统计："
sqlite3 data/evo_trade.db "
SELECT 'accounts' as table_name, COUNT(*) as count FROM accounts
UNION ALL
SELECT 'strategies', COUNT(*) FROM strategies
UNION ALL
SELECT 'trades', COUNT(*) FROM trades
UNION ALL
SELECT 'signals', COUNT(*) FROM signals
UNION ALL
SELECT 'account_allocations', COUNT(*) FROM account_allocations;
"
echo ""

# 测试datetime字段
echo "🕐 测试datetime字段兼容性..."
sqlite3 data/evo_trade.db "SELECT created_at FROM strategies LIMIT 1;" > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✅ datetime字段正常"
else
    echo "❌ datetime字段异常"
    exit 1
fi

echo ""
echo "✅ SQLite验证完成！Mac环境正常"
