"""
Multi-timeframe confluence analysis.
Identifies trading opportunities when multiple timeframes align.
"""
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from collections import defaultdict

from src.data.models import Pattern, Signal
from src.data.storage import db_manager
from src.config.settings import settings


class ConfluenceAnalyzer:
    """Analyzes pattern confluence across multiple timeframes."""

    def __init__(self):
        """Initialize confluence analyzer."""
        self.min_confluence = settings.MIN_TIMEFRAME_CONFLUENCE

    def analyze_confluence(
        self,
        symbol: str,
        timeframes: Optional[List[str]] = None,
        pattern_type: str = 'fvg',
        lookback_hours: int = 24
    ) -> List[Signal]:
        """
        Analyze confluence for a symbol across multiple timeframes.

        Args:
            symbol: Trading pair symbol
            timeframes: List of timeframes to analyze (default from settings)
            pattern_type: Pattern type to analyze
            lookback_hours: How far back to look for patterns

        Returns:
            List of Signal objects with confluence
        """
        timeframes = timeframes or settings.TIMEFRAMES

        # Get valid patterns for each timeframe
        patterns_by_timeframe = {}
        cutoff_time = datetime.utcnow() - timedelta(hours=lookback_hours)

        for timeframe in timeframes:
            patterns = db_manager.get_valid_patterns(
                symbol=symbol,
                pattern_type=pattern_type,
                timeframe=timeframe
            )

            # Filter by lookback period
            recent_patterns = [
                p for p in patterns
                if p.start_timestamp >= cutoff_time
            ]

            patterns_by_timeframe[timeframe] = recent_patterns

        # Find confluence (same direction across multiple timeframes)
        signals = []

        # Check for bullish confluence
        bullish_signal = self._find_confluence_signal(
            symbol=symbol,
            patterns_by_timeframe=patterns_by_timeframe,
            direction='bullish'
        )
        if bullish_signal:
            signals.append(bullish_signal)

        # Check for bearish confluence
        bearish_signal = self._find_confluence_signal(
            symbol=symbol,
            patterns_by_timeframe=patterns_by_timeframe,
            direction='bearish'
        )
        if bearish_signal:
            signals.append(bearish_signal)

        return signals

    def _find_confluence_signal(
        self,
        symbol: str,
        patterns_by_timeframe: Dict[str, List[Pattern]],
        direction: str
    ) -> Optional[Signal]:
        """
        Find confluence signal in a specific direction.

        Args:
            symbol: Trading pair symbol
            patterns_by_timeframe: Dictionary mapping timeframe to patterns
            direction: 'bullish' or 'bearish'

        Returns:
            Signal object if confluence found, None otherwise
        """
        # Find timeframes with patterns in the specified direction
        confluent_timeframes = []
        confluent_patterns = []

        for timeframe, patterns in patterns_by_timeframe.items():
            matching_patterns = [
                p for p in patterns
                if p.direction == direction
            ]

            if matching_patterns:
                confluent_timeframes.append(timeframe)
                # Use the most recent pattern from this timeframe
                confluent_patterns.append(
                    max(matching_patterns, key=lambda p: p.start_timestamp)
                )

        # Check if we have enough confluence
        confluence_count = len(confluent_timeframes)

        if confluence_count < self.min_confluence:
            return None

        # Determine primary timeframe (highest timeframe with the pattern)
        primary_timeframe = self._get_highest_timeframe(confluent_timeframes)

        # Calculate trade levels (using primary timeframe pattern as base)
        primary_pattern = next(
            p for p in confluent_patterns
            if p.timeframe == primary_timeframe
        )

        # Average entry across all patterns for more robust entry
        avg_entry = sum(p.entry_price for p in confluent_patterns) / len(confluent_patterns)

        # Use primary pattern for SL/TP but adjusted for averaged entry
        risk = abs(primary_pattern.entry_price - primary_pattern.stop_loss)
        reward = abs(primary_pattern.take_profit - primary_pattern.entry_price)

        if direction == 'bullish':
            stop_loss = avg_entry - risk
            take_profit = avg_entry + reward
        else:
            stop_loss = avg_entry + risk
            take_profit = avg_entry - reward

        # Calculate risk-reward ratio
        risk_reward_ratio = abs(take_profit - avg_entry) / abs(avg_entry - stop_loss)

        # Create signal
        signal = Signal(
            symbol=symbol,
            direction='long' if direction == 'bullish' else 'short',
            pattern_ids=','.join(str(p.id) for p in confluent_patterns),
            primary_timeframe=primary_timeframe,
            confluence_count=confluence_count,
            entry_price=avg_entry,
            stop_loss=stop_loss,
            take_profit=take_profit,
            risk_reward_ratio=risk_reward_ratio,
            position_size_percent=settings.POSITION_SIZE_PERCENT,
            risk_amount_percent=settings.MAX_RISK_PERCENT,
            status='active',
            notified=False
        )

        # Update confluence info in patterns
        confluence_timeframes_str = ','.join(confluent_timeframes)
        for pattern in confluent_patterns:
            pattern.confluence_count = confluence_count
            pattern.confluence_timeframes = confluence_timeframes_str

        return signal

    def _get_highest_timeframe(self, timeframes: List[str]) -> str:
        """
        Get the highest timeframe from a list.

        Args:
            timeframes: List of timeframe strings

        Returns:
            Highest timeframe string
        """
        timeframe_order = ['1m', '5m', '15m', '30m', '1h', '4h', '1d', '1w']

        for tf in reversed(timeframe_order):
            if tf in timeframes:
                return tf

        return timeframes[0]

    def scan_all_symbols_for_confluence(
        self,
        symbols: Optional[List[str]] = None,
        save_to_db: bool = True
    ) -> Dict[str, List[Signal]]:
        """
        Scan all symbols for confluence and generate signals.

        Args:
            symbols: List of symbols (default from settings)
            save_to_db: Whether to save signals to database

        Returns:
            Dictionary mapping symbol to list of signals
        """
        symbols = symbols or settings.SYMBOLS

        print(f"\n=== Scanning for confluence ===")
        print(f"Symbols: {len(symbols)}")
        print(f"Min confluence: {self.min_confluence} timeframes\n")

        results = {}

        for symbol in symbols:
            try:
                signals = self.analyze_confluence(symbol)

                if signals and save_to_db:
                    for signal in signals:
                        # Check if similar signal already exists
                        existing_signals = db_manager.get_active_signals(symbol)

                        is_duplicate = any(
                            s.direction == signal.direction and
                            abs(s.entry_price - signal.entry_price) / signal.entry_price < 0.01
                            for s in existing_signals
                        )

                        if not is_duplicate:
                            db_manager.save_signal(signal)
                            print(f"✓ {symbol}: {signal.direction.upper()} signal (confluence: {signal.confluence_count})")

                results[symbol] = signals

            except Exception as e:
                print(f"Error analyzing {symbol}: {e}")

        total_signals = sum(len(sigs) for sigs in results.values())
        print(f"\n=== Confluence scan complete: {total_signals} signals ===\n")

        return results

    def get_confluence_summary(self) -> Dict:
        """
        Get a summary of all confluence signals.

        Returns:
            Dictionary with signal summary
        """
        active_signals = db_manager.get_active_signals()

        # Group by direction
        long_signals = [s for s in active_signals if s.direction == 'long']
        short_signals = [s for s in active_signals if s.direction == 'short']

        # Group by confluence count
        by_confluence = defaultdict(list)
        for signal in active_signals:
            by_confluence[signal.confluence_count].append(signal)

        # Group by symbol
        by_symbol = defaultdict(list)
        for signal in active_signals:
            by_symbol[signal.symbol].append(signal)

        summary = {
            'total_signals': len(active_signals),
            'long_signals': len(long_signals),
            'short_signals': len(short_signals),
            'by_confluence': dict(by_confluence),
            'by_symbol': dict(by_symbol),
            'high_confluence': [
                s for s in active_signals
                if s.confluence_count >= self.min_confluence + 1
            ]
        }

        return summary

    def display_signals(self, signals: List[Signal]):
        """
        Display signals in a readable format.

        Args:
            signals: List of Signal objects
        """
        if not signals:
            print("No signals found")
            return

        print("\n" + "=" * 80)
        print(f"{'Symbol':<12} {'Direction':<8} {'Entry':<12} {'SL':<12} {'TP':<12} {'R:R':<6} {'Conf':<6}")
        print("=" * 80)

        for signal in signals:
            print(
                f"{signal.symbol:<12} "
                f"{signal.direction.upper():<8} "
                f"{signal.entry_price:<12.8f} "
                f"{signal.stop_loss:<12.8f} "
                f"{signal.take_profit:<12.8f} "
                f"{signal.risk_reward_ratio:<6.2f} "
                f"{signal.confluence_count:<6}"
            )

        print("=" * 80 + "\n")


# Global confluence analyzer instance
confluence_analyzer = ConfluenceAnalyzer()
