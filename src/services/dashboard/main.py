#!/usr/bin/env python3
"""Dashboard Service 入口"""
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

import uvicorn
from src.common.config.settings import settings

if __name__ == "__main__":
    # Dashboard 端口
    port = 8004

    print(f"📊 Dashboard Service 启动在 http://localhost:{port}")
    print(f"   职责：Web界面、数据展示、操作控制")
    print(f"   打开浏览器访问查看可视化界面")

    # 启动服务
    uvicorn.run(
        "src.services.dashboard.api.app:app",
        host="0.0.0.0",
        port=port,
        reload=False
    )
