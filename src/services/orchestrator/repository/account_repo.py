"""账户仓储层"""
from typing import List, Optional
from sqlalchemy.orm import Session
from datetime import datetime

from src.common.database.connection import db
from src.common.models.account import Account
from src.common.models.account_allocation import AccountAllocation
from src.common.utils.id_generator import generate_id


class AccountRepository:
    """账户数据访问对象"""

    def __init__(self):
        self.db = db

    def create(self, account: Account) -> Account:
        """创建账户"""
        with self.db.session_scope() as session:
            session.add(account)
            session.commit()
            session.refresh(account)
            return account

    def get_by_id(self, account_id: str) -> Optional[Account]:
        """根据ID获取账户"""
        with self.db.session_scope() as session:
            account = session.query(Account).filter(Account.id == account_id).first()
            if account:
                # 显式访问所有属性以确保加载
                _ = (account.id, account.login, account.server, account.company, account.name,
                     account.currency, account.leverage, account.initial_balance, account.start_time,
                     account.current_balance, account.current_equity, account.last_sync_time,
                     account.is_active, account.trade_allowed, account.risk_config, account.notes,
                     account.created_at, account.updated_at)
                session.expunge(account)
            return account

    def get_by_login(self, login: int) -> Optional[Account]:
        """根据MT5账号获取账户"""
        with self.db.session_scope() as session:
            account = session.query(Account).filter(Account.login == login).first()
            if account:
                _ = (account.id, account.login, account.server, account.company, account.name,
                     account.currency, account.leverage, account.initial_balance, account.start_time,
                     account.current_balance, account.current_equity, account.last_sync_time,
                     account.is_active, account.trade_allowed, account.risk_config, account.notes,
                     account.created_at, account.updated_at)
                session.expunge(account)
            return account

    def get_all(self, is_active: Optional[bool] = None) -> List[Account]:
        """获取所有账户"""
        with self.db.session_scope() as session:
            query = session.query(Account)
            if is_active is not None:
                query = query.filter(Account.is_active == is_active)
            accounts = query.order_by(Account.created_at.desc()).all()
            # 显式访问所有属性以确保加载
            for acc in accounts:
                _ = (acc.id, acc.login, acc.server, acc.company, acc.name,
                     acc.currency, acc.leverage, acc.initial_balance, acc.start_time,
                     acc.current_balance, acc.current_equity, acc.last_sync_time,
                     acc.is_active, acc.trade_allowed, acc.risk_config, acc.notes,
                     acc.created_at, acc.updated_at)
            session.expunge_all()
            return accounts

    def update(self, account: Account) -> Account:
        """更新账户"""
        with self.db.session_scope() as session:
            account.updated_at = datetime.now()
            session.merge(account)
            session.commit()
            return account

    def delete(self, account_id: str) -> bool:
        """删除账户"""
        with self.db.session_scope() as session:
            account = session.query(Account).filter(Account.id == account_id).first()
            if account:
                session.delete(account)
                session.commit()
                return True
            return False

    # ===== 账户同步 =====

    def sync_account_info(self, account_id: str, balance: float, equity: float) -> bool:
        """同步账户信息（从MT5）"""
        with self.db.session_scope() as session:
            account = session.query(Account).filter(Account.id == account_id).first()
            if not account:
                return False

            account.current_balance = balance
            account.current_equity = equity
            account.last_sync_time = datetime.now()
            account.updated_at = datetime.now()

            session.commit()
            return True


class AccountAllocationRepository:
    """账户策略配比数据访问对象"""

    def __init__(self):
        self.db = db

    def create(self, allocation: AccountAllocation) -> AccountAllocation:
        """创建配比记录"""
        with self.db.session_scope() as session:
            session.add(allocation)
            session.commit()
            session.refresh(allocation)
            return allocation

    def get_by_id(self, allocation_id: str) -> Optional[AccountAllocation]:
        """根据ID获取配比"""
        with self.db.session_scope() as session:
            return session.query(AccountAllocation).filter(
                AccountAllocation.id == allocation_id
            ).first()

    def get_by_account(self, account_id: str, is_active: Optional[bool] = None) -> List[AccountAllocation]:
        """获取账户的所有策略配比"""
        with self.db.session_scope() as session:
            query = session.query(AccountAllocation).filter(
                AccountAllocation.account_id == account_id
            )
            if is_active is not None:
                query = query.filter(AccountAllocation.is_active == is_active)
            allocations = query.order_by(AccountAllocation.allocation_percentage.desc()).all()
            # 显式访问所有属性以确保加载
            for alloc in allocations:
                _ = (alloc.id, alloc.account_id, alloc.strategy_id,
                     alloc.allocation_percentage, alloc.is_active,
                     alloc.created_at, alloc.updated_at)
            session.expunge_all()
            return allocations

    def get_by_account_strategy(self, account_id: str, strategy_id: str) -> Optional[AccountAllocation]:
        """获取特定账户的特定策略配比"""
        with self.db.session_scope() as session:
            return session.query(AccountAllocation).filter(
                AccountAllocation.account_id == account_id,
                AccountAllocation.strategy_id == strategy_id
            ).first()

    def update(self, allocation: AccountAllocation) -> AccountAllocation:
        """更新配比"""
        with self.db.session_scope() as session:
            allocation.updated_at = datetime.now()
            session.merge(allocation)
            session.commit()
            return allocation

    def delete(self, allocation_id: str) -> bool:
        """删除配比记录"""
        with self.db.session_scope() as session:
            allocation = session.query(AccountAllocation).filter(
                AccountAllocation.id == allocation_id
            ).first()
            if allocation:
                session.delete(allocation)
                session.commit()
                return True
            return False

    def set_allocations(self, account_id: str, allocations: List[dict]) -> bool:
        """
        批量设置账户的策略配比

        Args:
            account_id: 账户ID
            allocations: 配比列表 [{"strategy_id": "...", "allocation_percentage": 0.3}, ...]

        Returns:
            是否成功
        """
        with self.db.session_scope() as session:
            # 1. 获取现有配比
            existing = session.query(AccountAllocation).filter(
                AccountAllocation.account_id == account_id
            ).all()

            # 2. 创建策略ID到配比对象的映射
            existing_map = {alloc.strategy_id: alloc for alloc in existing}

            # 3. 处理新配比
            new_strategy_ids = set()
            for alloc_data in allocations:
                strategy_id = alloc_data['strategy_id']
                percentage = alloc_data['allocation_percentage']
                new_strategy_ids.add(strategy_id)

                if strategy_id in existing_map:
                    # 更新现有配比
                    existing_alloc = existing_map[strategy_id]
                    existing_alloc.allocation_percentage = percentage
                    existing_alloc.is_active = True
                    existing_alloc.updated_at = datetime.now()
                else:
                    # 创建新配比
                    new_alloc = AccountAllocation(
                        id=generate_id("ALLOC"),
                        account_id=account_id,
                        strategy_id=strategy_id,
                        allocation_percentage=percentage,
                        is_active=True
                    )
                    session.add(new_alloc)

            # 4. 停用不再使用的策略（设为is_active=False，不删除历史记录）
            for strategy_id, alloc in existing_map.items():
                if strategy_id not in new_strategy_ids:
                    alloc.is_active = False
                    alloc.updated_at = datetime.now()

            session.commit()
            return True
