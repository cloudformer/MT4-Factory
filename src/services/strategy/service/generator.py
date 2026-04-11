"""策略生成服务"""
from typing import List
from datetime import datetime

from src.common.models.strategy import Strategy, StrategyStatus
from src.common.utils.id_generator import generate_strategy_id
from ..repository.strategy_repo import StrategyRepository
from ..evaluator.strategy_evaluator import StrategyEvaluator


class StrategyGeneratorService:
    """策略生成业务逻辑"""

    def __init__(self, strategy_repo: StrategyRepository):
        self.strategy_repo = strategy_repo

    def generate_strategies(self, count: int, template: str = "ma_crossover") -> List[Strategy]:
        """
        生成策略，并使用多种方式评估

        Args:
            count: 生成数量
            template: 策略模板

        Returns:
            生成的策略列表
        """
        strategies = []

        print(f"🎯 开始生成 {count} 个策略...")

        for i in range(count):
            strategy_id = generate_strategy_id()

            # 生成策略代码（简化版，实际应调用AI）
            strategy_code = self._generate_code(strategy_id, template, i)

            # 从代码中提取参数作为名称
            import re
            match = re.search(r"快线(\d+)/慢线(\d+)", strategy_code)
            if match:
                fast, slow = match.groups()
                strategy_name = f"MA_{fast}x{slow}"
            else:
                strategy_name = f"{template.upper()}_{i+1}"

            print(f"\n🔬 [{i+1}/{count}] 评估策略: {strategy_name}")

            # 使用新的评估器进行评估
            try:
                # 创建评估器（使用配置文件中的参数）
                evaluator = StrategyEvaluator()

                # 运行评估（从配置文件读取启用状态和参数）
                # 配置文件路径：config/development.yaml
                # 配置项：strategy_evaluation.enabled_evaluators
                evaluation_results = evaluator.evaluate_all(strategy_code)

                # 提取评估结果
                # 优先级：有成功的评估就取第一个成功的，如果有多个则使用加权后的综合结果
                evaluations = evaluation_results['evaluations']

                # 查找第一个成功的评估结果
                performance = None
                for eval_type in ['synthetic', 'historical', 'realtime']:
                    result = evaluations.get(eval_type)
                    if result and 'error' not in result and result.get('status') != 'not_implemented':
                        performance = result
                        break

                if performance is None:
                    raise Exception("所有评估方式均失败")

                # 标记回测品种（为未来多货币对扩展预留）
                config_used = evaluation_results.get('config_used', {})
                performance['backtested_symbol'] = config_used.get('symbol', 'EURUSD')

                # 添加综合评分信息（如果有多个评估）
                summary = evaluation_results.get('summary', {})
                if summary.get('successful_evaluations', 0) > 1:
                    # 有多个成功的评估，添加综合评分到性能指标中
                    performance['weighted_overall_score'] = summary.get('overall_score')
                    performance['evaluation_consistency'] = summary.get('consistency')
                    performance['weights_used'] = summary.get('weights_used', {})

                print(f"   ✅ 评估完成 - 推荐度: {performance.get('recommendation_summary', {}).get('recommendation_score', 'N/A')}分")
                print(f"      Sharpe: {performance['sharpe_ratio']}, "
                      f"胜率: {performance['win_rate']*100:.1f}%, "
                      f"交易数: {performance['total_trades']}")

            except Exception as e:
                print(f"   ❌ 评估失败: {e}")
                # 如果评估失败，使用默认值
                performance = {
                    "sharpe_ratio": 0.0,
                    "max_drawdown": 0.0,
                    "win_rate": 0.0,
                    "profit_factor": 0.0,
                    "total_trades": 0,
                    "total_return": 0.0,
                    "backtest_date": datetime.now().isoformat(),
                    "data_source": "none"
                }

            # 创建策略对象
            strategy = Strategy(
                id=strategy_id,
                name=strategy_name,
                code=strategy_code,
                status=StrategyStatus.CANDIDATE,
                performance=performance
            )

            # 保存到数据库
            strategy = self.strategy_repo.create(strategy)
            strategies.append(strategy)

        print(f"\n✅ 策略生成完成！共 {len(strategies)} 个")
        return strategies

    def _generate_code(self, strategy_id: str, template: str, index: int) -> str:
        """
        生成策略代码

        未来这里会调用 AI（OpenAI/Claude）生成
        """
        import random

        if template == "ma_crossover":
            # 使用随机参数增加多样性
            # 快线: 5-20
            # 慢线: 20-60 (缩小范围，避免交易太少)
            fast_period = random.randint(5, 20)
            slow_period = random.randint(max(fast_period + 10, 20), 60)

            return f"""
class Strategy_{strategy_id}:
    '''MA 交叉策略 - 快线{fast_period}/慢线{slow_period}'''

    def __init__(self):
        self.fast_period = {fast_period}
        self.slow_period = {slow_period}

    def on_tick(self, data):
        # 计算均线
        fast_ma = data['close'].rolling(self.fast_period).mean()
        slow_ma = data['close'].rolling(self.slow_period).mean()

        # 交叉判断
        if fast_ma.iloc[-1] > slow_ma.iloc[-1] and fast_ma.iloc[-2] <= slow_ma.iloc[-2]:
            return 'buy'
        elif fast_ma.iloc[-1] < slow_ma.iloc[-1] and fast_ma.iloc[-2] >= slow_ma.iloc[-2]:
            return 'sell'

        return None
"""
        else:
            return f"# Template: {template} - Not implemented yet"

    def get_all_strategies(self) -> List[Strategy]:
        """获取所有策略"""
        return self.strategy_repo.get_all()

    def get_strategy(self, strategy_id: str) -> Strategy:
        """获取单个策略"""
        return self.strategy_repo.get_by_id(strategy_id)
