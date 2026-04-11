"""账户数据库管理API路由"""
from typing import List, Optional
import platform
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.services.orchestrator.service.account_service import AccountService
from src.common.mt5.connection import mt5_manager

router = APIRouter(prefix="/accounts-db", tags=["accounts-db"])
account_service = AccountService()


# ===== 请求/响应模型 =====

class CreateAccountRequest(BaseModel):
    """创建账户请求"""
    login: int = Field(..., description="MT5账号")
    server: str = Field(..., description="MT5服务器")
    company: str = Field(..., description="MT5公司")
    name: str = Field(..., description="账户名称")
    currency: str = Field(default="USD", description="账户货币")
    leverage: int = Field(default=100, description="杠杆")
    initial_balance: float = Field(..., description="初始资金")
    risk_config: Optional[dict] = Field(default=None, description="风险配置")
    notes: str = Field(default="", description="备注")


class UpdateAccountRequest(BaseModel):
    """更新账户请求"""
    name: Optional[str] = None
    is_active: Optional[bool] = None
    trade_allowed: Optional[bool] = None
    risk_config: Optional[dict] = None
    notes: Optional[str] = None


class AllocationItem(BaseModel):
    """策略配比项"""
    strategy_id: str = Field(..., description="策略ID")
    allocation_percentage: float = Field(..., description="配比百分比(0-1)")


class SetAllocationsRequest(BaseModel):
    """设置配比请求"""
    allocations: List[AllocationItem] = Field(..., description="配比列表")


class SyncAccountRequest(BaseModel):
    """同步账户请求"""
    balance: float = Field(..., description="当前余额")
    equity: float = Field(..., description="当前净值")


# ===== API路由 =====

@router.post("")
async def create_account(request: CreateAccountRequest):
    """创建新账户"""
    try:
        account = account_service.create_account(
            login=request.login,
            server=request.server,
            company=request.company,
            name=request.name,
            currency=request.currency,
            leverage=request.leverage,
            initial_balance=request.initial_balance,
            risk_config=request.risk_config,
            notes=request.notes
        )

        return {
            "code": 0,
            "message": "账户创建成功",
            "data": {
                "id": account.id,
                "login": account.login,
                "name": account.name,
                "initial_balance": account.initial_balance
            }
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("")
async def get_accounts(is_active: Optional[bool] = None):
    """获取所有账户"""
    try:
        # 平台检测
        system = platform.system()
        is_windows = system == "Windows"
        is_mock = not is_windows
        sync_status = None

        # Windows系统自动同步MT5数据
        if is_windows:
            try:
                # 连接MT5
                connected = mt5_manager.connect(use_investor=False)

                if connected:
                    # 获取账户信息
                    client = mt5_manager.get_client()
                    account_info = client.account_info()

                    # 同步所有账户
                    accounts = account_service.get_all_accounts(is_active=is_active)
                    for acc in accounts:
                        if acc.login == account_info.login:
                            account_service.sync_account_from_mt5(
                                account_id=acc.id,
                                balance=account_info.balance,
                                equity=account_info.equity
                            )

                    sync_status = {
                        "success": True,
                        "message": "✅ MT5连接成功，数据已同步",
                        "balance": account_info.balance,
                        "equity": account_info.equity
                    }

                    mt5_manager.disconnect()
                else:
                    sync_status = {
                        "success": False,
                        "message": "⚠️ MT5连接失败，显示数据库缓存数据",
                        "error_type": "connection_failed",
                        "solutions": [
                            "1. 确认MetaTrader5终端是否正在运行",
                            "2. 检查MT5账号是否已登录",
                            "3. 验证配置文件中的Login/Password是否正确"
                        ]
                    }
            except ModuleNotFoundError as e:
                # MT5 Python包未安装
                sync_status = {
                    "success": False,
                    "message": "❌ MT5未安装：MetaTrader5 Python包未找到",
                    "error_type": "module_not_found",
                    "error_detail": str(e),
                    "solutions": [
                        "1. 安装MetaTrader5 Python包：",
                        "   pip install MetaTrader5",
                        "",
                        "2. 如果已安装但仍报错，重新安装：",
                        "   pip uninstall MetaTrader5",
                        "   pip install MetaTrader5"
                    ]
                }
            except ImportError as e:
                # MT5终端未安装或找不到
                if "MetaTrader 5" in str(e) or "terminal" in str(e).lower():
                    sync_status = {
                        "success": False,
                        "message": "❌ MT5未安装：找不到MetaTrader5终端",
                        "error_type": "mt5_not_installed",
                        "error_detail": str(e),
                        "solutions": [
                            "1. 下载并安装MetaTrader5终端：",
                            "   https://www.metatrader5.com/zh/download",
                            "",
                            "2. 安装后重新启动应用",
                            "",
                            "3. 确保MT5终端安装在默认路径：",
                            "   C:\\Program Files\\MetaTrader 5"
                        ]
                    }
                else:
                    sync_status = {
                        "success": False,
                        "message": f"❌ 导入错误: {str(e)}",
                        "error_type": "import_error",
                        "error_detail": str(e),
                        "solutions": [
                            "1. 检查Python环境配置",
                            "2. 重新安装依赖包"
                        ]
                    }
            except Exception as e:
                # 其他错误
                error_msg = str(e).lower()
                if "initialize" in error_msg or "找不到" in error_msg:
                    sync_status = {
                        "success": False,
                        "message": "❌ MT5初始化失败：可能未安装MT5终端",
                        "error_type": "initialization_failed",
                        "error_detail": str(e),
                        "solutions": [
                            "1. 安装MetaTrader5终端：",
                            "   https://www.metatrader5.com/zh/download",
                            "",
                            "2. 确保MT5终端已完全安装并可正常启动",
                            "",
                            "3. 重启应用重试"
                        ]
                    }
                elif "login" in error_msg or "authorization" in error_msg:
                    sync_status = {
                        "success": False,
                        "message": "❌ MT5登录失败：账号或密码错误",
                        "error_type": "login_failed",
                        "error_detail": str(e),
                        "solutions": [
                            "1. 检查配置文件中的MT5账号（Login）",
                            "2. 验证MT5密码（Password）是否正确",
                            "3. 确认服务器地址（Server）是否正确"
                        ]
                    }
                else:
                    sync_status = {
                        "success": False,
                        "message": f"⚠️ MT5同步失败: {str(e)}",
                        "error_type": "unknown_error",
                        "error_detail": str(e),
                        "solutions": [
                            "1. 查看详细错误信息",
                            "2. 检查MT5终端是否正常运行",
                            "3. 联系技术支持"
                        ]
                    }

        # 重新获取账户（获取最新同步后的数据）
        accounts = account_service.get_all_accounts(is_active=is_active)

        return {
            "code": 0,
            "message": "获取成功",
            "platform": {
                "system": system,
                "is_windows": is_windows,
                "is_mock": is_mock,
                "mt5_mode": "Real" if is_windows else "Mock",
                "sync_status": sync_status
            },
            "data": [
                {
                    "id": acc.id,
                    "login": acc.login,
                    "server": acc.server,
                    "company": acc.company,
                    "name": acc.name,
                    "currency": acc.currency,
                    "initial_balance": acc.initial_balance,
                    "current_balance": acc.current_balance,
                    "current_equity": acc.current_equity,
                    "is_active": acc.is_active,
                    "trade_allowed": acc.trade_allowed,
                    "start_time": acc.start_time.isoformat() if acc.start_time else None,
                    "last_sync_time": acc.last_sync_time.isoformat() if acc.last_sync_time else None
                }
                for acc in accounts
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{account_id}")
async def get_account(account_id: str):
    """获取账户详情（包含策略配比）"""
    try:
        result = account_service.get_account_with_allocations(account_id)

        if not result:
            raise HTTPException(status_code=404, detail="账户不存在")

        account = result["account"]
        allocations = result["allocations"]

        return {
            "code": 0,
            "message": "获取成功",
            "data": {
                "account": {
                    "id": account.id,
                    "login": account.login,
                    "server": account.server,
                    "company": account.company,
                    "name": account.name,
                    "currency": account.currency,
                    "leverage": account.leverage,
                    "initial_balance": account.initial_balance,
                    "current_balance": account.current_balance,
                    "current_equity": account.current_equity,
                    "is_active": account.is_active,
                    "trade_allowed": account.trade_allowed,
                    "risk_config": account.risk_config,
                    "start_time": account.start_time.isoformat() if account.start_time else None,
                    "last_sync_time": account.last_sync_time.isoformat() if account.last_sync_time else None,
                    "notes": account.notes
                },
                "allocations": [
                    {
                        "id": alloc.id,
                        "strategy_id": alloc.strategy_id,
                        "allocation_percentage": alloc.allocation_percentage,
                        "is_active": alloc.is_active
                    }
                    for alloc in allocations
                ]
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{account_id}")
async def update_account(account_id: str, request: UpdateAccountRequest):
    """更新账户信息"""
    try:
        account = account_service.update_account(
            account_id=account_id,
            name=request.name,
            is_active=request.is_active,
            trade_allowed=request.trade_allowed,
            risk_config=request.risk_config,
            notes=request.notes
        )

        if not account:
            raise HTTPException(status_code=404, detail="账户不存在")

        return {
            "code": 0,
            "message": "更新成功",
            "data": {
                "id": account.id,
                "name": account.name,
                "is_active": account.is_active,
                "trade_allowed": account.trade_allowed
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{account_id}")
async def delete_account(account_id: str):
    """删除账户"""
    try:
        success = account_service.delete_account(account_id)

        if not success:
            raise HTTPException(status_code=404, detail="账户不存在")

        return {
            "code": 0,
            "message": "删除成功"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{account_id}/allocations")
async def set_allocations(account_id: str, request: SetAllocationsRequest):
    """设置账户的策略配比"""
    try:
        allocations = [
            {
                "strategy_id": item.strategy_id,
                "allocation_percentage": item.allocation_percentage
            }
            for item in request.allocations
        ]

        success = account_service.set_allocations(account_id, allocations)

        return {
            "code": 0,
            "message": "配比设置成功"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{account_id}/summary")
async def get_account_summary(account_id: str):
    """获取账户盈利统计"""
    try:
        summary = account_service.get_account_summary(account_id)

        if not summary:
            raise HTTPException(status_code=404, detail="账户不存在")

        return {
            "code": 0,
            "message": "获取成功",
            "data": summary
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{account_id}/sync")
async def sync_account(account_id: str, request: SyncAccountRequest):
    """同步账户信息（从MT5）"""
    try:
        success = account_service.sync_account_from_mt5(
            account_id=account_id,
            balance=request.balance,
            equity=request.equity
        )

        if not success:
            raise HTTPException(status_code=404, detail="账户不存在")

        return {
            "code": 0,
            "message": "同步成功"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
