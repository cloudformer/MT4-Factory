"""合成数据评估器 - 使用模拟/随机数据进行回测"""
from typing import Dict
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

from .base_evaluator import BaseEvaluator


class SyntheticDataEvaluator(BaseEvaluator):
    """合成数据评估器 - 使用模拟数据进行回测"""

    def evaluate(self, strategy_code: str, symbol: str = "EURUSD", bars: int = 3000) -> Dict:
        """
        使用合成数据评估策略

        Args:
            strategy_code: 策略代码
            symbol: 交易品种
            bars: K线数量

        Returns:
            性能指标字典，包含 'data_source': 'synthetic'
        """
        print(f"   📊 生成合成数据：{symbol} x {bars}根K线...")

        # 1. 生成模拟数据
        historical_data = self._generate_synthetic_data(symbol, bars)

        # 2. 运行回测（传递symbol）
        metrics = self.run_backtest(strategy_code, historical_data, symbol=symbol)

        # 3. 标记数据来源
        metrics['data_source'] = 'synthetic'
        metrics['data_symbol'] = symbol
        metrics['backtest_date'] = datetime.now().isoformat()

        return metrics

    def _generate_synthetic_data(self, symbol: str, bars: int) -> pd.DataFrame:
        """
        生成模拟历史数据

        策略：
        - 使用随机游走模拟价格
        - 添加市场制度切换（趋势/震荡交替）
        - 模拟真实外汇市场的波动特征

        Args:
            symbol: 交易品种
            bars: K线数量

        Returns:
            DataFrame with columns: time, open, high, low, close, volume
        """
        # 生成日期（H1周期）
        end_date = datetime.now()
        dates = pd.date_range(end=end_date, periods=bars, freq='h')

        # 基础价格
        base_price = 1.0850 if symbol == "EURUSD" else 1.2650

        # 生成价格序列（更真实的随机游走）
        np.random.seed(None)  # 每次不同

        # 1. 基础随机游走（无趋势）
        returns = np.random.normal(0, 0.003, bars)  # 均值0%, 标准差0.3%

        # 2. 添加市场制度切换（震荡/趋势交替）
        regime_length = 200  # 每200根K线切换一次
        for i in range(0, bars, regime_length):
            end_idx = min(i + regime_length, bars)
            # 50%概率趋势，50%概率震荡
            if np.random.rand() > 0.5:
                # 趋势期：添加小趋势
                trend_direction = 1 if np.random.rand() > 0.5 else -1
                trend = np.linspace(0, 0.005 * trend_direction, end_idx - i)
                returns[i:end_idx] += trend
            # else: 震荡期，保持随机游走

        close_prices = base_price * (1 + returns).cumprod()

        # 生成 OHLC
        data = pd.DataFrame({
            'time': dates,
            'open': close_prices * (1 + np.random.uniform(-0.0005, 0.0005, bars)),
            'high': close_prices * (1 + np.random.uniform(0.0002, 0.001, bars)),
            'low': close_prices * (1 - np.random.uniform(0.0002, 0.001, bars)),
            'close': close_prices,
            'volume': np.random.randint(100, 1000, bars)
        })

        return data
