"""策略执行引擎"""
import pandas as pd
from typing import Optional


class StrategyRunner:
    """动态加载和执行策略代码"""

    def load_strategy(self, strategy_code: str):
        """
        加载策略代码，返回策略实例

        Args:
            strategy_code: 策略的 Python 代码字符串

        Returns:
            策略实例
        """
        namespace = {}
        exec(strategy_code, namespace)

        # 找到策略类（以 Strategy_ 开头）
        strategy_class = None
        for name, obj in namespace.items():
            if name.startswith('Strategy_'):
                strategy_class = obj
                break

        if strategy_class is None:
            raise ValueError("策略代码中未找到 Strategy_ 类")

        return strategy_class()

    def run_strategy(self, strategy_instance, market_data: pd.DataFrame) -> Optional[str]:
        """
        执行策略，返回交易信号

        Args:
            strategy_instance: 策略实例
            market_data: 市场数据 DataFrame

        Returns:
            'buy', 'sell', or None
        """
        try:
            signal = strategy_instance.on_tick(market_data)
            return signal
        except Exception as e:
            print(f"❌ 策略执行错误: {e}")
            return None

    def execute(self, strategy_code: str, market_data: pd.DataFrame) -> Optional[str]:
        """
        一步执行：加载 + 运行

        Args:
            strategy_code: 策略代码
            market_data: 市场数据

        Returns:
            'buy', 'sell', or None
        """
        strategy = self.load_strategy(strategy_code)
        return self.run_strategy(strategy, market_data)
