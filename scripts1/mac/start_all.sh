#!/bin/bash
# Mac - 启动所有服务（后台运行）

export DEVICE=mac
source venv/bin/activate

echo "🚀 启动所有服务..."

# Dashboard (8001)
nohup uvicorn src.services.dashboard.api.app:app --host 0.0.0.0 --port 8001 > logs/dashboard.log 2>&1 &
echo "✅ Dashboard 启动 (端口 8001)"

# Orchestrator (8002)
nohup uvicorn src.services.orchestrator.main:app --host 0.0.0.0 --port 8002 > logs/orchestrator.log 2>&1 &
echo "✅ Orchestrator 启动 (端口 8002)"

sleep 2

echo ""
echo "🎉 所有服务已启动！"
echo ""
echo "服务地址："
echo "  Dashboard:     http://localhost:8001"
echo "  Orchestrator:  http://localhost:8002"
echo ""
echo "查看日志："
echo "  tail -f logs/dashboard.log"
echo "  tail -f logs/orchestrator.log"
