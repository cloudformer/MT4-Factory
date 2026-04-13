#!/bin/bash
# Cloud生产环境 - 启动所有服务（Docker）
# 包括：postgres, dashboard, orchestrator, strategy, validator, execution

echo "🚀 启动Cloud生产环境..."
echo ""

# 设置环境变量
export ENV=production

# 加载环境变量（密码、API密钥等）
if [ -f .env.production ]; then
    echo "📋 加载生产环境变量..."
    source .env.production
else
    echo "⚠️  警告：未找到 .env.production 文件"
    echo "   请确保设置以下环境变量："
    echo "   - POSTGRES_PASSWORD"
    echo "   - MT5_REAL_PASSWORD"
    echo "   - MT5_REAL_API_KEY"
    echo "   - ANTHROPIC_API_KEY"
    echo ""
fi

# 启动所有生产服务（使用production profile）
docker-compose --profile production up -d

echo ""
echo "✅ 所有服务已启动！"
echo ""
echo "📊 服务地址（内部）："
echo "   Dashboard:     http://dashboard:8001"
echo "   Orchestrator:  http://orchestrator:8002"
echo "   Strategy:      http://strategy:8000"
echo "   Validator:     http://validator:8080"
echo "   Execution:     http://execution:8003 ⚠️"
echo ""
echo "📝 查看日志："
echo "   docker-compose logs -f execution"
echo "   docker-compose logs -f validator"
echo ""
echo "🛑 停止服务："
echo "   docker-compose --profile production down"
echo ""
