"""平台检测API路由"""
import platform
from fastapi import APIRouter

router = APIRouter(prefix="/platform", tags=["platform"])


@router.get("/info")
async def get_platform_info():
    """
    获取平台信息

    Returns:
        平台类型、是否Mock模式等信息
    """
    system = platform.system()
    is_windows = system == "Windows"
    is_mock = not is_windows

    return {
        "code": 0,
        "message": "获取成功",
        "data": {
            "system": system,
            "is_windows": is_windows,
            "is_mock": is_mock,
            "platform_name": "Windows" if is_windows else "macOS/Linux",
            "mt5_mode": "Real" if is_windows else "Mock"
        }
    }
