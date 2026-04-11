"""MT5 客户端工厂"""
import platform

from .interface import MT5Interface, OrderRequest, OrderResult, AccountInfo, TickInfo
from .mock_client import MockMT5Client
from .real_client import RealMT5Client
from .connection import MT5ConnectionManager, mt5_manager


def get_mt5_client() -> MT5Interface:
    """
    根据操作系统自动选择 MT5 实现

    - Windows: RealMT5Client (真实交易)
    - macOS/Linux: MockMT5Client (模拟交易)

    Returns:
        MT5Interface: MT5客户端实例

    Note: 推荐使用 mt5_manager 全局单例
    """
    system = platform.system()

    if system == "Windows":
        print("✅ 检测到 Windows 系统，使用真实 MT5")
        return RealMT5Client()
    else:
        print(f"⚠️  检测到 {system} 系统，使用 Mock MT5（开发模式）")
        return MockMT5Client()


# 导出
__all__ = [
    'MT5Interface',
    'MockMT5Client',
    'RealMT5Client',
    'MT5ConnectionManager',
    'mt5_manager',
    'get_mt5_client',
    'OrderRequest',
    'OrderResult',
    'AccountInfo',
    'TickInfo'
]
