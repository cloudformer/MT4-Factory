"""测试加权评估功能"""
import sys
sys.path.insert(0, '/Users/frankzhang/repo-private/MT4-Factory')

from src.services.strategy.evaluator import StrategyEvaluator


def test_weighted_evaluation():
    """测试加权平均计算"""

    # 创建一个简单的测试策略
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

    evaluator = StrategyEvaluator(initial_balance=10000.0)

    print("=" * 60)
    print("测试加权评估功能")
    print("=" * 60)

    # 测试1：只有synthetic
    print("\n【测试1】只启用 synthetic")
    print("-" * 60)
    results1 = evaluator.evaluate_all(
        strategy_code,
        include_synthetic=True,
        include_historical=False,
        include_realtime=False
    )

    summary1 = results1['summary']
    print(f"✅ 综合评分: {summary1.get('overall_score', 'N/A')}")
    print(f"   计算方法: {summary1.get('calculation_method', 'N/A')}")
    print(f"   使用权重: {summary1.get('weights_used', {})}")
    print(f"   一致性: {summary1.get('consistency', 'N/A')}")

    # 测试2：模拟 synthetic + historical 的情况
    print("\n【测试2】模拟 synthetic + historical (手动构造)")
    print("-" * 60)

    # 手动构造一个假的historical结果
    synthetic_result = results1['evaluations']['synthetic']

    # 假设historical结果略有不同
    historical_result = synthetic_result.copy()
    if 'recommendation_summary' in historical_result:
        # 假设历史数据评估得分更高
        historical_result['recommendation_summary'] = historical_result['recommendation_summary'].copy()
        original_score = historical_result['recommendation_summary']['recommendation_score']
        historical_result['recommendation_summary']['recommendation_score'] = min(original_score + 5, 100)

    fake_evaluations = {
        'synthetic': synthetic_result,
        'historical': historical_result
    }

    fake_summary = evaluator._generate_summary(fake_evaluations)

    print(f"   Synthetic 分数: {synthetic_result.get('recommendation_summary', {}).get('recommendation_score', 'N/A')}")
    print(f"   Historical 分数: {historical_result.get('recommendation_summary', {}).get('recommendation_score', 'N/A')}")
    print(f"✅ 综合评分: {fake_summary.get('overall_score', 'N/A')}")
    print(f"   计算方法: {fake_summary.get('calculation_method', 'N/A')}")
    print(f"   使用权重: {fake_summary.get('weights_used', {})}")
    print(f"   一致性: {fake_summary.get('consistency', 'N/A')} - {fake_summary.get('consistency_note', '')}")

    # 手动验证计算
    syn_score = synthetic_result.get('recommendation_summary', {}).get('recommendation_score', 0)
    hist_score = historical_result.get('recommendation_summary', {}).get('recommendation_score', 0)
    expected_weighted = syn_score * 0.25 + hist_score * 0.75
    print(f"\n   🔍 手动验证: {syn_score} * 0.25 + {hist_score} * 0.75 = {expected_weighted:.1f}")
    print(f"   系统计算: {fake_summary.get('overall_score', 'N/A')}")
    print(f"   {'✅ 匹配' if abs(expected_weighted - fake_summary.get('overall_score', 0)) < 0.1 else '❌ 不匹配'}")

    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)


if __name__ == "__main__":
    test_weighted_evaluation()
