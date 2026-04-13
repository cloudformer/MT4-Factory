#!/usr/bin/env python3
"""策略注册管理脚本"""
import requests
import json
import sys
import os
from typing import List, Dict

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.common.config.settings import settings

# 从配置读取Orchestrator服务URL
ORCHESTRATOR_URL = settings.get("service_urls", {}).get("orchestrator", "http://127.0.0.1:8002")


def get_registration_summary():
    """获取注册概览"""
    response = requests.get(f"{ORCHESTRATOR_URL}/registration/summary")
    return response.json()


def get_candidates():
    """获取所有候选策略"""
    response = requests.get(f"{ORCHESTRATOR_URL}/registration/candidates")
    return response.json()


def get_active():
    """获取所有激活策略"""
    response = requests.get(f"{ORCHESTRATOR_URL}/registration/active")
    return response.json()


def evaluate_strategy(strategy_id):
    """评估单个策略"""
    response = requests.get(f"{ORCHESTRATOR_URL}/registration/evaluate/{strategy_id}")
    return response.json()


def activate_strategy(strategy_id, force=False):
    """激活策略"""
    response = requests.post(
        f"{ORCHESTRATOR_URL}/registration/activate/{strategy_id}",
        json={"force": force}
    )
    return response.json()


def deactivate_strategy(strategy_id, reason=None):
    """停用策略"""
    response = requests.post(
        f"{ORCHESTRATOR_URL}/registration/deactivate/{strategy_id}",
        json={"reason": reason}
    )
    return response.json()


def restore_strategy(strategy_id):
    """恢复归档的策略到候选状态"""
    response = requests.post(
        f"{ORCHESTRATOR_URL}/registration/restore/{strategy_id}"
    )
    return response.json()


def delete_strategy(strategy_id):
    """永久删除策略"""
    response = requests.delete(
        f"{ORCHESTRATOR_URL}/registration/delete/{strategy_id}"
    )
    return response.json()


def batch_evaluate():
    """批量评估（自动激活符合条件的）"""
    response = requests.post(f"{ORCHESTRATOR_URL}/registration/batch-evaluate")
    return response.json()


def filter_recommended(candidates: List[Dict], min_score: float = 65.0) -> List[Dict]:
    """过滤出推荐的策略"""
    recommended = []
    for candidate in candidates:
        quality_score = candidate.get('quality_score', 0)
        if quality_score >= min_score:
            recommended.append(candidate)

    # 按分数排序（从高到低）
    recommended.sort(key=lambda x: x.get('quality_score', 0), reverse=True)
    return recommended


def print_summary():
    """打印注册概览"""
    summary = get_registration_summary()
    print("\n" + "="*60)
    print("📊 策略注册概览")
    print("="*60)
    print(f"总策略数: {summary['total']}")
    print(f"  ✅ 激活 (Active):    {summary['active']}")
    print(f"  ⏸️  候选 (Candidate): {summary['candidate']}")
    print(f"  📦 归档 (Archived):  {summary['archived']}")
    print("\n激活标准:")
    criteria = summary['activation_criteria']
    print(f"  • 推荐度分数 ≥ {criteria['min_recommendation_score']}")
    print(f"  • 收益率 ≥ {criteria['min_total_return']:.1%}")
    print(f"  • Sharpe比率 ≥ {criteria['min_sharpe_ratio']}")
    print(f"  • 最大回撤 ≤ {criteria['max_drawdown']:.1%}")
    print("="*60 + "\n")


def print_candidates_table(candidates: List[Dict]):
    """打印候选策略表格"""
    if not candidates:
        print("没有候选策略")
        return

    print(f"\n找到 {len(candidates)} 个候选策略:\n")
    print(f"{'序号':<4} {'策略ID':<15} {'策略名称':<15} {'质量分数':<10} {'品种':<10} {'状态'}")
    print("-" * 80)

    for i, candidate in enumerate(candidates, 1):
        strategy_id = candidate['id']
        name = candidate['name']
        quality_score = candidate.get('quality_score', 0)
        symbol = candidate.get('backtested_symbol', '-')
        status = candidate['status']

        score_color = "🟢" if quality_score >= 80 else "🔵" if quality_score >= 65 else "🟡" if quality_score >= 50 else "🔴"
        print(f"{i:<4} {strategy_id:<15} {name:<15} {score_color} {quality_score:>6.1f}   {symbol:<10} {status}")


def main():
    """主函数"""
    import sys

    if len(sys.argv) < 2:
        print("\n策略注册管理工具")
        print("\n用法:")
        print("  python scripts/manage_registration.py [命令] [参数]")
        print("\n命令:")
        print("  summary              - 显示注册概览")
        print("  list-candidates      - 列出所有候选策略")
        print("  list-active          - 列出所有激活策略")
        print("  filter [min_score]   - 过滤推荐的候选策略（默认≥65分）")
        print("  evaluate <id>        - 评估单个策略")
        print("  activate <id>        - 激活单个策略")
        print("  activate-force <id>  - 强制激活策略（忽略质量检查）")
        print("  deactivate <id>      - 停用策略")
        print("  archive <id>         - 归档策略（只能归档候选状态）")
        print("  restore <id>         - 恢复归档的策略到候选状态")
        print("  delete <id>          - 永久删除策略（不可恢复）")
        print("  batch-evaluate       - 批量评估并自动激活符合条件的策略")
        print("\n示例:")
        print("  python scripts/manage_registration.py summary")
        print("  python scripts/manage_registration.py filter 70")
        print("  python scripts/manage_registration.py activate STR_xxx")
        print("  python scripts/manage_registration.py archive STR_xxx")
        print("  python scripts/manage_registration.py restore STR_xxx")
        print("  python scripts/manage_registration.py batch-evaluate")
        return

    command = sys.argv[1]

    try:
        if command == "summary":
            print_summary()

        elif command == "list-candidates":
            print_summary()
            candidates = get_candidates()
            print_candidates_table(candidates)

        elif command == "list-active":
            print_summary()
            active = get_active()
            print(f"\n找到 {len(active)} 个激活策略:\n")
            print_candidates_table(active)

        elif command == "filter":
            min_score = float(sys.argv[2]) if len(sys.argv) > 2 else 65.0
            print_summary()
            candidates = get_candidates()
            recommended = filter_recommended(candidates, min_score)
            print(f"\n🎯 推荐策略（质量分数 ≥ {min_score}）:")
            print_candidates_table(recommended)

            if recommended:
                print(f"\n💡 提示: 使用以下命令激活这些策略:")
                for candidate in recommended[:5]:  # 只显示前5个
                    print(f"  python scripts/manage_registration.py activate {candidate['id']}")

        elif command == "evaluate":
            if len(sys.argv) < 3:
                print("❌ 错误: 缺少策略ID")
                print("用法: python scripts/manage_registration.py evaluate <strategy_id>")
                return

            strategy_id = sys.argv[2]
            print(f"\n评估策略: {strategy_id}")
            result = evaluate_strategy(strategy_id)

            print(f"\n评估结果:")
            print(f"  符合激活条件: {'✅ 是' if result['qualified'] else '❌ 否'}")
            print(f"  质量分数: {result['quality_score']:.1f}")
            print(f"  稳定性分数: {result['stability_score']:.2f}")
            print(f"  核心指标通过: {result['core_passed']}/{result['core_required']}")
            print(f"  回测品种: {result['backtested_symbol']}")
            print(f"\n详细原因:")
            for reason in result['reasons']:
                print(f"  {reason}")

        elif command == "activate":
            if len(sys.argv) < 3:
                print("❌ 错误: 缺少策略ID")
                print("用法: python scripts/manage_registration.py activate <strategy_id>")
                return

            strategy_id = sys.argv[2]
            print(f"\n激活策略: {strategy_id}")
            print("💡 提示: 可以激活候选(candidate)或归档(archived)状态的策略")
            result = activate_strategy(strategy_id)

            if result['success']:
                print(f"✅ {result['message']}")
                if 'evaluation' in result:
                    print(f"   质量分数: {result['evaluation']['quality_score']:.1f}")
            else:
                print(f"❌ {result['message']}")

        elif command == "activate-force":
            if len(sys.argv) < 3:
                print("❌ 错误: 缺少策略ID")
                return

            strategy_id = sys.argv[2]
            print(f"\n⚠️  强制激活策略: {strategy_id} (忽略质量检查)")
            result = activate_strategy(strategy_id, force=True)

            if result['success']:
                print(f"✅ {result['message']}")
            else:
                print(f"❌ {result['message']}")

        elif command == "deactivate":
            if len(sys.argv) < 3:
                print("❌ 错误: 缺少策略ID")
                return

            strategy_id = sys.argv[2]
            reason = sys.argv[3] if len(sys.argv) > 3 else None
            print(f"\n停用策略: {strategy_id}")
            result = deactivate_strategy(strategy_id, reason)

            if result['success']:
                print(f"✅ {result['message']}")
            else:
                print(f"❌ {result['message']}")

        elif command == "archive":
            if len(sys.argv) < 3:
                print("❌ 错误: 缺少策略ID")
                print("用法: python scripts/manage_registration.py archive <strategy_id>")
                return

            strategy_id = sys.argv[2]
            reason = sys.argv[3] if len(sys.argv) > 3 else None
            print(f"\n归档策略: {strategy_id}")
            print("⚠️  提示: 只有候选(candidate)状态的策略可以归档")

            # 使用已存在的 archive_strategy 请求
            response = requests.post(
                f"{ORCHESTRATOR_URL}/registration/archive/{strategy_id}",
                json={"reason": reason or '手动归档'}
            )
            result = response.json()

            if result['success']:
                print(f"✅ {result['message']}")
            else:
                print(f"❌ {result['message']}")

        elif command == "restore":
            if len(sys.argv) < 3:
                print("❌ 错误: 缺少策略ID")
                print("用法: python scripts/manage_registration.py restore <strategy_id>")
                return

            strategy_id = sys.argv[2]
            print(f"\n恢复策略: {strategy_id}")
            print("💡 提示: 将归档(archived)状态的策略恢复为候选(candidate)状态")
            result = restore_strategy(strategy_id)

            if result['success']:
                print(f"✅ {result['message']}")
            else:
                print(f"❌ {result['message']}")

        elif command == "delete":
            if len(sys.argv) < 3:
                print("❌ 错误: 缺少策略ID")
                print("用法: python scripts/manage_registration.py delete <strategy_id>")
                return

            strategy_id = sys.argv[2]
            print(f"\n⚠️  警告: 即将永久删除策略: {strategy_id}")
            print("此操作不可逆，将从数据库中彻底删除该策略！")

            confirm = input("请输入 'DELETE' 确认删除: ")
            if confirm != 'DELETE':
                print("删除操作已取消")
                return

            result = delete_strategy(strategy_id)

            if result['success']:
                print(f"🗑️  {result['message']}")
            else:
                print(f"❌ {result['message']}")

        elif command == "batch-evaluate":
            print("\n🔄 批量评估所有候选策略...")
            print("符合条件的策略将自动激活\n")
            result = batch_evaluate()

            print(f"评估完成:")
            print(f"  评估策略数: {result['evaluated']}")
            print(f"  激活策略数: {result['activated']}")

            if result['results']:
                print(f"\n详细结果:")
                for item in result['results']:
                    status = "✅ 已激活" if item['activated'] else "⏸️  未激活"
                    score = item['evaluation']['quality_score']
                    print(f"  {status}  {item['strategy_name']} (ID: {item['strategy_id']}, 分数: {score:.1f})")

        else:
            print(f"❌ 未知命令: {command}")
            print("运行 'python scripts/manage_registration.py' 查看帮助")

    except requests.exceptions.ConnectionError:
        print("\n❌ 错误: 无法连接到Orchestrator服务")
        print("请确保Orchestrator服务正在运行 (http://localhost:8002)")
    except Exception as e:
        print(f"\n❌ 错误: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
