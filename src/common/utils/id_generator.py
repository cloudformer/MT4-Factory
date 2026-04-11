"""ID 生成器"""
import uuid


def generate_strategy_id() -> str:
    """生成策略ID"""
    return f"STR_{uuid.uuid4().hex[:8]}"


def generate_signal_id() -> str:
    """生成信号ID"""
    return f"SIG_{uuid.uuid4().hex[:8]}"


def generate_trade_id() -> str:
    """生成交易ID"""
    return f"TRD_{uuid.uuid4().hex[:8]}"
