"""初始化MT5主机配置数据"""
import sys
import os
import json
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


def seed_mt5_hosts():
    """初始化MT5主机配置"""
    print("🌱 开始初始化MT5主机配置...")

    # 创建数据库连接
    engine = create_engine('sqlite:///./data/evo_trade.db')
    Session = sessionmaker(bind=engine)
    session = Session()

    # Demo主机配置
    demo_hosts = [
        {
            'id': 'demo_1',
            'name': 'Demo Worker 1',
            'host_type': 'demo',
            'host': '192.168.1.101',
            'port': 9090,
            'api_key': 'demo_key_mock',
            'timeout': 10,
            'login': 5049130509,
            'password': 'mock_password',
            'server': 'MetaQuotes-Demo',
            'use_investor': True,
            'enabled': True,
            'weight': 1.0,
            'tags': json.dumps(['demo', 'validation']),
            'notes': 'Demo验证主机'
        },
        {
            'id': 'demo_2',
            'name': 'Demo Worker 2',
            'host_type': 'demo',
            'host': '192.168.1.102',
            'port': 9090,
            'api_key': 'demo_key_mock_2',
            'timeout': 10,
            'login': 5049130510,
            'password': 'mock_password',
            'server': 'MetaQuotes-Demo',
            'use_investor': True,
            'enabled': False,
            'weight': 1.0,
            'tags': json.dumps(['demo', 'validation', 'backup']),
            'notes': 'Demo备份主机（默认禁用）'
        }
    ]

    # Real主机配置
    real_hosts = [
        {
            'id': 'real_icm_1',
            'name': 'ICMarkets Real Worker 1',
            'host_type': 'real',
            'host': '52.10.20.101',
            'port': 9090,
            'api_key': 'real_key_mock',
            'timeout': 15,
            'login': 8012345678,
            'password': 'mock_real_password',
            'server': 'ICMarkets-Live',
            'use_investor': False,
            'enabled': True,
            'weight': 2.0,
            'tags': json.dumps(['real', 'icmarkets', 'primary']),
            'notes': 'ICMarkets主交易主机'
        },
        {
            'id': 'real_icm_2',
            'name': 'ICMarkets Real Worker 2',
            'host_type': 'real',
            'host': '52.10.20.102',
            'port': 9090,
            'api_key': 'real_key_mock_2',
            'timeout': 15,
            'login': 8012345679,
            'password': 'mock_real_password',
            'server': 'ICMarkets-Live',
            'use_investor': False,
            'enabled': True,
            'weight': 1.0,
            'tags': json.dumps(['real', 'icmarkets', 'backup']),
            'notes': 'ICMarkets备份主机'
        },
        {
            'id': 'real_pep_1',
            'name': 'Pepperstone Real Worker 1',
            'host_type': 'real',
            'host': '52.10.20.103',
            'port': 9090,
            'api_key': 'real_key_mock_3',
            'timeout': 15,
            'login': 9012345678,
            'password': 'mock_real_password',
            'server': 'Pepperstone-Live',
            'use_investor': False,
            'enabled': False,
            'weight': 1.0,
            'tags': json.dumps(['real', 'pepperstone']),
            'notes': 'Pepperstone交易主机（默认禁用）'
        }
    ]

    all_hosts = demo_hosts + real_hosts

    try:
        # 检查是否已有数据
        existing_count = session.execute(text("SELECT COUNT(*) FROM mt5_hosts")).scalar()

        if existing_count > 0:
            print(f"⚠️  数据库中已有 {existing_count} 个MT5主机配置，跳过初始化")
            session.close()
            return

        # 插入数据
        for host_data in all_hosts:
            session.execute(text("""
                INSERT INTO mt5_hosts (
                    id, name, host_type, host, port, api_key, timeout,
                    login, password, server, use_investor, enabled, weight, tags, notes,
                    created_at, updated_at
                ) VALUES (
                    :id, :name, :host_type, :host, :port, :api_key, :timeout,
                    :login, :password, :server, :use_investor, :enabled, :weight, :tags, :notes,
                    :created_at, :updated_at
                )
            """), {
                **host_data,
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            })
            print(f"  ✅ 添加: {host_data['name']} ({host_data['id']})")

        session.commit()
        print(f"🎉 成功初始化 {len(all_hosts)} 个MT5主机配置")
        session.close()

    except Exception as e:
        session.rollback()
        session.close()
        print(f"❌ 初始化失败: {str(e)}")
        raise


if __name__ == '__main__':
    seed_mt5_hosts()
