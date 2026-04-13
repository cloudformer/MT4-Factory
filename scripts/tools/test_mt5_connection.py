#!/usr/bin/env python3
"""MT5连接测试工具"""
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.common.mt5 import mt5_manager
from src.common.config.settings import settings


def main():
    """测试MT5连接"""
    print("=" * 60)
    print("MT5 连接测试工具")
    print("=" * 60)

    # 显示配置信息
    mt5_config = settings.get("mt5", {})
    print("\n📋 配置信息:")
    print(f"  Company: {mt5_config.get('company', 'N/A')}")
    print(f"  Server: {mt5_config.get('server', 'N/A')}")
    print(f"  Login: {mt5_config.get('login', 'N/A')}")
    print(f"  Proxy: {'启用' if mt5_config.get('proxy', {}).get('enabled') else '禁用'}")

    # 测试连接
    print("\n🔄 测试连接...")
    print("-" * 60)

    # 测试1: 交易模式
    print("\n【测试1】交易模式（主密码）")
    try:
        success = mt5_manager.connect(use_investor=False)
        if success:
            client = mt5_manager.get_client()
            account = client.account_info()
            if account:
                print(f"✅ 连接成功")
                print(f"   账号: {account.login}")
                print(f"   服务器: {account.server}")
                print(f"   余额: {account.balance} {account.currency}")
                print(f"   净值: {account.equity} {account.currency}")
                print(f"   杠杆: 1:{account.leverage}")
                print(f"   可用保证金: {account.margin_free} {account.currency}")
                print(f"   交易权限: {'✅ 是' if account.trade_allowed else '❌ 否'}")
            else:
                print("❌ 无法获取账户信息")
        else:
            print("❌ 连接失败")
            error = client.last_error()
            print(f"   错误: {error}")
    except Exception as e:
        print(f"❌ 连接异常: {e}")
    finally:
        mt5_manager.disconnect()

    # 测试2: 投资者模式（如果配置了投资者密码）
    investor_pwd = mt5_config.get('investor_password')
    if investor_pwd:
        print("\n【测试2】投资者模式（只读密码）")
        try:
            success = mt5_manager.connect(use_investor=True)
            if success:
                client = mt5_manager.get_client()
                account = client.account_info()
                if account:
                    print(f"✅ 连接成功（只读模式）")
                    print(f"   账号: {account.login}")
                    print(f"   余额: {account.balance} {account.currency}")
                    print(f"   交易权限: {'✅ 是' if account.trade_allowed else '❌ 否（预期）'}")
                else:
                    print("❌ 无法获取账户信息")
            else:
                print("❌ 连接失败")
        except Exception as e:
            print(f"❌ 连接异常: {e}")
        finally:
            mt5_manager.disconnect()

    # 测试3: 获取实时报价
    print("\n【测试3】获取实时报价")
    try:
        mt5_manager.connect(use_investor=False)
        client = mt5_manager.get_client()

        test_symbols = ['EURUSD', 'GBPUSD', 'USDJPY']
        for symbol in test_symbols:
            tick = client.symbol_info_tick(symbol)
            if tick:
                spread = tick.ask - tick.bid
                print(f"✅ {symbol:8} - Bid: {tick.bid:.5f}, Ask: {tick.ask:.5f}, Spread: {spread:.5f}")
            else:
                print(f"❌ {symbol:8} - 无法获取报价")
    except Exception as e:
        print(f"❌ 获取报价异常: {e}")
    finally:
        mt5_manager.disconnect()

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
