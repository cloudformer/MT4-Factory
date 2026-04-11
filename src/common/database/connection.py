"""MySQL 数据库连接管理"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from contextlib import contextmanager
from typing import Generator

from src.common.config.settings import settings


class DatabaseConnection:
    """数据库连接管理器"""

    def __init__(self):
        self._engine = None
        self._session_factory = None
        self._initialize()

    def _initialize(self):
        """初始化数据库连接"""
        db_config = settings.database

        # 检查是否使用URL模式（SQLite）
        if 'url' in db_config:
            db_url = db_config['url']
            self._engine = create_engine(
                db_url,
                connect_args={"check_same_thread": False},
                echo=db_config.get('echo', False)
            )
        else:
            # MySQL配置模式
            db_url = (
                f"mysql+pymysql://{db_config['user']}:{db_config['password']}"
                f"@{db_config['host']}:{db_config['port']}/{db_config['database']}"
                f"?charset=utf8mb4"
            )
            self._engine = create_engine(
                db_url,
                poolclass=QueuePool,
                pool_size=db_config.get('pool_size', 10),
                max_overflow=db_config.get('max_overflow', 20),
                pool_pre_ping=True,
                echo=db_config.get('echo', False)
            )

        # 创建Session工厂
        self._session_factory = sessionmaker(
            bind=self._engine,
            autocommit=False,
            autoflush=False
        )

    @property
    def engine(self):
        """获取引擎"""
        return self._engine

    def get_session(self) -> Session:
        """获取新的Session"""
        return self._session_factory()

    @contextmanager
    def session_scope(self) -> Generator[Session, None, None]:
        """
        Session上下文管理器

        Usage:
            with db.session_scope() as session:
                session.query(...)
        """
        session = self.get_session()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def close(self):
        """关闭所有连接"""
        if self._engine:
            self._engine.dispose()


# 全局数据库实例
db = DatabaseConnection()
