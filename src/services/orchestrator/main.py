#!/usr/bin/env python3
"""Orchestrator Service 入口 - 编排层"""
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

import uvicorn
from src.common.config.settings import settings

if __name__ == "__main__":
    # 获取服务配置
    service_config = settings.services.get('orchestrator', {})
    host = service_config.get('host', '0.0.0.0')
    port = service_config.get('port', 8002)

    print(f"🧠 Orchestrator Service 启动在 http://{host}:{port}")
    print(f"   职责：策略注册、调度决策、仓位管理、资金分配")

    # 启动服务
    uvicorn.run(
        "src.services.orchestrator.api.app:app",
        host=host,
        port=port,
        reload=False
    )
