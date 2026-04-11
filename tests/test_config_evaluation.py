"""测试配置化的评估器"""
import sys
sys.path.insert(0, '/Users/frankzhang/repo-private/MT4-Factory')

from src.common.config.evaluation_config import get_evaluation_config
from src.services.strategy.evaluator import StrategyEvaluator


def test_config_loading():
    """测试配置加载"""
    print("=" * 60)
    print("测试配置加载")
    print("=" * 60)

    config = get_evaluation_config()

    print(f"\n✅ 配置已加载: {config.config_path}")
    print(f"\n📊 启用的评估器:")
    print(f"  - Synthetic:  {config.include_synthetic}")
    print(f"  - Historical: {config.include_historical}")
    print(f"  - Realtime:   {config.include_realtime}")

    print(f"\n⚖️  评估权重 (三个都启用时):")
    for eval_type, weight in config.weights.items():
        print(f"  - {eval_type}: {weight*100:.0f}%")

    print(f"\n⚖️  双评估权重:")
    for combo, weights in config.two_evaluator_weights.items():
        print(f"  - {combo}:")
        for eval_type, weight in weights.items():
            print(f"      {eval_type}: {weight*100:.0f}%")

    print(f"\n📈 评估参数:")
    print(f"  - 初始资金: ${config.initial_balance:,.2f}")
    print(f"  - 合成数据K线数: {config.synthetic_bars}")
    print(f"  - 历史数据K线数: {config.historical_bars}")
    print(f"  - 实时测试时长: {config.realtime_duration_minutes}分钟")
    print(f"  - 默认品种: {config.symbol}")


def test_evaluator_with_config():
    """测试评估器使用配置"""
    print("\n" + "=" * 60)
    print("测试评估器使用配置")
    print("=" * 60)

    strategy_code = """
class Strategy_test:
    def __init__(self):
        self.fast_period = 10
        self.slow_period = 30

    def on_tick(self, data):
        fast_ma = data['close'].rolling(self.fast_period).mean()
        slow_ma = data['close'].rolling(self.slow_period).mean()

        if fast_ma.iloc[-1] > slow_ma.iloc[-1] and fast_ma.iloc[-2] <= slow_ma.iloc[-2]:
            return 'buy'
        elif fast_ma.iloc[-1] < slow_ma.iloc[-1] and fast_ma.iloc[-2] >= slow_ma.iloc[-2]:
            return 'sell'

        return None
"""

    # 创建评估器（不传参数，完全使用配置）
    print("\n🔧 创建评估器（使用配置文件默认值）...")
    evaluator = StrategyEvaluator()

    print(f"  - 初始资金: ${evaluator.initial_balance:,.2f}")
    print(f"  - 权重配置: {evaluator.evaluation_weights}")

    # 运行评估（不传参数，完全使用配置）
    print("\n🚀 运行评估（使用配置文件的启用状态）...")
    results = evaluator.evaluate_all(strategy_code)

    # 显示使用的配置
    config_used = results.get('config_used', {})
    print(f"\n✅ 实际使用的配置:")
    print(f"  - 品种: {config_used.get('symbol')}")
    print(f"  - Synthetic 启用: {config_used.get('include_synthetic')}")
    print(f"  - Historical 启用: {config_used.get('include_historical')}")
    print(f"  - Realtime 启用: {config_used.get('include_realtime')}")

    # 显示评估结果
    print(f"\n📊 评估结果:")
    for eval_type, result in results['evaluations'].items():
        if 'error' in result:
            print(f"  - {eval_type}: ❌ {result['error']}")
        elif result.get('status') == 'not_implemented':
            print(f"  - {eval_type}: ⚠️  暂未实现")
        else:
            score = result.get('recommendation_summary', {}).get('recommendation_score', 'N/A')
            print(f"  - {eval_type}: ✅ 推荐度 {score}分")

    # 显示综合评分
    summary = results.get('summary', {})
    if summary:
        print(f"\n🎯 综合评分:")
        print(f"  - 综合评分: {summary.get('overall_score', 'N/A')}分")
        print(f"  - 计算方法: {summary.get('calculation_method', 'N/A')}")
        print(f"  - 使用权重: {summary.get('weights_used', {})}")
        print(f"  - 一致性: {summary.get('consistency', 'N/A')}")


def test_override_config():
    """测试覆盖配置"""
    print("\n" + "=" * 60)
    print("测试覆盖配置（临时修改）")
    print("=" * 60)

    strategy_code = """
class Strategy_test:
    def __init__(self):
        self.fast_period = 10
        self.slow_period = 30

    def on_tick(self, data):
        fast_ma = data['close'].rolling(self.fast_period).mean()
        slow_ma = data['close'].rolling(self.slow_period).mean()

        if fast_ma.iloc[-1] > slow_ma.iloc[-1] and fast_ma.iloc[-2] <= slow_ma.iloc[-2]:
            return 'buy'
        elif fast_ma.iloc[-1] < slow_ma.iloc[-1] and fast_ma.iloc[-2] >= slow_ma.iloc[-2]:
            return 'sell'

        return None
"""

    evaluator = StrategyEvaluator()

    # 覆盖配置（临时修改）
    print("\n🔧 临时覆盖配置：强制开启 historical")
    results = evaluator.evaluate_all(
        strategy_code,
        symbol="GBPUSD",              # 覆盖品种
        include_synthetic=True,       # 覆盖启用状态
        include_historical=True,      # 强制开启（配置文件中是false）
        include_realtime=False
    )

    config_used = results.get('config_used', {})
    print(f"\n✅ 实际使用的配置:")
    print(f"  - 品种: {config_used.get('symbol')} (覆盖)")
    print(f"  - Synthetic 启用: {config_used.get('include_synthetic')}")
    print(f"  - Historical 启用: {config_used.get('include_historical')} (被覆盖)")
    print(f"  - Realtime 启用: {config_used.get('include_realtime')}")


if __name__ == "__main__":
    test_config_loading()
    test_evaluator_with_config()
    test_override_config()

    print("\n" + "=" * 60)
    print("✅ 所有测试完成！")
    print("=" * 60)
