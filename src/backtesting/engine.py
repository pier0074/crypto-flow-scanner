"""
Backtesting engine for testing trading strategies on historical data.
"""
import pandas as pd
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import numpy as np

from src.patterns.fvg import fvg_detector
from src.data.storage import db_manager
from src.data.models import BacktestResult
from src.config.settings import settings


class BacktestEngine:
    """Backtesting engine for pattern-based strategies."""

    def __init__(self, initial_capital: float = None):
        """
        Initialize backtest engine.

        Args:
            initial_capital: Starting capital (default from settings)
        """
        self.initial_capital = initial_capital or settings.BACKTEST_INITIAL_CAPITAL
        self.capital = self.initial_capital
        self.trades = []
        self.equity_curve = []

    def backtest_fvg_strategy(
        self,
        symbol: str,
        timeframe: str,
        start_date: str,
        end_date: str
    ) -> BacktestResult:
        """
        Backtest the FVG (Fair Value Gap) strategy.

        Args:
            symbol: Trading pair symbol
            timeframe: Timeframe string
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)

        Returns:
            BacktestResult object with performance metrics
        """
        print(f"\n{'=' * 60}")
        print(f"Backtesting FVG Strategy")
        print(f"{'=' * 60}")
        print(f"Symbol: {symbol}")
        print(f"Timeframe: {timeframe}")
        print(f"Period: {start_date} to {end_date}")
        print(f"Initial Capital: ${self.initial_capital:,.2f}")
        print(f"{'=' * 60}\n")

        # Reset state
        self.capital = self.initial_capital
        self.trades = []
        self.equity_curve = []

        # Get historical candles
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')

        candles = db_manager.get_candles(
            symbol=symbol,
            timeframe=timeframe,
            start_time=start_dt,
            end_time=end_dt
        )

        if not candles or len(candles) < 100:
            print(f"Error: Not enough candles for backtesting (need at least 100, got {len(candles)})")
            return None

        print(f"Loaded {len(candles)} candles\n")

        # Convert to DataFrame
        df = pd.DataFrame([{
            'timestamp': c.timestamp,
            'open': c.open,
            'high': c.high,
            'low': c.low,
            'close': c.close,
            'volume': c.volume
        } for c in candles])

        df.set_index('timestamp', inplace=True)

        # Run backtest
        print("Running backtest...\n")

        # Use a sliding window approach
        window_size = 100  # Minimum candles needed for pattern detection
        active_trades = []  # Currently open trades

        for i in range(window_size, len(df)):
            # Get window of data for pattern detection
            window_df = df.iloc[max(0, i - window_size):i + 1]
            current_candle = df.iloc[i]
            current_price = current_candle['close']
            current_timestamp = df.index[i]

            # Detect patterns in this window
            patterns = fvg_detector.detect(window_df, symbol, timeframe)

            # Get only the most recent pattern (if any)
            if patterns:
                latest_pattern = patterns[-1]

                # Check if we should enter a trade
                if not active_trades or len(active_trades) == 0:
                    # Check if price touched entry
                    if latest_pattern.direction == 'bullish':
                        if current_candle['low'] <= latest_pattern.entry_price:
                            # Enter long trade
                            trade = self._enter_trade(
                                pattern=latest_pattern,
                                entry_price=latest_pattern.entry_price,
                                entry_time=current_timestamp
                            )
                            active_trades.append(trade)
                    else:  # bearish
                        if current_candle['high'] >= latest_pattern.entry_price:
                            # Enter short trade
                            trade = self._enter_trade(
                                pattern=latest_pattern,
                                entry_price=latest_pattern.entry_price,
                                entry_time=current_timestamp
                            )
                            active_trades.append(trade)

            # Check active trades for exit conditions
            closed_trades = []

            for trade in active_trades:
                exit_signal = self._check_exit(trade, current_candle)

                if exit_signal:
                    # Close the trade
                    self._close_trade(
                        trade=trade,
                        exit_price=exit_signal['price'],
                        exit_time=current_timestamp,
                        exit_reason=exit_signal['reason']
                    )
                    closed_trades.append(trade)

            # Remove closed trades
            for trade in closed_trades:
                active_trades.remove(trade)

            # Record equity
            total_equity = self.capital
            for trade in active_trades:
                # Calculate unrealized P&L
                if trade['direction'] == 'long':
                    pnl = (current_price - trade['entry_price']) * trade['position_size'] / trade['entry_price']
                else:
                    pnl = (trade['entry_price'] - current_price) * trade['position_size'] / trade['entry_price']
                total_equity += pnl

            self.equity_curve.append({
                'timestamp': current_timestamp,
                'equity': total_equity
            })

        # Calculate performance metrics
        result = self._calculate_metrics(symbol, timeframe, start_date, end_date)

        print(f"\n{'=' * 60}")
        print("Backtest Results")
        print(f"{'=' * 60}")
        self._display_results(result)

        # Save to database
        db_manager.save_backtest_result(result)

        return result

    def _enter_trade(self, pattern, entry_price: float, entry_time: datetime) -> Dict:
        """Enter a new trade."""
        # Calculate position size based on risk
        risk_amount = self.capital * (settings.MAX_RISK_PERCENT / 100)
        risk_per_unit = abs(entry_price - pattern.stop_loss)
        position_size = risk_amount / risk_per_unit if risk_per_unit > 0 else 0

        # Limit position size to max percentage of capital
        max_position = self.capital * (settings.POSITION_SIZE_PERCENT / 100)
        position_size = min(position_size, max_position)

        trade = {
            'direction': pattern.direction,
            'entry_price': entry_price,
            'stop_loss': pattern.stop_loss,
            'take_profit': pattern.take_profit,
            'position_size': position_size,
            'entry_time': entry_time,
            'exit_price': None,
            'exit_time': None,
            'exit_reason': None,
            'pnl': None
        }

        return trade

    def _check_exit(self, trade: Dict, candle: pd.Series) -> Optional[Dict]:
        """Check if trade should be exited."""
        if trade['direction'] == 'long':
            # Check stop loss
            if candle['low'] <= trade['stop_loss']:
                return {'price': trade['stop_loss'], 'reason': 'stop_loss'}

            # Check take profit
            if candle['high'] >= trade['take_profit']:
                return {'price': trade['take_profit'], 'reason': 'take_profit'}

        else:  # short
            # Check stop loss
            if candle['high'] >= trade['stop_loss']:
                return {'price': trade['stop_loss'], 'reason': 'stop_loss'}

            # Check take profit
            if candle['low'] <= trade['take_profit']:
                return {'price': trade['take_profit'], 'reason': 'take_profit'}

        return None

    def _close_trade(self, trade: Dict, exit_price: float, exit_time: datetime, exit_reason: str):
        """Close a trade and update capital."""
        if trade['direction'] == 'long':
            pnl = (exit_price - trade['entry_price']) * trade['position_size'] / trade['entry_price']
        else:
            pnl = (trade['entry_price'] - exit_price) * trade['position_size'] / trade['entry_price']

        trade['exit_price'] = exit_price
        trade['exit_time'] = exit_time
        trade['exit_reason'] = exit_reason
        trade['pnl'] = pnl

        self.capital += pnl
        self.trades.append(trade)

    def _calculate_metrics(
        self,
        symbol: str,
        timeframe: str,
        start_date: str,
        end_date: str
    ) -> BacktestResult:
        """Calculate performance metrics."""
        if not self.trades:
            print("No trades executed during backtest period")
            return None

        winning_trades = [t for t in self.trades if t['pnl'] > 0]
        losing_trades = [t for t in self.trades if t['pnl'] <= 0]

        total_trades = len(self.trades)
        win_count = len(winning_trades)
        loss_count = len(losing_trades)
        win_rate = (win_count / total_trades) * 100 if total_trades > 0 else 0

        total_pnl = sum(t['pnl'] for t in self.trades)
        total_pnl_percent = (total_pnl / self.initial_capital) * 100

        avg_win = sum(t['pnl'] for t in winning_trades) / win_count if win_count > 0 else 0
        avg_loss = sum(t['pnl'] for t in losing_trades) / loss_count if loss_count > 0 else 0
        avg_win_percent = (avg_win / self.initial_capital) * 100
        avg_loss_percent = (avg_loss / self.initial_capital) * 100

        largest_win = max((t['pnl'] for t in self.trades), default=0)
        largest_loss = min((t['pnl'] for t in self.trades), default=0)

        # Calculate max drawdown
        equity_series = pd.Series([e['equity'] for e in self.equity_curve])
        running_max = equity_series.expanding().max()
        drawdown = (equity_series - running_max) / running_max
        max_drawdown = abs(drawdown.min()) * 100

        # Calculate Sharpe ratio (simplified)
        returns = equity_series.pct_change().dropna()
        sharpe_ratio = (returns.mean() / returns.std()) * np.sqrt(252) if returns.std() > 0 else 0

        # Profit factor
        total_wins = sum(t['pnl'] for t in winning_trades)
        total_losses = abs(sum(t['pnl'] for t in losing_trades))
        profit_factor = total_wins / total_losses if total_losses > 0 else 0

        result = BacktestResult(
            strategy_name='FVG',
            symbol=symbol,
            timeframe=timeframe,
            start_date=datetime.strptime(start_date, '%Y-%m-%d'),
            end_date=datetime.strptime(end_date, '%Y-%m-%d'),
            initial_capital=self.initial_capital,
            total_trades=total_trades,
            winning_trades=win_count,
            losing_trades=loss_count,
            win_rate=win_rate,
            total_pnl=total_pnl,
            total_pnl_percent=total_pnl_percent,
            avg_win_percent=avg_win_percent,
            avg_loss_percent=avg_loss_percent,
            largest_win=largest_win,
            largest_loss=largest_loss,
            max_drawdown=max_drawdown,
            sharpe_ratio=sharpe_ratio,
            profit_factor=profit_factor,
            final_capital=self.capital
        )

        return result

    def _display_results(self, result: BacktestResult):
        """Display backtest results."""
        print(f"Total Trades: {result.total_trades}")
        print(f"Winning Trades: {result.winning_trades} ({result.win_rate:.1f}%)")
        print(f"Losing Trades: {result.losing_trades}")
        print(f"\nP&L:")
        print(f"  Total: ${result.total_pnl:,.2f} ({result.total_pnl_percent:+.2f}%)")
        print(f"  Average Win: {result.avg_win_percent:+.2f}%")
        print(f"  Average Loss: {result.avg_loss_percent:+.2f}%")
        print(f"  Largest Win: ${result.largest_win:,.2f}")
        print(f"  Largest Loss: ${result.largest_loss:,.2f}")
        print(f"\nRisk Metrics:")
        print(f"  Max Drawdown: {result.max_drawdown:.2f}%")
        print(f"  Sharpe Ratio: {result.sharpe_ratio:.2f}")
        print(f"  Profit Factor: {result.profit_factor:.2f}")
        print(f"\nFinal Capital: ${result.final_capital:,.2f}")
        print(f"{'=' * 60}\n")


# Global backtest engine instance
backtest_engine = BacktestEngine()
