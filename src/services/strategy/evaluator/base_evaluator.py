"""基础评估器 - 包含所有指标计算逻辑"""
from typing import Dict, List, Tuple
import pandas as pd
import numpy as np


class BaseEvaluator:
    """基础评估器类 - 包含通用的回测和指标计算逻辑"""

    def __init__(self, initial_balance: float = 10000.0):
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.trades: List[Dict] = []
        self.equity_curve: List[float] = []

    def run_backtest(self, strategy_code: str, data: pd.DataFrame) -> Dict:
        """
        运行回测

        Args:
            strategy_code: 策略代码
            data: 历史K线数据 (包含 open, high, low, close, volume)

        Returns:
            性能指标字典
        """
        # 1. 动态加载策略
        strategy = self._load_strategy(strategy_code)

        # 2. 初始化
        self.balance = self.initial_balance
        self.trades = []
        self.equity_curve = [self.initial_balance]
        current_position = None  # (direction, entry_price, volume, entry_idx)

        # 3. 逐根K线执行
        for idx in range(50, len(data)):  # 留50根用于计算均线
            # 获取历史数据窗口
            window_data = data.iloc[:idx + 1].copy()

            # 执行策略
            try:
                signal = strategy.on_tick(window_data)
            except Exception as e:
                print(f"策略执行出错: {e}")
                signal = None

            # 处理信号
            if signal and current_position is None:
                # 开仓
                current_position = self._open_position(
                    signal, data.iloc[idx], idx
                )

            elif current_position and signal:
                # 如果有持仓且信号反向，平仓并开新仓
                direction, entry_price, volume, entry_idx = current_position
                if (direction == 'buy' and signal == 'sell') or \
                   (direction == 'sell' and signal == 'buy'):
                    # 平仓
                    self._close_position(current_position, data.iloc[idx], idx)
                    current_position = None

                    # 开新仓
                    current_position = self._open_position(
                        signal, data.iloc[idx], idx
                    )

            # 更新权益曲线
            if current_position:
                direction, entry_price, volume, entry_idx = current_position
                current_price = data.iloc[idx]['close']
                if direction == 'buy':
                    unrealized_pnl = (current_price - entry_price) * volume * 100000  # 标准手
                else:
                    unrealized_pnl = (entry_price - current_price) * volume * 100000

                self.equity_curve.append(self.balance + unrealized_pnl)
            else:
                self.equity_curve.append(self.balance)

        # 4. 平掉最后的持仓
        if current_position:
            self._close_position(current_position, data.iloc[-1], len(data) - 1)

        # 5. 计算性能指标
        return self.calculate_metrics()

    def _load_strategy(self, strategy_code: str):
        """动态加载策略"""
        namespace = {}
        exec(strategy_code, namespace)

        # 查找策略类
        for name, obj in namespace.items():
            if name.startswith('Strategy_') and callable(obj):
                return obj()

        raise ValueError("未找到策略类")

    def _open_position(self, direction: str, bar: pd.Series, idx: int) -> Tuple:
        """开仓"""
        entry_price = bar['close']
        volume = 0.1  # 固定0.1手

        return (direction, entry_price, volume, idx)

    def _close_position(self, position: Tuple, bar: pd.Series, idx: int):
        """平仓"""
        direction, entry_price, volume, entry_idx = position
        exit_price = bar['close']

        # 计算盈亏
        if direction == 'buy':
            pnl = (exit_price - entry_price) * volume * 100000  # 1标准手=100000
        else:
            pnl = (entry_price - exit_price) * volume * 100000

        self.balance += pnl

        # 记录交易
        self.trades.append({
            'entry_time': entry_idx,
            'exit_time': idx,
            'direction': direction,
            'entry_price': entry_price,
            'exit_price': exit_price,
            'volume': volume,
            'pnl': pnl,
            'balance': self.balance
        })

    def calculate_metrics(self) -> Dict:
        """计算完整的性能指标"""
        if not self.trades:
            return self._get_empty_metrics()

        # === 基础指标 ===
        total_return = (self.balance - self.initial_balance) / self.initial_balance
        winning_trades = [t for t in self.trades if t['pnl'] > 0]
        losing_trades = [t for t in self.trades if t['pnl'] < 0]
        win_rate = len(winning_trades) / len(self.trades)

        # 盈亏比
        total_profit = sum([t['pnl'] for t in winning_trades])
        total_loss = abs(sum([t['pnl'] for t in losing_trades]))
        profit_factor = total_profit / total_loss if total_loss > 0 else 0.0

        # === 回撤指标 ===
        equity_array = np.array(self.equity_curve)
        running_max = np.maximum.accumulate(equity_array)
        drawdown = (equity_array - running_max) / running_max
        max_drawdown = abs(drawdown.min())
        avg_drawdown = abs(drawdown[drawdown < 0].mean()) if len(drawdown[drawdown < 0]) > 0 else 0.0

        # 回撤恢复时间
        recovery_factor = total_return / max_drawdown if max_drawdown > 0 else 0.0

        # === 风险指标 ===
        equity_returns = np.diff(equity_array) / equity_array[:-1] if len(equity_array) > 1 else np.array([0])
        volatility = np.std(equity_returns) * np.sqrt(8760)  # 年化波动率

        # Sharpe Ratio
        annual_factor = np.sqrt(8760 / len(equity_returns)) if len(equity_returns) > 0 else 1
        sharpe_ratio = (np.mean(equity_returns) / np.std(equity_returns)) * annual_factor if np.std(equity_returns) > 0 else 0.0

        # Sortino Ratio (只看下行波动)
        downside_returns = equity_returns[equity_returns < 0]
        downside_std = np.std(downside_returns) if len(downside_returns) > 1 else 0.0001
        sortino_ratio = (np.mean(equity_returns) / downside_std) * annual_factor if downside_std > 0 else 0.0

        # Calmar Ratio
        calmar_ratio = total_return / max_drawdown if max_drawdown > 0 else 0.0

        # === 交易特征 ===
        # 平均持仓时间（K线数）
        holding_times = [t['exit_time'] - t['entry_time'] for t in self.trades]
        avg_holding_time = np.mean(holding_times) if holding_times else 0

        # 交易频率（每100根K线的交易数）
        total_bars = len(self.equity_curve)
        trade_frequency = (len(self.trades) / total_bars) * 100 if total_bars > 0 else 0

        # 平均盈利和亏损
        avg_win = np.mean([t['pnl'] for t in winning_trades]) if winning_trades else 0
        avg_loss = np.mean([abs(t['pnl']) for t in losing_trades]) if losing_trades else 0
        avg_win_loss_ratio = avg_win / avg_loss if avg_loss > 0 else 0

        # 最大连续盈亏
        consecutive_wins, consecutive_losses = self._calculate_consecutive_trades()

        # === 稳定性指标 ===
        # 收益稳定性（变异系数的倒数）
        trade_returns = [t['pnl'] / self.initial_balance for t in self.trades]
        cv = np.std(trade_returns) / abs(np.mean(trade_returns)) if np.mean(trade_returns) != 0 else 999
        stability_score = 1 / (1 + cv)  # 0-1之间，越高越稳定

        # 一致性（胜率和盈亏比的均衡性）
        consistency_score = min(win_rate, 1 - win_rate) * 2 * min(profit_factor / 3, 1)

        # === 风险分类 ===
        risk_profile = self._classify_risk(
            win_rate, max_drawdown, sharpe_ratio, profit_factor, volatility
        )

        # === 市场敏感度 ===
        # 滑点敏感度（基于交易频率和平均盈利）
        slippage_sensitivity = self._calculate_slippage_sensitivity(
            trade_frequency, avg_win, avg_loss
        )

        # === 策略适用性评估 ===
        suitability = self._evaluate_suitability(
            total_return, sharpe_ratio, max_drawdown, win_rate,
            profit_factor, stability_score, risk_profile,
            trade_frequency, consecutive_losses
        )

        # === 生成推荐摘要 ===
        recommendation_summary = self._generate_recommendation_summary(
            suitability, total_return, sharpe_ratio, max_drawdown,
            win_rate, profit_factor, stability_score, consecutive_losses
        )

        return {
            # === 基础性能 ===
            'total_return': round(total_return, 4),
            'final_balance': round(self.balance, 2),
            'total_trades': len(self.trades),

            # === 收益指标 ===
            'sharpe_ratio': round(sharpe_ratio, 2),
            'sortino_ratio': round(sortino_ratio, 2),
            'calmar_ratio': round(calmar_ratio, 2),
            'profit_factor': round(profit_factor, 2),
            'win_rate': round(win_rate, 3),
            'avg_win': round(avg_win, 2),
            'avg_loss': round(avg_loss, 2),
            'avg_win_loss_ratio': round(avg_win_loss_ratio, 2),

            # === 风险指标 ===
            'max_drawdown': round(max_drawdown, 3),
            'avg_drawdown': round(avg_drawdown, 3),
            'volatility': round(volatility, 4),
            'recovery_factor': round(recovery_factor, 2),

            # === 交易特征 ===
            'trade_frequency': round(trade_frequency, 2),  # 每100根K线
            'avg_holding_time': round(avg_holding_time, 1),  # K线数
            'max_consecutive_wins': consecutive_wins,
            'max_consecutive_losses': consecutive_losses,

            # === 稳定性 ===
            'stability_score': round(stability_score, 3),  # 0-1
            'consistency_score': round(consistency_score, 3),  # 0-1

            # === 风险分类 ===
            'risk_type': risk_profile['type'],
            'risk_score': risk_profile['score'],  # 0-10
            'risk_level': risk_profile['level'],  # low/medium/high

            # === 市场适应性 ===
            'slippage_sensitivity': slippage_sensitivity,  # low/medium/high
            'market_regime': 'trend' if profit_factor > 2 else 'range',

            # === 策略适用性 ===
            'suitability': suitability,

            # === 推荐摘要（简化版，人类可读）===
            'recommendation_summary': recommendation_summary,

            # === 其他 ===
            'backtest_bars': len(self.equity_curve)
        }

    def _get_empty_metrics(self) -> Dict:
        """无交易时的默认指标"""
        return {
            'total_return': 0.0, 'final_balance': self.initial_balance,
            'total_trades': 0, 'sharpe_ratio': 0.0, 'sortino_ratio': 0.0,
            'calmar_ratio': 0.0, 'profit_factor': 0.0, 'win_rate': 0.0,
            'avg_win': 0.0, 'avg_loss': 0.0, 'avg_win_loss_ratio': 0.0,
            'max_drawdown': 0.0, 'avg_drawdown': 0.0, 'volatility': 0.0,
            'recovery_factor': 0.0, 'trade_frequency': 0.0,
            'avg_holding_time': 0.0, 'max_consecutive_wins': 0,
            'max_consecutive_losses': 0, 'stability_score': 0.0,
            'consistency_score': 0.0, 'risk_type': 'unknown',
            'risk_score': 0, 'risk_level': 'unknown',
            'slippage_sensitivity': 'unknown', 'market_regime': 'unknown',
            'backtest_bars': 0
        }

    def _calculate_consecutive_trades(self) -> tuple:
        """计算最大连续盈亏次数"""
        max_wins = 0
        max_losses = 0
        current_wins = 0
        current_losses = 0

        for trade in self.trades:
            if trade['pnl'] > 0:
                current_wins += 1
                current_losses = 0
                max_wins = max(max_wins, current_wins)
            else:
                current_losses += 1
                current_wins = 0
                max_losses = max(max_losses, current_losses)

        return max_wins, max_losses

    def _classify_risk(self, win_rate: float, max_dd: float, sharpe: float,
                       profit_factor: float, volatility: float) -> Dict:
        """风险分类"""
        # 计算风险分数 (0-10)
        risk_score = 0

        # 胜率贡献 (0-2分)
        if win_rate >= 0.6:
            risk_score += 0
        elif win_rate >= 0.5:
            risk_score += 0.5
        elif win_rate >= 0.4:
            risk_score += 1
        else:
            risk_score += 2

        # 回撤贡献 (0-3分)
        if max_dd <= 0.08:
            risk_score += 0
        elif max_dd <= 0.12:
            risk_score += 1
        elif max_dd <= 0.20:
            risk_score += 2
        else:
            risk_score += 3

        # Sharpe贡献 (0-2分)
        if sharpe >= 2:
            risk_score += 0
        elif sharpe >= 1:
            risk_score += 0.5
        elif sharpe >= 0.5:
            risk_score += 1
        else:
            risk_score += 2

        # 波动率贡献 (0-3分)
        if volatility <= 0.15:
            risk_score += 0
        elif volatility <= 0.25:
            risk_score += 1
        elif volatility <= 0.40:
            risk_score += 2
        else:
            risk_score += 3

        # 确定风险类型
        if profit_factor >= 3 and win_rate < 0.45:
            risk_type = "aggressive_trend"  # 激进趋势型
        elif win_rate >= 0.55 and profit_factor < 2.5:
            risk_type = "conservative_scalp"  # 保守剥头皮
        elif sharpe >= 1.5 and max_dd <= 0.10:
            risk_type = "balanced_stable"  # 平衡稳定型
        elif max_dd >= 0.20:
            risk_type = "high_risk"  # 高风险型
        else:
            risk_type = "moderate"  # 中等型

        # 风险等级
        if risk_score <= 3:
            risk_level = "low"
        elif risk_score <= 6:
            risk_level = "medium"
        else:
            risk_level = "high"

        return {
            'type': risk_type,
            'score': round(risk_score, 1),
            'level': risk_level
        }

    def _calculate_slippage_sensitivity(self, trade_freq: float,
                                       avg_win: float, avg_loss: float) -> str:
        """计算滑点敏感度"""
        # 高频交易对滑点更敏感
        # 小盈利对滑点更敏感

        if trade_freq > 5:  # 每100根K线超过5笔
            if avg_win < 50:  # 平均盈利小于$50
                return "high"
            return "medium"
        elif trade_freq > 2:
            return "medium"
        else:
            return "low"

    def _evaluate_suitability(self, total_return: float, sharpe: float,
                             max_dd: float, win_rate: float, profit_factor: float,
                             stability: float, risk_profile: Dict,
                             trade_freq: float, max_consec_loss: int) -> Dict:
        """评估策略适用性"""

        # === 1. 投资者类型适配 ===
        investor_types = []

        # 保守型投资者
        if max_dd < 0.08 and sharpe > 1.0 and stability > 0.6:
            investor_types.append("conservative")

        # 稳健型投资者
        if max_dd < 0.12 and sharpe > 0.6 and win_rate > 0.45:
            investor_types.append("moderate")

        # 进取型投资者
        if total_return > 0.15 and profit_factor > 3:
            investor_types.append("aggressive")

        # 专业投资者
        if sharpe > 1.5 or (profit_factor > 5 and max_dd < 0.10):
            investor_types.append("professional")

        if not investor_types:
            investor_types = ["general"]  # 通用型

        # === 2. 推荐场景 ===
        recommended_for = []
        not_recommended_for = []

        # 高收益追求者
        if total_return > 0.30:
            recommended_for.append("high_return_seekers")

        # 低回撤追求者
        if max_dd < 0.08:
            recommended_for.append("low_drawdown_seekers")

        # 稳定性追求者
        if stability > 0.6:
            recommended_for.append("stability_seekers")
        else:
            not_recommended_for.append("stability_seekers")

        # 心理承受力强
        if max_consec_loss > 5:
            recommended_for.append("strong_mental_endurance")
            not_recommended_for.append("low_risk_tolerance")

        # === 3. 账户要求 ===
        # 最小建议账户规模
        if risk_profile['level'] == 'high':
            min_account = 10000
        elif risk_profile['level'] == 'medium':
            min_account = 5000
        else:
            min_account = 3000

        # 建议仓位
        if risk_profile['level'] == 'high':
            suggested_position = 0.02  # 2%
        elif risk_profile['level'] == 'medium':
            suggested_position = 0.05  # 5%
        else:
            suggested_position = 0.10  # 10%

        # === 4. 市场环境要求 ===
        market_conditions = []
        if profit_factor > 3:
            market_conditions.append("strong_trend")
        if win_rate > 0.55:
            market_conditions.append("ranging_market")
        if trade_freq < 2:
            market_conditions.append("low_volatility_ok")

        # === 5. 优势与劣势 ===
        strengths = []
        weaknesses = []

        # 收益优势
        if total_return > 0.50:
            strengths.append("exceptional_returns")
        elif total_return > 0.20:
            strengths.append("high_returns")

        # 回撤优势
        if max_dd < 0.08:
            strengths.append("excellent_drawdown_control")
        elif max_dd < 0.12:
            strengths.append("good_drawdown_control")
        else:
            weaknesses.append("high_drawdown_risk")

        # 盈亏比优势
        if profit_factor > 5:
            strengths.append("exceptional_profit_factor")
        elif profit_factor > 2.5:
            strengths.append("high_profit_factor")

        # 稳定性劣势
        if stability < 0.5:
            weaknesses.append("inconsistent_performance")

        # Sharpe劣势
        if sharpe < 0.5:
            weaknesses.append("poor_risk_adjusted_returns")

        # 连续亏损风险
        if max_consec_loss > 5:
            weaknesses.append("high_consecutive_loss_risk")

        # === 6. 关键注意事项 ===
        warnings = []

        if max_consec_loss > 5:
            warnings.append(f"可能连续亏损{max_consec_loss}次，需要强大心理承受力")

        if stability < 0.4:
            warnings.append("收益波动较大，不适合追求稳定的投资者")

        if trade_freq < 1:
            warnings.append("交易频率低，需要耐心等待信号")

        if max_dd > 0.15:
            warnings.append(f"最大回撤{max_dd*100:.1f}%，风险较高")

        # === 7. 综合评分 ===
        # 收益评分 (0-100)
        return_score = min(total_return * 100, 100)

        # 风险评分 (0-100，越高越好)
        risk_score = max(0, 100 - risk_profile['score'] * 10)

        # 稳定性评分 (0-100)
        stability_score = stability * 100

        # 综合推荐度 (0-100)
        overall_score = (
            return_score * 0.4 +      # 40% 收益权重
            risk_score * 0.35 +       # 35% 风险权重
            stability_score * 0.25    # 25% 稳定性权重
        )

        # === 8. 推荐等级 ===
        if overall_score >= 80:
            recommendation = "highly_recommended"
            recommendation_text = "强烈推荐"
        elif overall_score >= 65:
            recommendation = "recommended"
            recommendation_text = "推荐"
        elif overall_score >= 50:
            recommendation = "conditionally_recommended"
            recommendation_text = "条件推荐"
        else:
            recommendation = "not_recommended"
            recommendation_text = "不推荐"

        return {
            # 适用投资者类型
            'investor_types': investor_types,

            # 推荐场景
            'recommended_for': recommended_for,
            'not_recommended_for': not_recommended_for,

            # 账户要求
            'min_account_size': min_account,
            'suggested_position_size': round(suggested_position, 3),

            # 市场环境
            'suitable_market_conditions': market_conditions,

            # 优势与劣势
            'strengths': strengths,
            'weaknesses': weaknesses,

            # 注意事项
            'warnings': warnings,

            # 评分
            'scores': {
                'return': round(return_score, 1),
                'risk': round(risk_score, 1),
                'stability': round(stability_score, 1),
                'overall': round(overall_score, 1)
            },

            # 综合推荐
            'recommendation': recommendation,
            'recommendation_text': recommendation_text
        }

    def _generate_recommendation_summary(self, suitability: Dict, total_return: float,
                                        sharpe: float, max_dd: float, win_rate: float,
                                        profit_factor: float, stability: float,
                                        max_consec_loss: int) -> Dict:
        """生成简洁的推荐摘要"""

        # 推荐度
        score = suitability['scores']['overall']
        recommendation = suitability['recommendation_text']

        # 适合的投资者
        investor_types_cn = {
            'conservative': '保守型',
            'moderate': '稳健型',
            'aggressive': '进取型',
            'professional': '专业型',
            'general': '通用型'
        }
        suitable_investors = [investor_types_cn.get(t, t)
                             for t in suitability['investor_types']]

        # 账户要求
        min_account = suitability['min_account_size']
        suggested_position = suitability['suggested_position_size']

        # 优势（翻译）
        strengths_cn = {
            'exceptional_returns': '收益极高',
            'high_returns': '收益较高',
            'excellent_drawdown_control': '回撤极低',
            'good_drawdown_control': '回撤控制良好',
            'exceptional_profit_factor': '盈亏比极高',
            'high_profit_factor': '盈亏比较高'
        }
        strengths = [strengths_cn.get(s, s) for s in suitability['strengths']]

        # 劣势（翻译）
        weaknesses_cn = {
            'high_drawdown_risk': '回撤风险较高',
            'inconsistent_performance': '不够稳定',
            'poor_risk_adjusted_returns': '风险调整收益低',
            'high_consecutive_loss_risk': f'可能连续亏损{max_consec_loss}次'
        }
        weaknesses = [weaknesses_cn.get(w, w) for w in suitability['weaknesses']]

        # 关键提示
        key_warnings = []
        if max_consec_loss > 5:
            key_warnings.append("需要强大心理承受力")
        if stability < 0.4:
            key_warnings.append("收益波动较大")
        if max_dd > 0.15:
            key_warnings.append("回撤风险较高")

        # 快速事实
        quick_facts = []
        if total_return > 0.50:
            quick_facts.append(f"回测收益 {total_return*100:.1f}%")
        if max_dd < 0.08:
            quick_facts.append(f"最大回撤仅 {max_dd*100:.1f}%")
        if profit_factor > 5:
            quick_facts.append(f"盈亏比 {profit_factor:.1f}")
        if win_rate > 0.60:
            quick_facts.append(f"胜率 {win_rate*100:.0f}%")

        return {
            # 核心推荐
            'recommendation_score': round(score, 1),
            'recommendation_text': recommendation,
            'recommendation_emoji': self._get_recommendation_emoji(score),

            # 适合人群
            'suitable_for': ', '.join(suitable_investors) if suitable_investors else '通用型',

            # 账户要求
            'account_requirement': f"最小${min_account:,}，建议仓位{suggested_position*100:.0f}%",

            # 优势（最多3个）
            'key_strengths': ', '.join(strengths[:3]) if strengths else '暂无突出优势',

            # 劣势（最多3个）
            'key_weaknesses': ', '.join(weaknesses[:3]) if weaknesses else '暂无明显劣势',

            # 关键提示
            'key_warnings': ', '.join(key_warnings) if key_warnings else '无特殊提示',

            # 快速事实
            'quick_facts': ' | '.join(quick_facts) if quick_facts else '',

            # 一句话总结
            'one_line_summary': self._generate_one_line_summary(
                score, total_return, max_dd, profit_factor, stability
            )
        }

    def _get_recommendation_emoji(self, score: float) -> str:
        """获取推荐等级的emoji"""
        if score >= 80:
            return "🌟"
        elif score >= 65:
            return "✅"
        elif score >= 50:
            return "⚠️"
        else:
            return "❌"

    def _generate_one_line_summary(self, score: float, total_return: float,
                                   max_dd: float, profit_factor: float,
                                   stability: float) -> str:
        """生成一句话总结"""

        # 确定主要特征
        if total_return > 1.0 and max_dd < 0.10:
            return "高收益低回撤的优质策略，适合追求稳健高回报的投资者"
        elif total_return > 0.5 and profit_factor > 5:
            return "超高盈亏比策略，适合能承受波动的进取型投资者"
        elif max_dd < 0.08 and stability > 0.6:
            return "低回撤稳定型策略，适合风险厌恶的保守型投资者"
        elif score >= 80:
            return "综合表现优异，强烈推荐使用"
        elif score >= 65:
            return "整体表现良好，推荐在合适条件下使用"
        elif score >= 50:
            return "表现尚可，需根据个人情况谨慎使用"
        else:
            return "综合表现欠佳，建议谨慎考虑或暂不使用"
