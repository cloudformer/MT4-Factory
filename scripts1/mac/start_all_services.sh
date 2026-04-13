#!/bin/bash
# Mac环境 - 启动所有服务（使用Mock数据）

echo "=========================================="
echo "  启动MT4-Factory服务 (Mac环境)"
echo "=========================================="
echo ""

# 项目根目录
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$PROJECT_ROOT"

# 激活虚拟环境
if [ ! -d "venv" ]; then
    echo "❌ 虚拟环境不存在，请先创建: python3 -m venv venv"
    exit 1
fi

source venv/bin/activate

# 设置环境变量
export DEVICE=mac
export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"

echo "项目目录: $PROJECT_ROOT"
echo "配置环境: $DEVICE"
echo "虚拟环境: venv"
echo ""

# 检查Python
if ! command -v python &> /dev/null; then
    echo "❌ Python未安装"
    exit 1
fi

echo "✓ Python版本: $(python --version)"
echo ""

# 创建日志目录
mkdir -p logs

echo "=========================================="
echo "  启动服务..."
echo "=========================================="
echo ""

# 启动Dashboard (端口8001)
echo "[1/5] 启动Dashboard服务 (端口8001)..."
python -m uvicorn src.services.dashboard.api.app:app --host 0.0.0.0 --port 8001 > logs/dashboard.log 2>&1 &
DASHBOARD_PID=$!
echo "  PID: $DASHBOARD_PID"
sleep 2

# 启动Strategy (端口8000)
echo "[2/5] 启动Strategy服务 (端口8000)..."
python -m uvicorn src.services.strategy.api.app:app --host 0.0.0.0 --port 8000 > logs/strategy.log 2>&1 &
STRATEGY_PID=$!
echo "  PID: $STRATEGY_PID"
sleep 2

# 启动Orchestrator (端口8002)
echo "[3/5] 启动Orchestrator服务 (端口8002)..."
python -m uvicorn src.services.orchestrator.api.app:app --host 0.0.0.0 --port 8002 > logs/orchestrator.log 2>&1 &
ORCHESTRATOR_PID=$!
echo "  PID: $ORCHESTRATOR_PID"
sleep 2

# 启动Execution (端口8003)
echo "[4/5] 启动Execution服务 (端口8003)..."
python -m uvicorn src.services.execution.api.app:app --host 0.0.0.0 --port 8003 > logs/execution.log 2>&1 &
EXECUTION_PID=$!
echo "  PID: $EXECUTION_PID"
sleep 2

# 启动Validator (端口8004)
echo "[5/5] 启动Validator服务 (端口8004)..."
python -m uvicorn src.services.validator.api.app:app --host 0.0.0.0 --port 8004 > logs/validator.log 2>&1 &
VALIDATOR_PID=$!
echo "  PID: $VALIDATOR_PID"
sleep 2

echo ""
echo "=========================================="
echo "  所有服务已启动！"
echo "=========================================="
echo ""
echo "服务列表:"
echo "  - Dashboard:     http://localhost:8001  (PID: $DASHBOARD_PID)"
echo "  - Strategy:      http://localhost:8000  (PID: $STRATEGY_PID)"
echo "  - Orchestrator:  http://localhost:8002  (PID: $ORCHESTRATOR_PID)"
echo "  - Execution:     http://localhost:8003  (PID: $EXECUTION_PID)"
echo "  - Validator:     http://localhost:8004  (PID: $VALIDATOR_PID)"
echo ""
echo "日志文件:"
echo "  - logs/dashboard.log"
echo "  - logs/strategy.log"
echo "  - logs/orchestrator.log"
echo "  - logs/execution.log"
echo "  - logs/validator.log"
echo ""
echo "停止服务:"
echo "  ./scripts/mac/stop_all_services.sh"
echo ""
echo "查看日志:"
echo "  tail -f logs/dashboard.log"
echo ""
echo "=========================================="
echo "  使用Mock数据模式"
echo "  所有MT5连接均为模拟数据"
echo "=========================================="
echo ""

# 保存PID到文件
echo "$DASHBOARD_PID" > logs/dashboard.pid
echo "$STRATEGY_PID" > logs/strategy.pid
echo "$ORCHESTRATOR_PID" > logs/orchestrator.pid
echo "$EXECUTION_PID" > logs/execution.pid
echo "$VALIDATOR_PID" > logs/validator.pid

echo "按Ctrl+C停止所有服务..."
echo ""

# 等待用户中断
trap 'echo ""; echo "停止所有服务..."; kill $DASHBOARD_PID $STRATEGY_PID $ORCHESTRATOR_PID $EXECUTION_PID $VALIDATOR_PID 2>/dev/null; exit 0' INT

# 保持脚本运行
wait
