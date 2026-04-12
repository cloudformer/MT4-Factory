"""MT5主机模型"""
from datetime import datetime
from sqlalchemy import Column, String, Integer, Boolean, Float, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class MT5Host(Base):
    """MT5主机配置"""
    __tablename__ = 'mt5_hosts'

    # 主键
    id = Column(String(32), primary_key=True)

    # 基本信息
    name = Column(String(255), nullable=False, comment='主机名称')
    host_type = Column(String(20), nullable=False, comment='类型: demo/real')

    # 连接信息
    host = Column(String(255), nullable=False, comment='主机地址')
    port = Column(Integer, nullable=False, default=9090, comment='端口')
    api_key = Column(String(255), comment='API密钥')
    timeout = Column(Integer, default=10, comment='超时时间(秒)')

    # MT5账户信息
    login = Column(Integer, comment='MT5登录账号')
    password = Column(String(255), comment='MT5密码')
    server = Column(String(255), comment='MT5服务器')

    # 配置选项
    use_investor = Column(Boolean, default=True, comment='使用只读账户')
    enabled = Column(Boolean, default=True, comment='是否启用')

    # 权重和标签
    weight = Column(Float, default=1.0, comment='权重（负载均衡）')
    tags = Column(Text, comment='标签（JSON数组字符串）')

    # 备注
    notes = Column(String(500), comment='备注')

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        """转换为字典"""
        import json

        tags_list = []
        if self.tags:
            try:
                tags_list = json.loads(self.tags)
            except:
                tags_list = []

        return {
            'id': self.id,
            'name': self.name,
            'host_type': self.host_type,
            'host': self.host,
            'port': self.port,
            'api_key': self.api_key,
            'timeout': self.timeout,
            'login': self.login,
            'password': '******' if self.password else None,  # 隐藏密码
            'server': self.server,
            'use_investor': self.use_investor,
            'enabled': self.enabled,
            'weight': self.weight,
            'tags': tags_list,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
