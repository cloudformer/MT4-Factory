"""信号数据访问层"""
from typing import List, Optional
from sqlalchemy.orm import Session

from src.common.models.signal import Signal, SignalStatus


class SignalRepository:
    """信号数据访问对象"""

    def __init__(self, session: Session):
        self.session = session

    def create(self, signal: Signal) -> Signal:
        """创建信号"""
        self.session.add(signal)
        self.session.flush()
        return signal

    def get_by_id(self, signal_id: str) -> Optional[Signal]:
        """根据ID获取信号"""
        return self.session.query(Signal).filter(Signal.id == signal_id).first()

    def get_by_status(self, status: SignalStatus) -> List[Signal]:
        """根据状态获取信号"""
        return self.session.query(Signal).filter(Signal.status == status).all()

    def get_pending_signals(self) -> List[Signal]:
        """获取待执行的信号"""
        return self.get_by_status(SignalStatus.PENDING)

    def update_status(self, signal_id: str, status: SignalStatus) -> bool:
        """更新信号状态"""
        signal = self.get_by_id(signal_id)
        if signal:
            signal.status = status
            self.session.flush()
            return True
        return False
