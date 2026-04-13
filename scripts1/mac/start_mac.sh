#!/bin/bash
# Mac本地快速启动脚本

export DEVICE=mac
source venv/bin/activate
uvicorn src.services.dashboard.api.app:app --host 0.0.0.0 --port 8001
