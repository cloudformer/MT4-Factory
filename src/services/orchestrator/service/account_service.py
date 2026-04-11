"""账户管理服务"""
from typing import List, Optional, Dict, Any
from datetime import datetime

from src.common.models.account import Account
from src.common.models.account_allocation import AccountAllocation
from src.common.models.trade import Trade
from src.common.utils.id_generator import generate_id
from src.services.orchestrator.repository.account_repo import (
    AccountRepository,
    AccountAllocationRepository
)
from src.services.orchestrator.repository.trade_repo import TradeRepository


class AccountService:
    """账户管理服务 - 处理账户业务逻辑"""

    def __init__(self):
        self.account_repo = AccountRepository()
        self.allocation_repo = AccountAllocationRepository()
        self.trade_repo = TradeRepository()

    # ===== 账户管理 =====

    def create_account(
        self,
        login: int,
        server: str,
        company: str,
        name: str,
        currency: str = "USD",
        leverage: int = 100,
        initial_balance: float = 10000.0,
        risk_config: Optional[Dict] = None,
        notes: str = ""
    ) -> Account:
        """
        创建新账户

        Args:
            login: MT5账号
            server: MT5服务器
            company: MT5公司
            name: 账户名称
            currency: 账户货币
            leverage: 杠杆
            initial_balance: 初始资金
            risk_config: 风险配置
            notes: 备注

        Returns:
            创建的账户对象

        Raises:
            ValueError: 参数验证失败
            Exception: 账号已存在
        """
        # 1. 验证参数
        if initial_balance <= 0:
            raise ValueError("初始资金必须大于0")

        if leverage <= 0:
            raise ValueError("杠杆必须大于0")

        # 2. 检查账号是否已存在
        existing = self.account_repo.get_by_login(login)
        if existing:
            raise Exception(f"账号 {login} 已存在")

        # 3. 设置默认风险配置
        if risk_config is None:
            risk_config = {
                "max_daily_loss": 0.05,
                "max_total_exposure": 0.30,
                "max_concurrent_trades": 10
            }

        # 4. 创建账户对象
        account = Account(
            id=generate_id("ACC"),
            login=login,
            server=server,
            company=company,
            name=name,
            currency=currency,
            leverage=leverage,
            initial_balance=initial_balance,
            start_time=datetime.now(),
            current_balance=initial_balance,
            current_equity=initial_balance,
            last_sync_time=datetime.now(),
            is_active=True,
            trade_allowed=True,
            risk_config=risk_config,
            notes=notes
        )

        # 5. 保存到数据库
        return self.account_repo.create(account)

    def get_account(self, account_id: str) -> Optional[Account]:
        """获取账户"""
        return self.account_repo.get_by_id(account_id)

    def get_all_accounts(self, is_active: Optional[bool] = None) -> List[Account]:
        """获取所有账户"""
        return self.account_repo.get_all(is_active=is_active)

    def update_account(
        self,
        account_id: str,
        name: Optional[str] = None,
        is_active: Optional[bool] = None,
        trade_allowed: Optional[bool] = None,
        risk_config: Optional[Dict] = None,
        notes: Optional[str] = None
    ) -> Optional[Account]:
        """
        更新账户信息

        Args:
            account_id: 账户ID
            name: 新名称
            is_active: 是否激活
            trade_allowed: 是否允许交易
            risk_config: 风险配置
            notes: 备注

        Returns:
            更新后的账户对象
        """
        account = self.account_repo.get_by_id(account_id)
        if not account:
            return None

        # 更新字段
        if name is not None:
            account.name = name
        if is_active is not None:
            account.is_active = is_active
        if trade_allowed is not None:
            account.trade_allowed = trade_allowed
        if risk_config is not None:
            account.risk_config = risk_config
        if notes is not None:
            account.notes = notes

        return self.account_repo.update(account)

    def delete_account(self, account_id: str) -> bool:
        """删除账户"""
        return self.account_repo.delete(account_id)

    # ===== 策略配比管理 =====

    def get_account_with_allocations(self, account_id: str) -> Optional[Dict[str, Any]]:
        """
        获取账户及其策略配比

        Returns:
            {
                "account": Account对象,
                "allocations": [AccountAllocation列表]
            }
        """
        account = self.account_repo.get_by_id(account_id)
        if not account:
            return None

        allocations = self.allocation_repo.get_by_account(account_id, is_active=True)

        return {
            "account": account,
            "allocations": allocations
        }

    def set_allocations(
        self,
        account_id: str,
        allocations: List[Dict[str, Any]]
    ) -> bool:
        """
        设置账户的策略配比

        Args:
            account_id: 账户ID
            allocations: 配比列表 [{"strategy_id": "...", "allocation_percentage": 0.3}, ...]

        Returns:
            是否成功

        Raises:
            ValueError: 配比总和不等于1
            Exception: 账户不存在
        """
        # 1. 验证账户存在
        account = self.account_repo.get_by_id(account_id)
        if not account:
            raise Exception(f"账户 {account_id} 不存在")

        # 2. 验证配比总和
        total_percentage = sum(a["allocation_percentage"] for a in allocations)
        if abs(total_percentage - 1.0) > 0.001:  # 允许浮点误差
            raise ValueError(f"配比总和必须为1.0，当前为 {total_percentage}")

        # 3. 验证每个配比在0-1之间
        for alloc in allocations:
            percentage = alloc["allocation_percentage"]
            if percentage < 0 or percentage > 1:
                raise ValueError(f"配比必须在0-1之间，当前为 {percentage}")

        # 4. 批量设置配比
        return self.allocation_repo.set_allocations(account_id, allocations)

    # ===== 盈利统计 =====

    def get_account_summary(self, account_id: str) -> Optional[Dict[str, Any]]:
        """
        获取账户盈利统计

        Returns:
            {
                "account_id": "账户ID",
                "account_name": "账户名称",
                "start_time": "上线时间",
                "initial_balance": 初始资金,
                "current_balance": 当前资金,
                "current_equity": 当前净值,
                "total_pnl": 总盈亏,
                "total_pnl_percentage": 盈亏百分比,
                "trade_count": 交易数,
                "win_count": 盈利交易数,
                "loss_count": 亏损交易数,
                "win_rate": 胜率,
                "max_drawdown": 最大回撤,
                "max_drawdown_percentage": 最大回撤百分比
            }
        """
        # 1. 获取账户信息
        account = self.account_repo.get_by_id(account_id)
        if not account:
            return None

        # 2. 获取该账户的所有交易记录
        trades = self.trade_repo.get_by_account(account_id)

        # 3. 计算统计数据
        trade_count = len(trades)
        win_count = sum(1 for t in trades if t.profit and t.profit > 0)
        loss_count = sum(1 for t in trades if t.profit and t.profit < 0)
        win_rate = win_count / trade_count if trade_count > 0 else 0.0

        # 总盈亏
        total_pnl = account.current_balance - account.initial_balance
        total_pnl_percentage = total_pnl / account.initial_balance if account.initial_balance > 0 else 0.0

        # 计算最大回撤
        max_drawdown = 0.0
        max_drawdown_percentage = 0.0

        if trades:
            # 按时间排序
            sorted_trades = sorted(trades, key=lambda t: t.open_time)

            # 模拟资金曲线
            balance = account.initial_balance
            peak_balance = balance

            for trade in sorted_trades:
                if trade.profit:
                    balance += trade.profit

                    # 更新峰值
                    if balance > peak_balance:
                        peak_balance = balance

                    # 计算回撤
                    drawdown = peak_balance - balance
                    if drawdown > max_drawdown:
                        max_drawdown = drawdown
                        max_drawdown_percentage = drawdown / peak_balance if peak_balance > 0 else 0.0

        return {
            "account_id": account.id,
            "account_name": account.name,
            "start_time": account.start_time.isoformat() if account.start_time else None,
            "initial_balance": account.initial_balance,
            "current_balance": account.current_balance,
            "current_equity": account.current_equity,
            "total_pnl": total_pnl,
            "total_pnl_percentage": total_pnl_percentage,
            "trade_count": trade_count,
            "win_count": win_count,
            "loss_count": loss_count,
            "win_rate": win_rate,
            "max_drawdown": max_drawdown,
            "max_drawdown_percentage": max_drawdown_percentage
        }

    # ===== MT5同步 =====

    def sync_account_from_mt5(self, account_id: str, balance: float, equity: float) -> bool:
        """
        从MT5同步账户信息

        Args:
            account_id: 账户ID
            balance: 当前余额
            equity: 当前净值

        Returns:
            是否同步成功
        """
        return self.account_repo.sync_account_info(account_id, balance, equity)
