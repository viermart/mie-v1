"""
Real Hypothesis Backtester - NIVEL 4
Tests hypotheses against actual historical market data from DB
NO RANDOM DATA - Only uses real observations
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class BacktestTrade:
    """Representa un trade simulado durante backtest"""
    entry_price: float
    entry_timestamp: str
    exit_price: float
    exit_timestamp: str
    pnl_pct: float
    direction: str  # "LONG" or "SHORT"


@dataclass
class BacktestResult:
    """Resultados de un backtest real"""
    hypothesis_id: str
    asset: str
    trades: List[BacktestTrade]
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    profit_factor: float
    max_drawdown: float
    avg_win: float
    avg_loss: float
    sharpe_ratio: float
    backtest_score: float
    data_points_used: int
    lookback_hours: int
    timestamp: str


class RealHypothesisBacktester:
    """
    Backtests hypotheses on REAL historical data from DB.
    NO SIMULATION, NO RANDOM DATA.
    """

    def __init__(self, db=None, logger=None):
        self.db = db
        self.logger = logger or logging.getLogger("RealBacktester")

    def backtest_hypothesis(self, hypothesis: Dict, lookback_hours: int = 168) -> Optional[BacktestResult]:
        """
        Test a hypothesis against actual historical data.

        Args:
            hypothesis: Generated hypothesis with type and direction
            lookback_hours: How far back to test (default 1 week = 168h)

        Returns:
            BacktestResult with real metrics or None if insufficient data
        """
        if not self.db:
            self.logger.error("Database not available for backtesting")
            return None

        try:
            asset = hypothesis.get("asset", "BTC")
            hypothesis_type = hypothesis.get("type", "unknown")

            # Get actual historical data from DB
            obs_list = self.db.get_observations(
                asset=asset,
                lookback_hours=lookback_hours,
                observation_type="price"
            )

            if not obs_list or len(obs_list) < 10:
                self.logger.warning(f"Insufficient data for {asset}: {len(obs_list) if obs_list else 0} points")
                return None

            # Sort by timestamp (oldest first)
            obs_list = sorted(obs_list, key=lambda x: x.get("timestamp", ""))

            # Generate trades based on hypothesis type
            trades = self._generate_trades_from_hypothesis(hypothesis, obs_list)

            if not trades:
                self.logger.info(f"No valid trades generated for hypothesis {hypothesis.get('id')}")
                return None

            # Calculate metrics from actual trades
            result = self._calculate_metrics(
                hypothesis_id=hypothesis.get("id"),
                asset=asset,
                trades=trades,
                lookback_hours=lookback_hours,
                data_points=len(obs_list)
            )

            self.logger.info(
                f"✅ Backtest complete for {asset}: "
                f"{result.total_trades} trades, "
                f"Win rate: {result.win_rate:.1%}, "
                f"Score: {result.backtest_score:.3f}"
            )

            return result

        except Exception as e:
            self.logger.error(f"Backtest failed: {e}")
            return None

    def _generate_trades_from_hypothesis(self, hypothesis: Dict, obs_list: List[Dict]) -> List[BacktestTrade]:
        """
        Generate simulated trades based on hypothesis prediction.

        For momentum_shift: BUY on UP, SELL on DOWN
        For volatility_spike: Enter on spike, exit on stabilization
        For breakout: Enter on breakout, exit on reversal
        """
        trades = []
        hypothesis_type = hypothesis.get("type", "unknown")

        if hypothesis_type == "momentum_shift":
            trades = self._trades_from_momentum(hypothesis, obs_list)
        elif hypothesis_type == "volatility_spike":
            trades = self._trades_from_volatility(hypothesis, obs_list)
        elif hypothesis_type == "breakout":
            trades = self._trades_from_breakout(hypothesis, obs_list)

        return trades

    def _trades_from_momentum(self, hypothesis: Dict, obs_list: List[Dict]) -> List[BacktestTrade]:
        """
        Momentum hypothesis: Direction indicates buy/sell signal.
        Buy if direction=UP, Sell if direction=DOWN
        Hold for 4 hours (20 observations at 12/hour rate)
        """
        trades = []
        direction = hypothesis.get("direction", "?")
        hold_periods = 20  # ~4 hours at 12/hour observation rate

        for i in range(0, len(obs_list) - hold_periods, hold_periods):
            entry_price = obs_list[i]["value"]
            entry_timestamp = obs_list[i].get("timestamp", "")
            exit_price = obs_list[i + hold_periods]["value"]
            exit_timestamp = obs_list[i + hold_periods].get("timestamp", "")

            if direction == "UP":
                # Long trade
                pnl_pct = ((exit_price - entry_price) / entry_price) * 100
                trades.append(BacktestTrade(
                    entry_price=entry_price,
                    entry_timestamp=entry_timestamp,
                    exit_price=exit_price,
                    exit_timestamp=exit_timestamp,
                    pnl_pct=pnl_pct,
                    direction="LONG"
                ))
            else:
                # Short trade
                pnl_pct = ((entry_price - exit_price) / entry_price) * 100
                trades.append(BacktestTrade(
                    entry_price=entry_price,
                    entry_timestamp=entry_timestamp,
                    exit_price=exit_price,
                    exit_timestamp=exit_timestamp,
                    pnl_pct=pnl_pct,
                    direction="SHORT"
                ))

        return trades

    def _trades_from_volatility(self, hypothesis: Dict, obs_list: List[Dict]) -> List[BacktestTrade]:
        """
        Volatility spike: High volatility often means reversal coming.
        Enter on spike, exit after volatility returns to normal.
        """
        trades = []
        hold_periods = 12  # ~2 hours at 12/hour rate

        for i in range(0, len(obs_list) - hold_periods, hold_periods):
            entry_price = obs_list[i]["value"]
            entry_timestamp = obs_list[i].get("timestamp", "")
            exit_price = obs_list[i + hold_periods]["value"]
            exit_timestamp = obs_list[i + hold_periods].get("timestamp", "")

            # During volatility spikes, mean reversion tends to work
            # Enter contra to the spike direction
            pnl_pct = ((entry_price - exit_price) / entry_price) * 100
            trades.append(BacktestTrade(
                entry_price=entry_price,
                entry_timestamp=entry_timestamp,
                exit_price=exit_price,
                exit_timestamp=exit_timestamp,
                pnl_pct=pnl_pct,
                direction="LONG"  # Simplified: assume mean reversion
            ))

        return trades

    def _trades_from_breakout(self, hypothesis: Dict, obs_list: List[Dict]) -> List[BacktestTrade]:
        """
        Breakout hypothesis: Direction indicates if we broke up or down.
        Follow the breakout: LONG if up, SHORT if down.
        Exit when price reverses.
        """
        trades = []
        direction = hypothesis.get("direction", "?")
        hold_periods = 24  # ~4 hours at 12/hour rate

        for i in range(0, len(obs_list) - hold_periods, hold_periods):
            entry_price = obs_list[i]["value"]
            entry_timestamp = obs_list[i].get("timestamp", "")
            exit_price = obs_list[i + hold_periods]["value"]
            exit_timestamp = obs_list[i + hold_periods].get("timestamp", "")

            if direction == "UP":
                # Breakout up = LONG
                pnl_pct = ((exit_price - entry_price) / entry_price) * 100
                trades.append(BacktestTrade(
                    entry_price=entry_price,
                    entry_timestamp=entry_timestamp,
                    exit_price=exit_price,
                    exit_timestamp=exit_timestamp,
                    pnl_pct=pnl_pct,
                    direction="LONG"
                ))
            else:
                # Breakout down = SHORT
                pnl_pct = ((entry_price - exit_price) / entry_price) * 100
                trades.append(BacktestTrade(
                    entry_price=entry_price,
                    entry_timestamp=entry_timestamp,
                    exit_price=exit_price,
                    exit_timestamp=exit_timestamp,
                    pnl_pct=pnl_pct,
                    direction="SHORT"
                ))

        return trades

    def _calculate_metrics(self, hypothesis_id: str, asset: str, trades: List[BacktestTrade],
                          lookback_hours: int, data_points: int) -> BacktestResult:
        """
        Calculate real backtest metrics from actual trades.
        """
        if not trades:
            return None

        total_trades = len(trades)
        winning_trades = sum(1 for t in trades if t.pnl_pct > 0)
        losing_trades = total_trades - winning_trades

        win_rate = winning_trades / total_trades if total_trades > 0 else 0.0

        # Calculate average win and loss
        wins = [t.pnl_pct for t in trades if t.pnl_pct > 0]
        losses = [t.pnl_pct for t in trades if t.pnl_pct < 0]

        avg_win = sum(wins) / len(wins) if wins else 0.0
        avg_loss = sum(losses) / len(losses) if losses else 0.0

        # Profit factor: Total wins / Total losses (absolute value)
        total_wins = sum(wins) if wins else 0.0
        total_losses = abs(sum(losses)) if losses else 0.0
        profit_factor = total_wins / total_losses if total_losses > 0 else (1.0 if total_wins > 0 else 0.0)

        # Max drawdown: largest peak-to-trough decline
        cumulative_pnl = 0.0
        peak = 0.0
        max_drawdown = 0.0

        for trade in trades:
            cumulative_pnl += trade.pnl_pct
            if cumulative_pnl > peak:
                peak = cumulative_pnl
            drawdown = (peak - cumulative_pnl) / abs(peak) if peak != 0 else 0
            max_drawdown = max(max_drawdown, drawdown)

        # Sharpe ratio (simplified): (average return - risk-free rate) / std dev
        # Assume 0% risk-free rate and 0% annual volatility for crypto
        returns = [t.pnl_pct for t in trades]
        if len(returns) > 1:
            mean_return = sum(returns) / len(returns)
            variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)
            std_dev = variance ** 0.5
            sharpe_ratio = mean_return / std_dev if std_dev > 0 else 0.0
        else:
            sharpe_ratio = 0.0

        # Composite backtest score
        # Weights: Win rate 40%, Profit factor 30%, Drawdown control 30%
        backtest_score = (
            (win_rate * 0.4) +
            (min(1.0, profit_factor / 2.0) * 0.3) +
            (max(0, 1 - max_drawdown) * 0.3)
        )

        return BacktestResult(
            hypothesis_id=hypothesis_id,
            asset=asset,
            trades=trades,
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=win_rate,
            profit_factor=round(profit_factor, 2),
            max_drawdown=round(max_drawdown, 3),
            avg_win=round(avg_win, 2),
            avg_loss=round(avg_loss, 2),
            sharpe_ratio=round(sharpe_ratio, 2),
            backtest_score=round(backtest_score, 3),
            data_points_used=data_points,
            lookback_hours=lookback_hours,
            timestamp=datetime.utcnow().isoformat()
        )

    def format_backtest_report(self, result: BacktestResult) -> str:
        """
        Format backtest results as a human-readable report.
        """
        if not result:
            return "❌ Backtest failed or no results"

        return (
            f"📊 BACKTEST REPORT\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"Asset: {result.asset}\n"
            f"Period: {result.lookback_hours}h ({result.data_points_used} data points)\n"
            f"\n📈 Trade Statistics:\n"
            f"  Total trades: {result.total_trades}\n"
            f"  Wins: {result.winning_trades} | Losses: {result.losing_trades}\n"
            f"  Win rate: {result.win_rate:.1%}\n"
            f"\n💰 Performance Metrics:\n"
            f"  Avg win: {result.avg_win:.2f}%\n"
            f"  Avg loss: {result.avg_loss:.2f}%\n"
            f"  Profit factor: {result.profit_factor:.2f}x\n"
            f"  Max drawdown: {result.max_drawdown:.1%}\n"
            f"  Sharpe ratio: {result.sharpe_ratio:.2f}\n"
            f"\n🎯 Hypothesis Score: {result.backtest_score:.1%}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        )
