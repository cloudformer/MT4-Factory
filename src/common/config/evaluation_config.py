"""策略评估配置加载器"""
from typing import Dict, Optional
import yaml
from pathlib import Path


class EvaluationConfig:
    """策略评估配置类"""

    def __init__(self, config_path: Optional[str] = None):
        """
        初始化配置

        Args:
            config_path: 配置文件路径，默认为 config/development.yaml
        """
        if config_path is None:
            # 默认配置文件路径
            project_root = Path(__file__).parent.parent.parent.parent
            config_path = project_root / "config" / "development.yaml"

        self.config_path = config_path
        self._load_config()

    def _load_config(self):
        """从YAML文件加载配置"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)

            eval_config = config.get('strategy_evaluation', {})

            # 启用的评估器
            self.enabled_evaluators = eval_config.get('enabled_evaluators', {
                'synthetic': True,
                'historical': False,
                'realtime': False
            })

            # 权重配置
            self.weights = eval_config.get('weights', {
                'historical': 0.60,
                'synthetic': 0.20,
                'realtime': 0.20
            })

            # 双评估权重
            self.two_evaluator_weights = eval_config.get('two_evaluator_weights', {
                'synthetic_historical': {'historical': 0.75, 'synthetic': 0.25},
                'synthetic_realtime': {'synthetic': 0.60, 'realtime': 0.40},
                'historical_realtime': {'historical': 0.75, 'realtime': 0.25}
            })

            # 评估参数
            params = eval_config.get('parameters', {})
            self.initial_balance = params.get('initial_balance', 10000.0)
            self.synthetic_bars = params.get('synthetic_bars', 3000)
            self.historical_bars = params.get('historical_bars', 3000)
            self.realtime_duration_minutes = params.get('realtime_duration_minutes', 60)
            self.symbol = params.get('symbol', 'EURUSD')

        except FileNotFoundError:
            print(f"⚠️  配置文件未找到: {self.config_path}，使用默认配置")
            self._use_defaults()
        except Exception as e:
            print(f"⚠️  加载配置失败: {e}，使用默认配置")
            self._use_defaults()

    def _use_defaults(self):
        """使用默认配置"""
        self.enabled_evaluators = {
            'synthetic': True,
            'historical': False,
            'realtime': False
        }
        self.weights = {
            'historical': 0.60,
            'synthetic': 0.20,
            'realtime': 0.20
        }
        self.two_evaluator_weights = {
            'synthetic_historical': {'historical': 0.75, 'synthetic': 0.25},
            'synthetic_realtime': {'synthetic': 0.60, 'realtime': 0.40},
            'historical_realtime': {'historical': 0.75, 'realtime': 0.25}
        }
        self.initial_balance = 10000.0
        self.synthetic_bars = 3000
        self.historical_bars = 3000
        self.realtime_duration_minutes = 60
        self.symbol = 'EURUSD'

    @property
    def include_synthetic(self) -> bool:
        """是否启用合成数据评估"""
        return self.enabled_evaluators.get('synthetic', True)

    @property
    def include_historical(self) -> bool:
        """是否启用历史数据评估"""
        return self.enabled_evaluators.get('historical', False)

    @property
    def include_realtime(self) -> bool:
        """是否启用实时数据评估"""
        return self.enabled_evaluators.get('realtime', False)

    def get_weights_for_combination(self, active_evaluators: list) -> Dict[str, float]:
        """
        根据启用的评估器组合，获取对应的权重

        Args:
            active_evaluators: 启用的评估器列表，如 ['synthetic', 'historical']

        Returns:
            权重字典
        """
        # 只有一个评估器
        if len(active_evaluators) == 1:
            return {active_evaluators[0]: 1.0}

        # 两个评估器
        if len(active_evaluators) == 2:
            sorted_evals = sorted(active_evaluators)
            combo_key = '_'.join(sorted_evals)

            # 查找配置的权重
            if combo_key in self.two_evaluator_weights:
                return self.two_evaluator_weights[combo_key]

            # 如果没有配置，使用默认
            if 'synthetic' in active_evaluators and 'historical' in active_evaluators:
                return {'historical': 0.75, 'synthetic': 0.25}
            elif 'synthetic' in active_evaluators and 'realtime' in active_evaluators:
                return {'synthetic': 0.60, 'realtime': 0.40}
            elif 'historical' in active_evaluators and 'realtime' in active_evaluators:
                return {'historical': 0.75, 'realtime': 0.25}

        # 三个评估器：使用配置的权重
        if len(active_evaluators) == 3:
            return self.weights.copy()

        # 默认均分
        equal_weight = 1.0 / len(active_evaluators)
        return {eval_type: equal_weight for eval_type in active_evaluators}

    def to_dict(self) -> Dict:
        """导出配置为字典"""
        return {
            'enabled_evaluators': self.enabled_evaluators,
            'weights': self.weights,
            'two_evaluator_weights': self.two_evaluator_weights,
            'parameters': {
                'initial_balance': self.initial_balance,
                'synthetic_bars': self.synthetic_bars,
                'historical_bars': self.historical_bars,
                'realtime_duration_minutes': self.realtime_duration_minutes,
                'symbol': self.symbol
            }
        }

    def __repr__(self):
        """字符串表示"""
        return (
            f"EvaluationConfig(\n"
            f"  enabled: {self.enabled_evaluators},\n"
            f"  weights: {self.weights},\n"
            f"  initial_balance: {self.initial_balance},\n"
            f"  symbol: {self.symbol}\n"
            f")"
        )


# 全局配置实例（单例模式）
_global_config: Optional[EvaluationConfig] = None


def get_evaluation_config(config_path: Optional[str] = None) -> EvaluationConfig:
    """
    获取全局评估配置实例

    Args:
        config_path: 配置文件路径（可选）

    Returns:
        配置实例
    """
    global _global_config

    if _global_config is None or config_path is not None:
        _global_config = EvaluationConfig(config_path)

    return _global_config
