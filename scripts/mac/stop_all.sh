#!/bin/bash
# Mac - 停止所有服务

echo "🛑 停止所有服务..."

pkill -f "uvicorn src.services.dashboard"
pkill -f "uvicorn src.services.orchestrator"

echo "✅ 所有服务已停止"
