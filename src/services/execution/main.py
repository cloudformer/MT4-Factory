#!/usr/bin/env python3
"""Execution Service 入口"""
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

import uvicorn
from src.common.config.settings import settings
from src.common.mt5 import get_mt5_client

if __name__ == "__main__":
    # 初始化MT5
    mt5 = get_mt5_client()
    if mt5.initialize():
        mt5_config = settings.mt5
        if mt5.login(mt5_config['login'], mt5_config['password'], mt5_config['server']):
            account = mt5.account_info()
            if account:
                print(f"✅ MT5 连接成功: {account.login}@{account.server}")
                print(f"   余额: {account.balance} {account.currency}")

    # 获取服务配置
    service_config = settings.services.get('execution', {})
    host = service_config.get('host', '0.0.0.0')
    port = service_config.get('port', 8003)

    print(f"📡 Execution Service 启动在 http://{host}:{port}")
    print(f"   职责：订单执行、MT5对接、持仓查询、账户同步")

    # 启动服务
    uvicorn.run(
        "src.services.execution.api.app:app",
        host=host,
        port=port,
        reload=False
    )
