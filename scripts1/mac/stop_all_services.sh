#!/bin/bash
# Mac环境 - 停止所有服务

echo "=========================================="
echo "  停止MT4-Factory服务 (Mac环境)"
echo "=========================================="
echo ""

# 项目根目录
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$PROJECT_ROOT"

# 读取PID并停止服务
services=("dashboard" "strategy" "orchestrator" "execution" "validator")

for service in "${services[@]}"; do
    pid_file="logs/${service}.pid"

    if [ -f "$pid_file" ]; then
        PID=$(cat "$pid_file")

        if ps -p $PID > /dev/null 2>&1; then
            echo "停止 $service (PID: $PID)..."
            kill $PID 2>/dev/null
            sleep 1

            # 如果还在运行，强制停止
            if ps -p $PID > /dev/null 2>&1; then
                echo "  强制停止 $service..."
                kill -9 $PID 2>/dev/null
            fi

            echo "  ✓ $service 已停止"
        else
            echo "  - $service 未运行"
        fi

        rm -f "$pid_file"
    else
        echo "  - $service PID文件不存在"
    fi
done

echo ""
echo "=========================================="
echo "  所有服务已停止"
echo "=========================================="
echo ""
