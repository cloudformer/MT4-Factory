"""信号编排服务"""
from src.common.models.signal import Signal, SignalStatus, Direction
from src.common.models.strategy import Strategy
from src.common.utils.id_generator import generate_signal_id
from src.common.mt5 import get_mt5_client
from ..repository.signal_repo import SignalRepository
from .strategy_runner import StrategyRunner


class SignalOrchestrator:
    """信号编排业务逻辑"""

    def __init__(self, signal_repo: SignalRepository):
        self.signal_repo = signal_repo
        self.strategy_runner = StrategyRunner()
        self.mt5_client = get_mt5_client()

    def generate_signal(self, strategy: Strategy, symbol: str) -> Signal:
        """
        基于策略生成交易信号

        Args:
            strategy: 策略对象
            symbol: 交易品种

        Returns:
            Signal对象
        """
        # 1. 初始化MT5
        if not self.mt5_client.initialize():
            raise RuntimeError("MT5初始化失败")

        # 2. 获取市场数据
        market_data = self.mt5_client.get_bars(symbol, timeframe="H1", count=100)

        if market_data.empty:
            raise ValueError(f"无法获取 {symbol} 的市场数据")

        # 3. 执行策略，获取信号
        signal_direction = self.strategy_runner.execute(strategy.code, market_data)

        if signal_direction is None:
            raise ValueError("策略未产生信号")

        # 4. 创建信号对象
        signal = Signal(
            id=generate_signal_id(),
            strategy_id=strategy.id,
            symbol=symbol,
            direction=Direction.BUY if signal_direction == 'buy' else Direction.SELL,
            volume=0.01,  # TODO: 根据资金分配计算
            status=SignalStatus.PENDING
        )

        # 5. 保存到数据库
        signal = self.signal_repo.create(signal)

        return signal

    def get_all_signals(self):
        """获取所有信号"""
        return self.signal_repo.session.query(Signal).order_by(Signal.created_at.desc()).limit(50).all()
