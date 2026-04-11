"""ID 生成器"""
import uuid


def generate_id(prefix: str = "ID") -> str:
    """
    生成通用ID

    Args:
        prefix: ID前缀（例如: ACC, ALLOC, STR等）

    Returns:
        格式为 {prefix}_{随机8位hex} 的ID
    """
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def generate_strategy_id() -> str:
    """生成策略ID"""
    return generate_id("STR")


def generate_signal_id() -> str:
    """生成信号ID"""
    return generate_id("SIG")


def generate_trade_id() -> str:
    """生成交易ID"""
    return generate_id("TRD")


def generate_account_id() -> str:
    """生成账户ID"""
    return generate_id("ACC")


def generate_allocation_id() -> str:
    """生成配比ID"""
    return generate_id("ALLOC")
