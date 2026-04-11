# Evo Trade System - 企业级架构设计文档

> **设计理念**：像资深架构师一样思考，像资深开发一样实现  
> **核心原则**：高内聚低耦合、错误处理完善、模块调用清晰、稳定性第一、强壮性优先

**文档版本**: v2.0  
**最后更新**: 2026-04-10  
**维护者**: Evo Trade Team

---

## 📚 目录

1. [架构概览](#架构概览)
2. [设计原则](#设计原则)
3. [分层架构](#分层架构)
4. [核心设计模式](#核心设计模式)
5. [异常处理体系](#异常处理体系)
6. [日志与监控](#日志与监控)
7. [数据库设计](#数据库设计)
8. [服务间通信](#服务间通信)
9. [配置管理](#配置管理)
10. [测试策略](#测试策略)
11. [性能优化](#性能优化)
12. [安全设计](#安全设计)
13. [部署架构](#部署架构)
14. [代码规范](#代码规范)

---

## 架构概览

### 四层微服务架构

\`\`\`
┌─────────────────────────────────────────────────────────────┐
│                  Dashboard Service (8000)                   │
│               Web UI + 数据展示 + 用户交互                   │
└─────────────────────────────────────────────────────────────┘
                             ↓ REST API
┌─────────────────────────────────────────────────────────────┐
│                Orchestrator Service (8002)                  │
│     策略注册 + 账户管理 + 资金分配 + 风险控制 + 编排调度      │
│  ┌─────────────┬──────────────┬──────────────┬───────────┐ │
│  │ Strategy    │ Account      │ Allocation   │ Risk      │ │
│  │ Registration│ Manager      │ Engine       │ Manager   │ │
│  └─────────────┴──────────────┴──────────────┴───────────┘ │
└─────────────────────────────────────────────────────────────┘
         ↓                                           ↓
┌──────────────────────────┐         ┌─────────────────────────┐
│  Strategy Service (8001) │         │ Execution Service (8003)│
│  策略生成 + 回测 + 评估   │         │ 订单执行 + MT5对接      │
│  信号生成                │         │ 持仓管理 + 账户同步      │
└──────────────────────────┘         └─────────────────────────┘
\`\`\`

### 系统特点

- ✅ **高可用性**: 服务独立部署，故障隔离
- ✅ **高可扩展**: 水平扩展，负载均衡
- ✅ **高可维护**: 清晰分层，职责单一
- ✅ **高可测试**: 依赖注入，Mock友好  
- ✅ **高性能**: 异步处理，连接池，缓存
- ✅ **高安全性**: 输入验证，权限控制，敏感信息加密

---

## 设计原则

### SOLID原则

1. **Single Responsibility (单一职责)**
   - 每个类只有一个改变的理由
   - 示例：`AccountRepository` 只负责数据访问，不包含业务逻辑

2. **Open-Closed (开闭原则)**
   - 对扩展开放，对修改封闭
   - 示例：通过策略模式扩展分配算法，无需修改核心代码

3. **Liskov Substitution (里氏替换)**
   - 子类可以替换父类
   - 示例：`RealMT5Client` 和 `MockMT5Client` 都可替换 `MT5Interface`

4. **Interface Segregation (接口隔离)**
   - 客户端不应依赖它不需要的接口
   - 示例：分离读写接口 `IReadRepository` 和 `IWriteRepository`

5. **Dependency Inversion (依赖倒置)**
   - 依赖抽象而非具体实现
   - 示例：Service 依赖 `IRepository` 接口而非具体实现

### 其他核心原则

6. **Don't Repeat Yourself (DRY)**
   - 避免重复代码
   - 使用继承、组合、工具类

7. **Keep It Simple, Stupid (KISS)**
   - 保持简单
   - 不过度设计

8. **You Aren't Gonna Need It (YAGNI)**
   - 不实现未来"可能"需要的功能
   - 当前需求优先

9. **Principle of Least Astonishment**
   - 代码行为符合直觉
   - 命名清晰，避免意外行为

10. **Fail Fast**
    - 尽早发现错误
    - 输入验证在最外层完成

---

## 分层架构

### 三层架构详解

\`\`\`
┌──────────────────────────────────────────────────────────┐
│                  Presentation Layer                      │
│  📍 位置: src/services/*/api/routes/                     │
│  🎯 职责:                                                 │
│    - HTTP请求/响应处理                                    │
│    - 输入数据验证 (Pydantic)                             │
│    - 输出格式化 (JSON)                                    │
│    - API文档生成 (OpenAPI)                               │
│    - 认证授权检查                                         │
│  ⚠️  禁止:                                                │
│    - ❌ 直接访问数据库                                    │
│    - ❌ 包含业务逻辑                                      │
│    - ❌ 直接调用外部服务                                  │
└──────────────────────────────────────────────────────────┘
                           ↓
┌──────────────────────────────────────────────────────────┐
│                    Business Layer                        │
│  📍 位置: src/services/*/service/                        │
│  🎯 职责:                                                 │
│    - 实现业务逻辑                                         │
│    - 业务规则验证                                         │
│    - 跨Repository事务管理                                │
│    - 业务流程编排                                         │
│    - 领域事件发布                                         │
│    - 调用外部服务                                         │
│  ⚠️  禁止:                                                │
│    - ❌ 依赖HTTP框架                                      │
│    - ❌ 直接操作SQL                                       │
└──────────────────────────────────────────────────────────┘
                           ↓
┌──────────────────────────────────────────────────────────┐
│                 Data Access Layer                        │
│  📍 位置: src/services/*/repository/                     │
│  🎯 职责:                                                 │
│    - 封装数据访问逻辑                                     │
│    - 提供CRUD操作                                        │
│    - 查询优化 (避免N+1)                                  │
│    - 数据库事务管理                                       │
│    - 连接池管理                                           │
│  ⚠️  禁止:                                                │
│    - ❌ 包含业务逻辑                                      │
│    - ❌ 返回Domain对象以外的数据                          │
└──────────────────────────────────────────────────────────┘
                           ↓
┌──────────────────────────────────────────────────────────┐
│                    Infrastructure                        │
│  📍 位置: src/common/                                     │
│    - Database (SQLAlchemy)                               │
│    - Cache (Redis - 未来)                                │
│    - Message Queue (RabbitMQ - 未来)                     │
│    - External APIs (MT5, 第三方服务)                     │
└──────────────────────────────────────────────────────────┘
\`\`\`

### 层级交互规则

**允许的调用方向**：
\`\`\`
Presentation → Business → Data Access → Infrastructure
\`\`\`

**禁止的调用方向**：
\`\`\`
Infrastructure → Data Access  ❌
Data Access → Business        ❌  
Business → Presentation       ❌
\`\`\`

---

## 核心设计模式

### 1. Repository Pattern (仓储模式)

**目的**: 分离数据访问逻辑与业务逻辑

**接口定义**:
\`\`\`python
# src/services/orchestrator/repository/interfaces.py
from abc import ABC, abstractmethod
from typing import Optional, List

class IAccountRepository(ABC):
    """账户仓储接口"""
    
    @abstractmethod
    def create(self, account: Account) -> Account:
        """创建账户"""
        pass
    
    @abstractmethod
    def get_by_id(self, account_id: str) -> Optional[Account]:
        """根据ID获取账户"""
        pass
    
    @abstractmethod
    def get_by_login(self, login: int) -> Optional[Account]:
        """根据MT5账号获取账户"""
        pass
    
    @abstractmethod
    def get_all(self, is_active: Optional[bool] = None) -> List[Account]:
        """获取所有账户"""
        pass
    
    @abstractmethod
    def update(self, account: Account) -> Account:
        """更新账户"""
        pass
    
    @abstractmethod
    def delete(self, account_id: str) -> bool:
        """删除账户"""
        pass
\`\`\`

**实现类**:
\`\`\`python
# src/services/orchestrator/repository/account_repo.py
class AccountRepository(IAccountRepository):
    """SQLAlchemy实现"""
    
    def __init__(self, db: DatabaseConnection, logger: Logger):
        self.db = db
        self.logger = logger
    
    def create(self, account: Account) -> Account:
        """创建账户"""
        with self.db.session_scope() as session:
            try:
                # 检查重复
                existing = session.query(Account).filter(
                    Account.login == account.login
                ).first()
                
                if existing:
                    raise DuplicateEntityException(
                        "Account", "login", account.login
                    )
                
                # 创建
                session.add(account)
                session.commit()
                session.refresh(account)
                
                self.logger.info(
                    "Account created",
                    account_id=account.id,
                    login=account.login
                )
                
                return account
                
            except IntegrityError as e:
                session.rollback()
                self.logger.error(
                    "Integrity error when creating account",
                    login=account.login,
                    error=str(e)
                )
                raise DuplicateEntityException(
                    "Account", "login", account.login,
                    original_exception=e
                )
            except Exception as e:
                session.rollback()
                self.logger.error(
                    "Failed to create account",
                    login=account.login,
                    error=str(e),
                    exc_info=True
                )
                raise DatabaseException(
                    "Failed to create account",
                    original_exception=e
                )
    
    def get_by_id(self, account_id: str) -> Optional[Account]:
        """根据ID获取账户"""
        with self.db.session_scope() as session:
            try:
                account = session.query(Account).filter(
                    Account.id == account_id
                ).first()
                
                if account:
                    # 触发lazy loading避免DetachedInstanceError
                    session.expunge(account)
                
                return account
                
            except Exception as e:
                self.logger.error(
                    "Failed to get account by ID",
                    account_id=account_id,
                    error=str(e)
                )
                raise DatabaseException(
                    f"Failed to get account {account_id}",
                    original_exception=e
                )
\`\`\`

### 2. Service Pattern (服务模式)

**目的**: 封装业务逻辑，编排多个Repository

\`\`\`python
# src/services/orchestrator/service/account_service.py
from typing import List, Dict
from datetime import datetime

class AccountService:
    """
    账户业务服务
    
    职责:
    - 账户生命周期管理
    - 业务规则验证
    - 跨Repository事务编排
    - MT5账户同步
    """
    
    def __init__(
        self,
        account_repo: IAccountRepository,
        allocation_repo: IAccountAllocationRepository,
        mt5_manager: MT5ConnectionManager,
        validator: AccountValidator,
        logger: Logger
    ):
        """依赖注入"""
        self.account_repo = account_repo
        self.allocation_repo = allocation_repo
        self.mt5_manager = mt5_manager
        self.validator = validator
        self.logger = logger
    
    def create_account(
        self,
        login: int,
        server: str,
        company: str,
        initial_balance: float,
        name: Optional[str] = None
    ) -> Account:
        """
        创建账户
        
        Business Rules:
        1. login必须唯一
        2. initial_balance > 0
        3. server不为空
        4. 自动创建默认风控配置
        
        Args:
            login: MT5账号
            server: 服务器名称
            company: 经纪商名称
            initial_balance: 初始资金
            name: 账户别名
        
        Returns:
            创建的账户对象
        
        Raises:
            ValidationException: 数据验证失败
            DuplicateEntityException: 账号已存在
            DatabaseException: 数据库操作失败
        """
        # 1. 输入验证
        self.validator.validate_create_account(
            login, server, initial_balance
        )
        
        # 2. 检查重复（业务规则）
        existing = self.account_repo.get_by_login(login)
        if existing:
            self.logger.warning(
                "Attempt to create duplicate account",
                login=login
            )
            raise DuplicateEntityException(
                "Account", "login", login
            )
        
        # 3. 创建实体
        account = AccountFactory.create_default_account(
            login=login,
            server=server,
            company=company,
            initial_balance=initial_balance,
            name=name or f"Account-{login}"
        )
        
        # 4. 持久化
        try:
            account = self.account_repo.create(account)
            
            self.logger.info(
                "Account created successfully",
                account_id=account.id,
                login=login,
                server=server
            )
            
            return account
            
        except Exception as e:
            self.logger.error(
                "Failed to create account",
                login=login,
                error=str(e),
                exc_info=True
            )
            raise
    
    def sync_account_from_mt5(self, account_id: str) -> Account:
        """
        从MT5同步账户信息
        
        Args:
            account_id: 账户ID
        
        Returns:
            更新后的账户对象
        
        Raises:
            EntityNotFoundException: 账户不存在
            MT5ConnectionException: MT5连接失败
        """
        # 1. 获取账户
        account = self.account_repo.get_by_id(account_id)
        if not account:
            raise EntityNotFoundException("Account", account_id)
        
        # 2. 检查MT5连接
        if not self.mt5_manager.is_connected():
            raise MT5ConnectionException("MT5 not connected")
        
        # 3. 从MT5获取数据
        try:
            client = self.mt5_manager.get_client()
            mt5_account = client.account_info()
            
            if not mt5_account:
                raise MT5ConnectionException(
                    "Failed to get account info from MT5"
                )
            
            # 4. 更新账户
            account.current_balance = mt5_account.balance
            account.current_equity = mt5_account.equity
            account.leverage = mt5_account.leverage
            account.last_sync_time = datetime.now()
            
            # 5. 持久化
            account = self.account_repo.update(account)
            
            self.logger.info(
                "Account synced from MT5",
                account_id=account.id,
                balance=mt5_account.balance,
                equity=mt5_account.equity
            )
            
            return account
            
        except Exception as e:
            self.logger.error(
                "Failed to sync account from MT5",
                account_id=account_id,
                error=str(e),
                exc_info=True
            )
            raise
    
    def get_account_with_allocations(
        self,
        account_id: str
    ) -> Dict:
        """
        获取账户及其策略配比
        
        Returns:
            {
                'account': Account对象,
                'allocations': [Allocation对象列表],
                'total_allocation': 总配比
            }
        """
        # 1. 获取账户
        account = self.account_repo.get_by_id(account_id)
        if not account:
            raise EntityNotFoundException("Account", account_id)
        
        # 2. 获取配比
        allocations = self.allocation_repo.get_by_account(
            account_id,
            is_active=True
        )
        
        # 3. 计算总配比
        total_allocation = sum(
            a.allocation_percentage for a in allocations
        )
        
        return {
            'account': account,
            'allocations': allocations,
            'total_allocation': total_allocation
        }
\`\`\`

### 3. Factory Pattern (工厂模式)

**目的**: 封装对象创建逻辑

\`\`\`python
# src/common/factories/account_factory.py
class AccountFactory:
    """账户工厂"""
    
    @staticmethod
    def create_default_account(
        login: int,
        server: str,
        company: str,
        initial_balance: float,
        name: str
    ) -> Account:
        """创建带默认配置的账户"""
        from src.common.utils.id_generator import generate_account_id
        
        return Account(
            id=generate_account_id(),
            login=login,
            server=server,
            company=company,
            name=name,
            currency="USD",
            leverage=100,
            initial_balance=initial_balance,
            start_time=datetime.now(),
            current_balance=initial_balance,
            current_equity=initial_balance,
            last_sync_time=datetime.now(),
            is_active=True,
            trade_allowed=True,
            risk_config=RiskConfigFactory.create_balanced(),
            notes="系统自动创建"
        )

class RiskConfigFactory:
    """风控配置工厂"""
    
    @staticmethod
    def create_balanced() -> Dict:
        """平衡型风控"""
        return {
            "max_daily_loss": 0.05,
            "max_total_exposure": 0.30,
            "max_concurrent_trades": 10,
            "max_strategy_allocation": 0.10
        }
    
    @staticmethod
    def create_aggressive() -> Dict:
        """进取型风控"""
        return {
            "max_daily_loss": 0.08,
            "max_total_exposure": 0.50,
            "max_concurrent_trades": 20,
            "max_strategy_allocation": 0.15
        }
    
    @staticmethod
    def create_conservative() -> Dict:
        """保守型风控"""
        return {
            "max_daily_loss": 0.03,
            "max_total_exposure": 0.20,
            "max_concurrent_trades": 5,
            "max_strategy_allocation": 0.08
        }
\`\`\`

### 4. Validator Pattern (验证器模式)

**目的**: 集中管理业务规则验证逻辑

\`\`\`python
# src/services/orchestrator/validators/account_validator.py
class AccountValidator:
    """账户验证器"""
    
    @staticmethod
    def validate_create_account(
        login: int,
        server: str,
        initial_balance: float
    ) -> None:
        """
        验证创建账户的输入
        
        Raises:
            ValidationException: 验证失败
        """
        # 验证login
        if login <= 0:
            raise ValidationException(
                "Login must be positive",
                field="login",
                value=login
            )
        
        if len(str(login)) > 15:
            raise ValidationException(
                "Login too long",
                field="login",
                value=login
            )
        
        # 验证server
        if not server or not server.strip():
            raise ValidationException(
                "Server cannot be empty",
                field="server",
                value=server
            )
        
        if len(server) > 255:
            raise ValidationException(
                "Server name too long",
                field="server",
                value=server
            )
        
        # 防止注入
        dangerous_chars = ['<', '>', '"', "'", ';', '--']
        if any(c in server for c in dangerous_chars):
            raise ValidationException(
                "Server name contains dangerous characters",
                field="server",
                value=server
            )
        
        # 验证initial_balance
        if initial_balance < 0:
            raise ValidationException(
                "Initial balance cannot be negative",
                field="initial_balance",
                value=initial_balance
            )
        
        if initial_balance == 0:
            raise ValidationException(
                "Initial balance must be greater than zero",
                field="initial_balance",
                value=initial_balance
            )
        
        if initial_balance > 1_000_000_000:
            raise ValidationException(
                "Initial balance too large",
                field="initial_balance",
                value=initial_balance
            )
    
    @staticmethod
    def validate_allocation(
        allocations: List[Dict]
    ) -> None:
        """
        验证策略配比
        
        Rules:
        1. 总配比不超过100%
        2. 单个配比 > 0
        3. 至少有一个策略
        
        Raises:
            ValidationException: 验证失败
            AllocationExceedsLimitException: 配比超限
        """
        if not allocations:
            raise ValidationException(
                "At least one strategy allocation required"
            )
        
        total = sum(a['allocation_percentage'] for a in allocations)
        
        if total > 1.0:
            raise AllocationExceedsLimitException(total, 1.0)
        
        for alloc in allocations:
            pct = alloc['allocation_percentage']
            if pct <= 0:
                raise ValidationException(
                    "Allocation percentage must be positive",
                    field="allocation_percentage",
                    value=pct
                )
            
            if pct > 1.0:
                raise ValidationException(
                    "Allocation percentage cannot exceed 100%",
                    field="allocation_percentage",
                    value=pct
                )
\`\`\`

---

## 异常处理体系

### 异常层次结构

\`\`\`
BaseBusinessException (基础业务异常)
├── DatabaseException (数据库异常)
│   ├── EntityNotFoundException (实体未找到)
│   ├── DuplicateEntityException (实体重复)
│   └── DatabaseConnectionException (连接失败)
├── ValidationException (验证异常)
├── BusinessRuleViolationException (业务规则违反)
│   ├── InsufficientBalanceException (余额不足)
│   ├── AllocationExceedsLimitException (配比超限)
│   └── InvalidStateException (非法状态)
├── ExternalServiceException (外部服务异常)
│   ├── MT5ConnectionException (MT5连接异常)
│   └── MT5OrderException (MT5订单异常)
├── ConfigurationException (配置异常)
└── PermissionDeniedException (权限拒绝)
\`\`\`

### 异常基类设计

\`\`\`python
# src/common/exceptions/__init__.py
class BaseBusinessException(Exception):
    """业务异常基类"""
    
    def __init__(
        self,
        message: str,
        error_code: str = "UNKNOWN_ERROR",
        details: Optional[Dict[str, Any]] = None,
        original_exception: Optional[Exception] = None
    ):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        self.original_exception = original_exception
        super().__init__(message)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（用于API响应）"""
        result = {
            'error_code': self.error_code,
            'message': self.message,
            'details': self.details
        }
        if self.original_exception:
            result['original_error'] = str(self.original_exception)
        return result
    
    def __str__(self):
        return f"[{self.error_code}] {self.message}"
\`\`\`

### API层异常处理

\`\`\`python
# src/services/orchestrator/api/routes/account.py
from fastapi import APIRouter, HTTPException
from src.common.exceptions import *

router = APIRouter()

@router.post("/accounts")
async def create_account(request: CreateAccountRequest):
    """创建账户API"""
    try:
        account = account_service.create_account(
            login=request.login,
            server=request.server,
            company=request.company,
            initial_balance=request.initial_balance,
            name=request.name
        )
        
        return {
            "success": True,
            "data": account.to_dict()
        }
        
    except ValidationException as e:
        logger.warning(
            "Validation error",
            error=e.to_dict()
        )
        raise HTTPException(
            status_code=400,
            detail=e.to_dict()
        )
    
    except DuplicateEntityException as e:
        logger.warning(
            "Duplicate entity",
            error=e.to_dict()
        )
        raise HTTPException(
            status_code=409,
            detail=e.to_dict()
        )
    
    except BaseBusinessException as e:
        logger.error(
            "Business error",
            error=e.to_dict(),
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail=e.to_dict()
        )
    
    except Exception as e:
        logger.error(
            "Unexpected error",
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail={
                "error_code": "INTERNAL_ERROR",
                "message": "Internal server error"
            }
        )
\`\`\`

### 异常处理最佳实践

1. **不要吞噬异常**: 必须记录或重新抛出
2. **异常要有上下文**: 包含足够的调试信息
3. **区分业务异常和系统异常**: 不同的处理方式
4. **异常层级合理**: 不要过深的继承
5. **统一错误码**: 便于前端处理

---

## 日志与监控

### 结构化日志设计

\`\`\`python
# src/common/logging/structured_logger.py
import logging
import json
from datetime import datetime
from typing import Any, Dict

class StructuredLogger:
    """结构化日志器"""
    
    def __init__(self, name: str, level: str = "INFO"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, level))
        
        # 控制台Handler - JSON格式
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(JSONFormatter())
        self.logger.addHandler(console_handler)
        
        # 文件Handler - JSON格式（生产环境）
        # file_handler = RotatingFileHandler(
        #     f"logs/{name}.log",
        #     maxBytes=10*1024*1024,  # 10MB
        #     backupCount=5
        # )
        # file_handler.setFormatter(JSONFormatter())
        # self.logger.addHandler(file_handler)
    
    def _log(self, level: str, message: str, **kwargs):
        """统一日志方法"""
        extra = {
            'timestamp': datetime.now().isoformat(),
            **kwargs
        }
        getattr(self.logger, level)(message, extra=extra)
    
    def debug(self, message: str, **kwargs):
        """DEBUG级别日志"""
        self._log('debug', message, **kwargs)
    
    def info(self, message: str, **kwargs):
        """INFO级别日志"""
        self._log('info', message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """WARNING级别日志"""
        self._log('warning', message, **kwargs)
    
    def error(self, message: str, exc_info: bool = False, **kwargs):
        """ERROR级别日志"""
        if exc_info:
            kwargs['exc_info'] = True
        self._log('error', message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        """CRITICAL级别日志"""
        self._log('critical', message, **kwargs)

class JSONFormatter(logging.Formatter):
    """JSON格式化器"""
    
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            'timestamp': datetime.now().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
            'process': record.process,
            'thread': record.thread
        }
        
        # 添加extra字段
        if hasattr(record, 'timestamp'):
            log_data['timestamp'] = record.timestamp
        for key in dir(record):
            if key not in ['timestamp', 'message', 'args', 'exc_info', 'exc_text', 
                          'stack_info', 'created', 'filename', 'funcName', 
                          'levelname', 'levelno', 'lineno', 'module', 'msecs',
                          'msg', 'name', 'pathname', 'process', 'processName',
                          'relativeCreated', 'thread', 'threadName']:
                value = getattr(record, key)
                if not callable(value) and not key.startswith('_'):
                    log_data[key] = value
        
        # 添加异常信息
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_data, ensure_ascii=False)
\`\`\`

### 日志使用示例

\`\`\`python
# 初始化
logger = StructuredLogger('account_service')

# 记录业务操作
logger.info(
    "Account created",
    account_id="ACC_12345",
    login=5049130509,
    server="MetaQuotes-Demo",
    initial_balance=10000.0
)

# 输出:
# {
#   "timestamp": "2026-04-10T22:30:00.123456",
#   "level": "INFO",
#   "logger": "account_service",
#   "message": "Account created",
#   "module": "account_service",
#   "function": "create_account",
#   "line": 45,
#   "account_id": "ACC_12345",
#   "login": 5049130509,
#   "server": "MetaQuotes-Demo",
#   "initial_balance": 10000.0
# }

# 记录错误
try:
    ...
except Exception as e:
    logger.error(
        "Failed to create account",
        exc_info=True,
        login=login,
        error_type=type(e).__name__
    )
\`\`\`

### 监控指标

\`\`\`python
# src/common/monitoring/metrics.py
from prometheus_client import Counter, Histogram, Gauge
import time

# 定义指标
request_count = Counter(
    'api_requests_total',
    'Total API requests',
    ['method', 'endpoint', 'status']
)

request_duration = Histogram(
    'api_request_duration_seconds',
    'API request duration',
    ['method', 'endpoint']
)

active_accounts = Gauge(
    'active_accounts_total',
    'Total number of active accounts'
)

# 使用装饰器
def monitor_performance(func):
    """性能监控装饰器"""
    def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            request_count.labels(
                method=func.__name__,
                endpoint=func.__module__,
                status='success'
            ).inc()
            return result
        except Exception as e:
            request_count.labels(
                method=func.__name__,
                endpoint=func.__module__,
                status='error'
            ).inc()
            raise
        finally:
            duration = time.time() - start_time
            request_duration.labels(
                method=func.__name__,
                endpoint=func.__module__
            ).observe(duration)
    return wrapper

# 使用
@monitor_performance
def create_account(...):
    ...
\`\`\`

---

## 数据库设计

### 事务管理

\`\`\`python
# src/common/database/connection.py
from contextlib import contextmanager
from typing import Generator
from sqlalchemy.orm import Session

class DatabaseConnection:
    """数据库连接管理"""
    
    @contextmanager
    def session_scope(self) -> Generator[Session, None, None]:
        """
        会话上下文管理器
        
        自动提交和回滚：
        - 正常执行：自动commit
        - 异常：自动rollback
        - 总是：close session
        """
        session = self.Session()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    @contextmanager
    def transaction(self) -> Generator[Session, None, None]:
        """
        显式事务管理
        
        用于需要明确事务边界的场景
        """
        session = self.Session()
        try:
            session.begin()
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

# 装饰器形式
def transactional(func):
    """事务装饰器"""
    def wrapper(self, *args, **kwargs):
        with self.db.transaction() as session:
            # 将session注入到kwargs
            kwargs['session'] = session
            return func(self, *args, **kwargs)
    return wrapper

# 使用示例
class AccountService:
    
    @transactional
    def create_account_with_allocations(
        self,
        account_data: Dict,
        allocations: List[Dict],
        session: Session = None  # 由装饰器注入
    ):
        """
        创建账户和配比 - 原子操作
        
        如果任何一步失败，整个操作回滚
        """
        # 1. 创建账户
        account = Account(**account_data)
        session.add(account)
        session.flush()  # 获取account.id但不提交
        
        # 2. 创建配比
        for alloc_data in allocations:
            allocation = AccountAllocation(
                id=generate_id("ALLOC"),
                account_id=account.id,  # 使用刚创建的account.id
                **alloc_data
            )
            session.add(allocation)
        
        # 3. 事务由装饰器自动提交
        return account
\`\`\`

### 连接池配置

\`\`\`python
# src/common/database/connection.py
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool
from sqlalchemy.orm import sessionmaker

class DatabaseConnection:
    def __init__(self, database_url: str):
        # 创建引擎 - 生产级配置
        self.engine = create_engine(
            database_url,
            
            # 连接池配置
            poolclass=QueuePool,
            pool_size=10,              # 连接池大小
            max_overflow=20,           # 超出pool_size的最大连接数
            pool_timeout=30,           # 获取连接超时时间（秒）
            pool_recycle=3600,         # 连接回收时间（秒）
            pool_pre_ping=True,        # 连接前测试可用性
            
            # 日志配置
            echo=False,                # 不打印SQL（生产环境）
            echo_pool=False,           # 不打印连接池日志
            
            # 性能配置
            connect_args={
                "connect_timeout": 10,  # 连接超时
                "check_same_thread": False  # SQLite专用
            }
        )
        
        # 创建Session工厂
        self.Session = sessionmaker(
            bind=self.engine,
            autocommit=False,
            autoflush=False,
            expire_on_commit=False  # 避免DetachedInstanceError
        )
\`\`\`

### 查询优化 - 避免N+1查询

\`\`\`python
# 不好的方式 - N+1查询
def get_accounts_with_allocations_bad():
    accounts = session.query(Account).all()  # 1次查询
    
    for account in accounts:  # N次查询
        allocations = session.query(AccountAllocation).filter(
            AccountAllocation.account_id == account.id
        ).all()
        account.allocations = allocations

# 好的方式 - 使用JOIN
def get_accounts_with_allocations_good():
    from sqlalchemy.orm import joinedload
    
    accounts = session.query(Account).options(
        joinedload(Account.allocations)  # 预加载关联数据
    ).all()  # 只需1次查询
    
    return accounts

# 更好的方式 - 显式JOIN + 过滤
def get_active_accounts_with_active_allocations():
    from sqlalchemy.orm import contains_eager
    
    accounts = session.query(Account).join(
        AccountAllocation,
        Account.id == AccountAllocation.account_id
    ).filter(
        Account.is_active == True,
        AccountAllocation.is_active == True
    ).options(
        contains_eager(Account.allocations)
    ).all()
    
    return accounts
\`\`\`

### 索引策略

\`\`\`python
# src/common/models/account.py
from sqlalchemy import Index

class Account(Base):
    __tablename__ = "accounts"
    
    id = Column(String(32), primary_key=True)
    login = Column(Integer, nullable=False, unique=True, index=True)  # 单列索引
    server = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, index=True)  # 单列索引
    
    # 复合索引（多列查询优化）
    __table_args__ = (
        Index('idx_account_login_server', 'login', 'server'),  # 复合索引
        Index('idx_account_active_created', 'is_active', 'created_at'),  # 复合索引
    )
\`\`\`

---

## 服务间通信

### HTTP Client封装 - 带重试和超时

\`\`\`python
# src/common/clients/base_client.py
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential
from typing import Any, Dict, Optional

class BaseServiceClient:
    """服务客户端基类"""
    
    def __init__(
        self,
        base_url: str,
        timeout: float = 30.0,
        max_retries: int = 3,
        logger: Optional[Logger] = None
    ):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.max_retries = max_retries
        self.logger = logger or StructuredLogger(self.__class__.__name__)
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    async def _request(
        self,
        method: str,
        path: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        发送HTTP请求（带重试）
        
        Args:
            method: HTTP方法
            path: 路径
            **kwargs: httpx参数
        
        Returns:
            响应JSON
        
        Raises:
            httpx.HTTPStatusError: HTTP错误
            httpx.RequestError: 请求错误
        """
        url = f"{self.base_url}{path}"
        
        self.logger.info(
            f"Calling {method} {url}",
            method=method,
            url=url,
            timeout=self.timeout
        )
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.request(method, url, **kwargs)
                response.raise_for_status()
                
                self.logger.info(
                    "Request successful",
                    method=method,
                    url=url,
                    status_code=response.status_code,
                    duration=response.elapsed.total_seconds()
                )
                
                return response.json()
                
            except httpx.HTTPStatusError as e:
                self.logger.error(
                    "HTTP error",
                    method=method,
                    url=url,
                    status_code=e.response.status_code,
                    response_body=e.response.text[:500]
                )
                raise
                
            except httpx.RequestError as e:
                self.logger.error(
                    "Request error",
                    method=method,
                    url=url,
                    error=str(e),
                    error_type=type(e).__name__
                )
                raise
    
    async def get(self, path: str, **kwargs) -> Dict:
        """GET请求"""
        return await self._request("GET", path, **kwargs)
    
    async def post(self, path: str, **kwargs) -> Dict:
        """POST请求"""
        return await self._request("POST", path, **kwargs)
    
    async def put(self, path: str, **kwargs) -> Dict:
        """PUT请求"""
        return await self._request("PUT", path, **kwargs)
    
    async def delete(self, path: str, **kwargs) -> Dict:
        """DELETE请求"""
        return await self._request("DELETE", path, **kwargs)

# 具体服务客户端
class OrchestratorClient(BaseServiceClient):
    """Orchestrator服务客户端"""
    
    async def get_accounts(self, is_active: Optional[bool] = None) -> List[Dict]:
        """获取账户列表"""
        params = {}
        if is_active is not None:
            params['is_active'] = is_active
        
        response = await self.get("/accounts", params=params)
        return response.get('data', [])
    
    async def create_account(self, data: Dict) -> Dict:
        """创建账户"""
        response = await self.post("/accounts", json=data)
        return response.get('data')
\`\`\`

### 熔断器模式 - 防止雪崩

\`\`\`python
# src/common/resilience/circuit_breaker.py
from enum import Enum
from datetime import datetime, timedelta
from typing import Callable

class CircuitState(Enum):
    """熔断器状态"""
    CLOSED = "closed"          # 正常
    OPEN = "open"              # 熔断（拒绝请求）
    HALF_OPEN = "half_open"    # 半开（尝试恢复）

class CircuitBreaker:
    """
    熔断器
    
    防止故障扩散，保护系统稳定性
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,      # 失败阈值
        timeout: int = 60,               # 熔断超时（秒）
        expected_exception: type = Exception
    ):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED
        self.logger = StructuredLogger('circuit_breaker')
    
    def call(self, func: Callable, *args, **kwargs):
        """
        执行函数调用
        
        状态转换:
        CLOSED -> OPEN: 失败次数达到阈值
        OPEN -> HALF_OPEN: 超时后尝试恢复
        HALF_OPEN -> CLOSED: 调用成功
        HALF_OPEN -> OPEN: 调用失败
        """
        # 检查是否需要尝试恢复
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
                self.logger.info("Circuit breaker transitioning to HALF_OPEN")
            else:
                raise Exception(
                    f"Circuit breaker is OPEN. "
                    f"Will retry after {self.timeout} seconds."
                )
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
            
        except self.expected_exception as e:
            self._on_failure()
            raise
    
    def _on_success(self):
        """成功回调"""
        if self.state == CircuitState.HALF_OPEN:
            self.logger.info("Circuit breaker transitioning to CLOSED")
        
        self.failure_count = 0
        self.state = CircuitState.CLOSED
    
    def _on_failure(self):
        """失败回调"""
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            self.logger.warning(
                "Circuit breaker transitioning to OPEN",
                failure_count=self.failure_count,
                threshold=self.failure_threshold
            )
    
    def _should_attempt_reset(self) -> bool:
        """是否应该尝试重置"""
        return (
            self.last_failure_time and
            datetime.now() - self.last_failure_time > 
            timedelta(seconds=self.timeout)
        )

# 使用示例
mt5_breaker = CircuitBreaker(
    failure_threshold=5,
    timeout=60,
    expected_exception=MT5ConnectionException
)

def safe_mt5_call():
    """安全的MT5调用"""
    try:
        return mt5_breaker.call(mt5_client.account_info)
    except Exception as e:
        logger.error(f"MT5 call failed: {e}")
        # 降级处理：返回缓存数据或默认值
        return get_cached_account_info()
\`\`\`

---

## 配置管理

### 配置层次和优先级

\`\`\`
1. 代码默认值（最低优先级）
2. 配置文件 (config/*.yaml)
3. 环境变量
4. 运行时配置（数据库）
5. 命令行参数（最高优先级）
\`\`\`

### 配置模型 - 使用Pydantic验证

\`\`\`python
# src/common/config/models.py
from pydantic import BaseModel, validator, Field
from typing import Dict, List, Optional

class MT5Config(BaseModel):
    """MT5配置"""
    company: str = Field(..., description="经纪商名称")
    server: str = Field(..., description="服务器名称")
    login: int = Field(..., gt=0, description="账号")
    password: str = Field(..., min_length=4, description="密码")
    investor_password: Optional[str] = Field(None, description="投资者密码")
    
    path: Optional[str] = Field(None, description="MT5终端路径")
    timeout: int = Field(60000, ge=1000, le=300000, description="超时时间（毫秒）")
    portable: bool = Field(False, description="便携模式")
    
    @validator('login')
    def validate_login(cls, v):
        if len(str(v)) > 15:
            raise ValueError('login too long')
        return v

class ServiceConfig(BaseModel):
    """服务配置"""
    host: str = Field("0.0.0.0", description="监听地址")
    port: int = Field(..., ge=1024, le=65535, description="端口")
    workers: int = Field(1, ge=1, le=32, description="工作进程数")

class DatabaseConfig(BaseModel):
    """数据库配置"""
    url: str = Field(..., description="数据库URL")
    echo: bool = Field(False, description="是否打印SQL")
    pool_size: int = Field(10, ge=1, le=100)
    max_overflow: int = Field(20, ge=0, le=100)

class AppConfig(BaseModel):
    """应用配置根模型"""
    app: Dict
    database: DatabaseConfig
    services: Dict[str, ServiceConfig]
    service_urls: Dict[str, str]
    mt5: MT5Config
    orchestrator: Dict
    
    @classmethod
    def load_from_file(cls, path: str) -> 'AppConfig':
        """从YAML文件加载配置"""
        import yaml
        
        with open(path, 'r') as f:
            data = yaml.safe_load(f)
        
        # 环境变量替换
        data = cls._replace_env_vars(data)
        
        return cls(**data)
    
    @staticmethod
    def _replace_env_vars(data: Dict) -> Dict:
        """递归替换环境变量"""
        import os
        import re
        
        def replace_value(value):
            if isinstance(value, str):
                # ${VAR_NAME} 或 ${VAR_NAME:default}
                pattern = r'\$\{([^:}]+)(?::([^}]+))?\}'
                
                def replacer(match):
                    var_name = match.group(1)
                    default = match.group(2)
                    return os.getenv(var_name, default or '')
                
                return re.sub(pattern, replacer, value)
            elif isinstance(value, dict):
                return {k: replace_value(v) for k, v in value.items()}
            elif isinstance(value, list):
                return [replace_value(v) for v in value]
            return value
        
        return replace_value(data)

# 使用
config = AppConfig.load_from_file('config/development.yaml')
print(config.mt5.login)
print(config.services['orchestrator'].port)
\`\`\`

---

## 测试策略

### 测试金字塔

\`\`\`
          /\
         /E2E\         10% - 端到端测试
        /    \         - 完整业务流程
       /______\        - 真实环境
      /        \
     /Integration\     20% - 集成测试
    /   Tests    \     - 多组件协作
   /______________\    - 测试数据库
  /                \
 /   Unit Tests     \  70% - 单元测试
/____________________\ - 单一组件
                       - Mock依赖
\`\`\`

### 单元测试示例

\`\`\`python
# tests/unit/test_account_service.py
import pytest
from unittest.mock import Mock, patch
from src.services.orchestrator.service.account_service import AccountService
from src.common.exceptions import *

class TestAccountService:
    """账户服务单元测试"""
    
    @pytest.fixture
    def mock_account_repo(self):
        """Mock AccountRepository"""
        return Mock(spec=AccountRepository)
    
    @pytest.fixture
    def mock_validator(self):
        """Mock AccountValidator"""
        return Mock(spec=AccountValidator)
    
    @pytest.fixture
    def service(self, mock_account_repo, mock_validator):
        """创建测试服务"""
        return AccountService(
            account_repo=mock_account_repo,
            allocation_repo=Mock(),
            mt5_manager=Mock(),
            validator=mock_validator,
            logger=Mock()
        )
    
    def test_create_account_success(self, service, mock_account_repo, mock_validator):
        """测试创建账户 - 成功场景"""
        # Arrange
        mock_validator.validate_create_account.return_value = None
        mock_account_repo.get_by_login.return_value = None
        mock_account_repo.create.return_value = Account(
            id="ACC_123",
            login=5049130509,
            server="Demo",
            initial_balance=10000.0
        )
        
        # Act
        account = service.create_account(
            login=5049130509,
            server="Demo",
            company="Test",
            initial_balance=10000.0
        )
        
        # Assert
        assert account.id == "ACC_123"
        assert account.login == 5049130509
        mock_validator.validate_create_account.assert_called_once()
        mock_account_repo.get_by_login.assert_called_once_with(5049130509)
        mock_account_repo.create.assert_called_once()
    
    def test_create_account_duplicate(self, service, mock_account_repo, mock_validator):
        """测试创建账户 - 重复账号"""
        # Arrange
        mock_validator.validate_create_account.return_value = None
        existing_account = Account(
            id="ACC_456",
            login=5049130509,
            server="Demo",
            initial_balance=5000.0
        )
        mock_account_repo.get_by_login.return_value = existing_account
        
        # Act & Assert
        with pytest.raises(DuplicateEntityException) as exc_info:
            service.create_account(
                login=5049130509,
                server="Demo",
                company="Test",
                initial_balance=10000.0
            )
        
        assert exc_info.value.error_code == "DUPLICATE_ENTITY"
        mock_account_repo.create.assert_not_called()
    
    def test_create_account_validation_error(self, service, mock_validator):
        """测试创建账户 - 验证失败"""
        # Arrange
        mock_validator.validate_create_account.side_effect = ValidationException(
            "Invalid login",
            field="login",
            value=-1
        )
        
        # Act & Assert
        with pytest.raises(ValidationException):
            service.create_account(
                login=-1,
                server="Demo",
                company="Test",
                initial_balance=10000.0
            )
\`\`\`

### 集成测试示例

\`\`\`python
# tests/integration/test_account_integration.py
import pytest
from sqlalchemy import create_engine
from src.common.database.connection import DatabaseConnection
from src.common.models import Account, AccountAllocation
from src.services.orchestrator.repository.account_repo import AccountRepository

@pytest.mark.integration
class TestAccountIntegration:
    """账户集成测试"""
    
    @pytest.fixture(scope="function")
    def db(self):
        """测试数据库 - 每个测试独立"""
        # 创建内存数据库
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        
        db_conn = DatabaseConnection(engine)
        
        yield db_conn
        
        # 清理
        Base.metadata.drop_all(engine)
    
    @pytest.fixture
    def account_repo(self, db):
        """创建Repository"""
        return AccountRepository(db, logger=Mock())
    
    def test_create_and_retrieve_account(self, account_repo):
        """测试创建和查询账户"""
        # 创建
        account = Account(
            id="ACC_789",
            login=5049130509,
            server="Test",
            company="Test Company",
            initial_balance=10000.0
        )
        created = account_repo.create(account)
        
        # 验证创建
        assert created.id == "ACC_789"
        assert created.login == 5049130509
        
        # 查询
        retrieved = account_repo.get_by_id("ACC_789")
        
        # 验证查询
        assert retrieved is not None
        assert retrieved.login == 5049130509
        assert retrieved.server == "Test"
    
    def test_duplicate_login_raises_exception(self, account_repo):
        """测试重复login抛出异常"""
        # 创建第一个账户
        account1 = Account(
            id="ACC_001",
            login=123456,
            server="Server1",
            initial_balance=10000.0
        )
        account_repo.create(account1)
        
        # 尝试创建相同login的账户
        account2 = Account(
            id="ACC_002",
            login=123456,  # 重复
            server="Server2",
            initial_balance=20000.0
        )
        
        with pytest.raises(DuplicateEntityException):
            account_repo.create(account2)
\`\`\`

### E2E测试示例

\`\`\`python
# tests/e2e/test_account_flow.py
import pytest
import httpx

@pytest.mark.e2e
class TestAccountE2E:
    """账户端到端测试"""
    
    @pytest.fixture
    def api_url(self):
        """API基础URL"""
        return "http://localhost:8002"
    
    async def test_complete_account_flow(self, api_url):
        """测试完整账户流程"""
        async with httpx.AsyncClient() as client:
            # 1. 创建账户
            create_response = await client.post(
                f"{api_url}/accounts",
                json={
                    "login": 9999999,
                    "server": "Test-Server",
                    "company": "Test Company",
                    "initial_balance": 10000.0,
                    "name": "E2E Test Account"
                }
            )
            assert create_response.status_code == 200
            data = create_response.json()
            assert data['success'] == True
            account_id = data['data']['id']
            
            # 2. 查询账户
            get_response = await client.get(
                f"{api_url}/accounts/{account_id}"
            )
            assert get_response.status_code == 200
            account = get_response.json()['data']
            assert account['login'] == 9999999
            
            # 3. 更新账户
            update_response = await client.put(
                f"{api_url}/accounts/{account_id}",
                json={"name": "Updated Name"}
            )
            assert update_response.status_code == 200
            
            # 4. 删除账户
            delete_response = await client.delete(
                f"{api_url}/accounts/{account_id}"
            )
            assert delete_response.status_code == 200
\`\`\`

---

## 性能优化

### 1. 数据库查询优化

\`\`\`python
# ❌ 不好的方式
accounts = session.query(Account).all()
for account in accounts:
    allocations = session.query(AccountAllocation).filter(
        AccountAllocation.account_id == account.id
    ).all()

# ✅ 好的方式
from sqlalchemy.orm import joinedload

accounts = session.query(Account).options(
    joinedload(Account.allocations)
).all()
\`\`\`

### 2. 缓存策略

\`\`\`python
# src/common/cache/redis_cache.py
from redis import Redis
import json
from functools import wraps

class CacheService:
    """缓存服务"""
    
    def __init__(self, redis_client: Redis):
        self.redis = redis_client
    
    def get(self, key: str):
        """获取缓存"""
        value = self.redis.get(key)
        if value:
            return json.loads(value)
        return None
    
    def set(self, key: str, value, ttl: int = 3600):
        """设置缓存"""
        self.redis.setex(
            key,
            ttl,
            json.dumps(value)
        )
    
    def delete(self, key: str):
        """删除缓存"""
        self.redis.delete(key)

# 缓存装饰器
def cached(ttl: int = 3600, key_prefix: str = ""):
    """缓存装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 生成缓存key
            cache_key = f"{key_prefix}:{func.__name__}:{args}:{kwargs}"
            
            # 尝试从缓存获取
            cached_value = cache_service.get(cache_key)
            if cached_value is not None:
                logger.debug(f"Cache hit: {cache_key}")
                return cached_value
            
            # 执行函数
            result = func(*args, **kwargs)
            
            # 写入缓存
            cache_service.set(cache_key, result, ttl)
            
            return result
        return wrapper
    return decorator

# 使用
@cached(ttl=300, key_prefix="account")
def get_account_summary(account_id: str):
    # 复杂计算...
    return summary
\`\`\`

### 3. 异步处理

\`\`\`python
# src/common/async_tasks/task_manager.py
import asyncio
from concurrent.futures import ThreadPoolExecutor

class AsyncTaskManager:
    """异步任务管理器"""
    
    def __init__(self, max_workers: int = 10):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
    
    async def run_in_background(self, func, *args, **kwargs):
        """在后台运行任务"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor,
            func,
            *args,
            **kwargs
        )
    
    async def run_parallel(self, tasks: List):
        """并行运行多个任务"""
        return await asyncio.gather(*tasks)

# 使用
async def sync_all_accounts():
    tasks = [
        task_manager.run_in_background(sync_account, acc_id)
        for acc_id in account_ids
    ]
    results = await asyncio.gather(*tasks)
    return results
\`\`\`

---

## 安全设计

### 1. 输入验证

\`\`\`python
from pydantic import BaseModel, validator

class CreateAccountRequest(BaseModel):
    login: int
    server: str
    initial_balance: float
    
    @validator('login')
    def validate_login(cls, v):
        if v <= 0:
            raise ValueError('login must be positive')
        if len(str(v)) > 15:
            raise ValueError('login too long')
        return v
    
    @validator('server')
    def validate_server(cls, v):
        # 防止SQL注入和XSS
        dangerous_chars = ['<', '>', '"', "'", ';', '--', 'OR', 'DROP']
        if any(c in v.upper() for c in dangerous_chars):
            raise ValueError('invalid characters in server name')
        return v.strip()
    
    @validator('initial_balance')
    def validate_balance(cls, v):
        if v < 0:
            raise ValueError('balance cannot be negative')
        if v > 1_000_000_000:
            raise ValueError('balance too large')
        return v
\`\`\`

### 2. 敏感信息处理

\`\`\`python
# src/common/security/secret_manager.py
class SecretManager:
    """密钥管理"""
    
    @staticmethod
    def mask_password(password: str) -> str:
        """密码脱敏"""
        if len(password) <= 4:
            return "****"
        return password[:2] + "****" + password[-2:]
    
    @staticmethod
    def mask_dict(data: Dict, sensitive_keys: List[str]) -> Dict:
        """字典脱敏"""
        result = data.copy()
        for key in sensitive_keys:
            if key in result:
                result[key] = SecretManager.mask_password(result[key])
        return result

# 日志中自动脱敏
logger.info(
    "Account created",
    account_id="ACC_123",
    login=5049130509,
    password=SecretManager.mask_password(password)  # 输出: ab****yz
)
\`\`\`

---

## 部署架构

### Docker Compose部署

\`\`\`yaml
version: '3.8'

services:
  dashboard:
    build:
      context: .
      dockerfile: Dockerfile
    command: uvicorn src.services.dashboard.api.app:app --host 0.0.0.0 --port 8000
    ports:
      - "8000:8000"
    environment:
      - ENV=production
      - DATABASE_URL=postgresql://user:pass@db:5432/evotrade
    depends_on:
      - db
      - orchestrator
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
  
  orchestrator:
    build:
      context: .
      dockerfile: Dockerfile
    command: uvicorn src.services.orchestrator.api.app:app --host 0.0.0.0 --port 8002
    ports:
      - "8002:8002"
    environment:
      - ENV=production
      - DATABASE_URL=postgresql://user:pass@db:5432/evotrade
    depends_on:
      - db
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8002/health"]
      interval: 30s
      timeout: 10s
      retries: 3
  
  execution:
    build:
      context: .
      dockerfile: Dockerfile
    command: uvicorn src.services.execution.api.app:app --host 0.0.0.0 --port 8003
    ports:
      - "8003:8003"
    environment:
      - ENV=production
      - DATABASE_URL=postgresql://user:pass@db:5432/evotrade
      - MT5_LOGIN=${MT5_LOGIN}
      - MT5_PASSWORD=${MT5_PASSWORD}
      - MT5_SERVER=${MT5_SERVER}
    depends_on:
      - db
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8003/health"]
      interval: 30s
      timeout: 10s
      retries: 3
  
  db:
    image: postgres:15
    environment:
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
      - POSTGRES_DB=evotrade
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U user"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  pgdata:
\`\`\`

---

## 代码规范

### 命名规范

\`\`\`python
# 类名: PascalCase
class AccountService:
    pass

# 函数/方法名: snake_case
def create_account():
    pass

# 常量: UPPER_SNAKE_CASE
MAX_RETRY_COUNT = 3
DATABASE_URL = "..."

# 变量: snake_case
account_id = "ACC_123"
total_balance = 10000.0

# 私有成员: _前缀
class MyClass:
    def __init__(self):
        self._private_var = 10
    
    def _private_method(self):
        pass
\`\`\`

### 文档字符串

\`\`\`python
def create_account(
    login: int,
    server: str,
    initial_balance: float
) -> Account:
    """
    创建账户
    
    Args:
        login: MT5账号
        server: 服务器名称
        initial_balance: 初始资金
    
    Returns:
        创建的账户对象
    
    Raises:
        ValidationException: 输入验证失败
        DuplicateEntityException: 账号已存在
        DatabaseException: 数据库操作失败
    
    Example:
        >>> account = create_account(
        ...     login=5049130509,
        ...     server="MetaQuotes-Demo",
        ...     initial_balance=10000.0
        ... )
        >>> print(account.id)
        'ACC_12345678'
    """
    ...
\`\`\`

---

## 总结

本架构设计遵循**企业级标准**，体现了资深架构师和开发人员的最佳实践：

### ✅ 核心特征

1. **清晰的分层架构**: Presentation → Business → Data Access
2. **完善的异常处理**: 业务异常体系 + 统一错误处理
3. **结构化日志**: JSON格式，便于监控和分析  
4. **Repository模式**: 分离数据访问逻辑
5. **Service模式**: 封装业务逻辑
6. **Factory模式**: 封装对象创建
7. **Validator模式**: 集中验证逻辑
8. **依赖注入**: 降低耦合，提高可测试性
9. **事务管理**: 保证数据一致性
10. **重试和熔断**: 提高系统稳定性
11. **缓存策略**: 提升性能
12. **安全设计**: 输入验证 + 敏感信息保护
13. **完整测试**: 单元测试 + 集成测试 + E2E测试

### ✅ 系统特性

- **高可维护性**: 代码清晰，职责明确，易于理解和修改
- **高可测试性**: 依赖注入，Mock友好，测试覆盖完整
- **高可扩展性**: 插件式架构，易于添加新功能
- **高稳定性**: 完善的错误处理、重试和熔断机制
- **高性能**: 缓存、异步、连接池优化
- **高安全性**: 输入验证、权限控制、敏感信息加密

---

**版本**: v2.0  
**最后更新**: 2026-04-10  
**维护者**: Evo Trade Team

