"""策略评估器 - 统一调用各种评估方式"""
from typing import Dict, List, Optional
from datetime import datetime

from .synthetic_evaluator import SyntheticDataEvaluator
from .historical_evaluator import HistoricalDataEvaluator
from .realtime_evaluator import RealtimeDataEvaluator
from src.common.config.evaluation_config import get_evaluation_config, EvaluationConfig


class StrategyEvaluator:
    """
    策略评估器 - 统一调用多种评估方式

    支持三种评估模式：
    1. 合成数据评估（默认）- 使用模拟数据快速评估
    2. 历史数据评估 - 使用真实历史数据回测
    3. 实时数据评估 - 在实时行情中纸面交易测试
    """

    def __init__(self, initial_balance: Optional[float] = None, config: Optional[EvaluationConfig] = None):
        """
        初始化策略评估器

        Args:
            initial_balance: 初始资金（可选，如不指定则从配置文件读取）
            config: 评估配置对象（可选，如不指定则从配置文件加载）
        """
        # 加载配置
        self.config = config if config is not None else get_evaluation_config()

        # 初始资金（优先使用参数，否则使用配置）
        self.initial_balance = initial_balance if initial_balance is not None else self.config.initial_balance

        # 初始化三种评估器
        self.synthetic_evaluator = SyntheticDataEvaluator(self.initial_balance)
        self.historical_evaluator = HistoricalDataEvaluator(self.initial_balance)
        self.realtime_evaluator = RealtimeDataEvaluator(self.initial_balance)

        # 评估权重配置（从配置文件读取）
        self.evaluation_weights = self.config.weights.copy()

    def evaluate_all(self, strategy_code: str, symbol: Optional[str] = None,
                    include_synthetic: Optional[bool] = None,
                    include_historical: Optional[bool] = None,
                    include_realtime: Optional[bool] = None) -> Dict:
        """
        使用多种方式评估策略

        Args:
            strategy_code: 策略代码
            symbol: 交易品种（可选，默认从配置读取）
            include_synthetic: 是否包含合成数据评估（可选，默认从配置读取）
            include_historical: 是否包含历史数据评估（可选，默认从配置读取）
            include_realtime: 是否包含实时评估（可选，默认从配置读取）

        Returns:
            包含所有评估结果的字典
        """
        # 从配置读取默认值（如果参数未指定）
        symbol = symbol if symbol is not None else self.config.symbol
        include_synthetic = include_synthetic if include_synthetic is not None else self.config.include_synthetic
        include_historical = include_historical if include_historical is not None else self.config.include_historical
        include_realtime = include_realtime if include_realtime is not None else self.config.include_realtime

        results = {
            'strategy_code': strategy_code,
            'symbol': symbol,
            'evaluation_time': datetime.now().isoformat(),
            'evaluations': {},
            'config_used': {
                'include_synthetic': include_synthetic,
                'include_historical': include_historical,
                'include_realtime': include_realtime,
                'symbol': symbol
            }
        }

        # 1. 合成数据评估
        if include_synthetic:
            try:
                print("📊 [1/3] 合成数据评估...")
                synthetic_result = self.evaluate_synthetic(strategy_code, symbol)
                results['evaluations']['synthetic'] = synthetic_result
                print(f"   ✅ 完成 - 综合评分: {synthetic_result.get('recommendation_summary', {}).get('recommendation_score', 'N/A')}")
            except Exception as e:
                print(f"   ❌ 合成数据评估失败: {e}")
                results['evaluations']['synthetic'] = {'error': str(e)}

        # 2. 历史数据评估
        if include_historical:
            try:
                print("📊 [2/3] 历史数据评估...")
                historical_result = self.evaluate_historical(strategy_code, symbol)
                results['evaluations']['historical'] = historical_result
                print(f"   ✅ 完成 - 综合评分: {historical_result.get('recommendation_summary', {}).get('recommendation_score', 'N/A')}")
            except NotImplementedError as e:
                print(f"   ⚠️  历史数据评估暂未实现: {e}")
                results['evaluations']['historical'] = {'status': 'not_implemented', 'message': str(e)}
            except Exception as e:
                print(f"   ❌ 历史数据评估失败: {e}")
                results['evaluations']['historical'] = {'error': str(e)}

        # 3. 实时评估
        if include_realtime:
            try:
                print("📊 [3/3] 实时数据评估...")
                realtime_result = self.evaluate_realtime(strategy_code, symbol)
                results['evaluations']['realtime'] = realtime_result
                print(f"   ✅ 完成 - 综合评分: {realtime_result.get('recommendation_summary', {}).get('recommendation_score', 'N/A')}")
            except NotImplementedError as e:
                print(f"   ⚠️  实时评估暂未实现: {e}")
                results['evaluations']['realtime'] = {'status': 'not_implemented', 'message': str(e)}
            except Exception as e:
                print(f"   ❌ 实时评估失败: {e}")
                results['evaluations']['realtime'] = {'error': str(e)}

        # 4. 综合结论（基于已完成的评估）
        results['summary'] = self._generate_summary(results['evaluations'])

        return results

    def evaluate_synthetic(self, strategy_code: str, symbol: str = "EURUSD", bars: int = 3000) -> Dict:
        """
        使用合成数据评估策略（默认方式）

        Args:
            strategy_code: 策略代码
            symbol: 交易品种
            bars: K线数量

        Returns:
            评估指标
        """
        return self.synthetic_evaluator.evaluate(strategy_code, symbol, bars)

    def evaluate_historical(self, strategy_code: str, symbol: str = "EURUSD",
                           timeframe: str = "H1", bars: int = 3000) -> Dict:
        """
        使用历史数据评估策略

        Args:
            strategy_code: 策略代码
            symbol: 交易品种
            timeframe: 时间周期
            bars: K线数量

        Returns:
            评估指标
        """
        return self.historical_evaluator.evaluate(
            strategy_code, symbol, timeframe, bars
        )

    def evaluate_realtime(self, strategy_code: str, symbol: str = "EURUSD",
                         duration_minutes: int = 60) -> Dict:
        """
        使用实时数据评估策略（纸面交易）

        Args:
            strategy_code: 策略代码
            symbol: 交易品种
            duration_minutes: 测试持续时间

        Returns:
            评估指标
        """
        return self.realtime_evaluator.evaluate(
            strategy_code, symbol, duration_minutes
        )

    def _generate_summary(self, evaluations: Dict) -> Dict:
        """
        生成综合评估总结

        使用加权平均计算综合评分：
        - 只有synthetic: 100% synthetic
        - synthetic + historical: 按比例调整
        - 全部开启: historical 60%, synthetic 20%, realtime 20%

        Args:
            evaluations: 所有评估结果

        Returns:
            综合总结
        """
        summary = {
            'total_evaluations': 0,
            'successful_evaluations': 0,
            'failed_evaluations': 0,
            'individual_scores': {},
            'weights_used': {},
            'consistency': 'unknown'
        }

        # 1. 收集有效的评估结果
        valid_evaluations = {}
        for eval_type, result in evaluations.items():
            summary['total_evaluations'] += 1

            if 'error' in result or result.get('status') == 'not_implemented':
                summary['failed_evaluations'] += 1
                continue

            summary['successful_evaluations'] += 1

            # 提取推荐分数
            rec_score = result.get('recommendation_summary', {}).get('recommendation_score')
            if rec_score:
                valid_evaluations[eval_type] = rec_score
                summary['individual_scores'][eval_type] = rec_score

        # 2. 计算加权平均分
        if valid_evaluations:
            # 动态调整权重
            active_weights = self._calculate_dynamic_weights(list(valid_evaluations.keys()))

            # 加权求和
            weighted_sum = 0
            total_weight = 0

            for eval_type, score in valid_evaluations.items():
                weight = active_weights.get(eval_type, 0)
                weighted_sum += score * weight
                total_weight += weight
                summary['weights_used'][eval_type] = f"{weight*100:.0f}%"

            # 综合评分（加权平均）
            if total_weight > 0:
                summary['overall_score'] = round(weighted_sum / total_weight, 1)
                summary['calculation_method'] = 'weighted_average'
            else:
                # 回退到简单平均
                summary['overall_score'] = round(sum(valid_evaluations.values()) / len(valid_evaluations), 1)
                summary['calculation_method'] = 'simple_average'

            # 3. 评估一致性（分数差异）
            scores = list(valid_evaluations.values())
            if len(scores) > 1:
                score_variance = max(scores) - min(scores)
                if score_variance < 10:
                    summary['consistency'] = 'high'  # 高度一致
                    summary['consistency_note'] = '各评估方式结果高度一致'
                elif score_variance < 20:
                    summary['consistency'] = 'medium'  # 中等一致
                    summary['consistency_note'] = '各评估方式结果基本一致'
                else:
                    summary['consistency'] = 'low'  # 低一致性（需要注意）
                    summary['consistency_note'] = f'⚠️  评估结果差异较大（{score_variance:.1f}分），建议谨慎使用'
            else:
                summary['consistency'] = 'single_evaluation'
                summary['consistency_note'] = '仅有一种评估方式'

        return summary

    def _calculate_dynamic_weights(self, active_eval_types: List[str]) -> Dict[str, float]:
        """
        根据实际启用的评估方式，动态调整权重（从配置文件读取）

        Args:
            active_eval_types: 实际运行的评估类型列表

        Returns:
            权重字典
        """
        # 使用配置的权重计算方法
        return self.config.get_weights_for_combination(active_eval_types)

    def compare_evaluations(self, results: Dict) -> Dict:
        """
        对比不同评估方式的结果

        Args:
            results: evaluate_all() 返回的结果

        Returns:
            对比分析
        """
        comparison = {
            'metrics_comparison': {},
            'recommendation_comparison': {},
            'discrepancies': []
        }

        evaluations = results.get('evaluations', {})

        # 对比关键指标
        key_metrics = [
            'total_return', 'sharpe_ratio', 'max_drawdown',
            'win_rate', 'profit_factor'
        ]

        for metric in key_metrics:
            comparison['metrics_comparison'][metric] = {}
            for eval_type, result in evaluations.items():
                if 'error' not in result and result.get('status') != 'not_implemented':
                    value = result.get(metric)
                    if value is not None:
                        comparison['metrics_comparison'][metric][eval_type] = value

        # 对比推荐结论
        for eval_type, result in evaluations.items():
            if 'error' not in result and result.get('status') != 'not_implemented':
                rec = result.get('recommendation_summary', {})
                comparison['recommendation_comparison'][eval_type] = {
                    'score': rec.get('recommendation_score'),
                    'text': rec.get('recommendation_text'),
                    'emoji': rec.get('recommendation_emoji')
                }

        # 检测重大差异
        scores = [v['score'] for v in comparison['recommendation_comparison'].values() if v.get('score')]
        if len(scores) > 1:
            if max(scores) - min(scores) > 20:
                comparison['discrepancies'].append(
                    f"⚠️  推荐分数差异较大：{min(scores)}-{max(scores)}，建议谨慎使用"
                )

        return comparison
