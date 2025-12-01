"""
Pattern detection orchestrator.
Manages pattern detection across multiple symbols and timeframes.
"""
from typing import List, Dict, Optional
import pandas as pd
from datetime import datetime

from src.patterns.fvg import fvg_detector
from src.data.models import Pattern
from src.data.storage import db_manager
from src.config.settings import settings


class PatternDetector:
    """Orchestrates pattern detection across symbols and timeframes."""

    def __init__(self):
        """Initialize pattern detector."""
        self.detectors = {
            'fvg': fvg_detector,
            # Add more pattern detectors here in the future
            # 'liquidity_sweep': liquidity_sweep_detector,
            # 'order_block': order_block_detector,
        }

    def detect_patterns(
        self,
        symbol: str,
        timeframe: str,
        pattern_types: Optional[List[str]] = None,
        save_to_db: bool = True
    ) -> List[Pattern]:
        """
        Detect patterns for a given symbol and timeframe.

        Args:
            symbol: Trading pair symbol
            timeframe: Timeframe string
            pattern_types: List of pattern types to detect (default: all)
            save_to_db: Whether to save detected patterns to database

        Returns:
            List of detected Pattern objects
        """
        # Get candles from database
        candles = db_manager.get_candles(symbol, timeframe)

        if not candles or len(candles) < 3:
            print(f"Not enough candles for {symbol} {timeframe}")
            return []

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

        # Determine which patterns to detect
        if pattern_types is None:
            pattern_types = list(self.detectors.keys())

        all_patterns = []

        # Run each detector
        for pattern_type in pattern_types:
            detector = self.detectors.get(pattern_type)
            if not detector:
                print(f"Unknown pattern type: {pattern_type}")
                continue

            try:
                patterns = detector.detect(df, symbol, timeframe)
                all_patterns.extend(patterns)

                print(f"Detected {len(patterns)} {pattern_type} patterns for {symbol} {timeframe}")

            except Exception as e:
                print(f"Error detecting {pattern_type} for {symbol} {timeframe}: {e}")

        # Save to database
        if save_to_db and all_patterns:
            for pattern in all_patterns:
                db_manager.save_pattern(pattern)

        return all_patterns

    def scan_all_symbols(
        self,
        symbols: Optional[List[str]] = None,
        timeframes: Optional[List[str]] = None,
        pattern_types: Optional[List[str]] = None
    ) -> Dict[str, List[Pattern]]:
        """
        Scan all symbols and timeframes for patterns.

        Args:
            symbols: List of symbols (default from settings)
            timeframes: List of timeframes (default from settings)
            pattern_types: List of pattern types to detect (default: all)

        Returns:
            Dictionary mapping symbol to list of patterns
        """
        symbols = symbols or settings.SYMBOLS
        timeframes = timeframes or settings.TIMEFRAMES

        print(f"\n=== Starting pattern scan ===")
        print(f"Symbols: {len(symbols)}")
        print(f"Timeframes: {len(timeframes)}")
        print(f"Pattern types: {pattern_types or 'all'}\n")

        results = {}

        for symbol in symbols:
            symbol_patterns = []

            for timeframe in timeframes:
                try:
                    patterns = self.detect_patterns(
                        symbol=symbol,
                        timeframe=timeframe,
                        pattern_types=pattern_types,
                        save_to_db=True
                    )
                    symbol_patterns.extend(patterns)

                except Exception as e:
                    print(f"Error scanning {symbol} {timeframe}: {e}")

            results[symbol] = symbol_patterns

            if symbol_patterns:
                print(f"{symbol}: {len(symbol_patterns)} patterns found")

        total_patterns = sum(len(patterns) for patterns in results.values())
        print(f"\n=== Scan complete: {total_patterns} total patterns ===\n")

        return results

    def update_pattern_validity(
        self,
        symbol: str,
        current_price: float,
        current_timestamp: datetime
    ):
        """
        Update the validity of existing patterns based on current price.

        Args:
            symbol: Trading pair symbol
            current_price: Current market price
            current_timestamp: Current timestamp
        """
        # Get all valid patterns for this symbol
        valid_patterns = db_manager.get_valid_patterns(symbol=symbol)

        for pattern in valid_patterns:
            detector = self.detectors.get(pattern.pattern_type)
            if not detector:
                continue

            # Check if pattern is still valid
            is_valid = detector.is_pattern_valid(
                pattern,
                current_price,
                current_timestamp
            )

            if not is_valid:
                # Invalidate the pattern
                db_manager.invalidate_pattern(pattern.id, current_timestamp)
                print(f"Invalidated {pattern.pattern_type} pattern for {symbol} @ {pattern.start_timestamp}")

    def get_pattern_summary(
        self,
        symbol: Optional[str] = None,
        timeframe: Optional[str] = None,
        pattern_type: Optional[str] = None
    ) -> Dict:
        """
        Get a summary of valid patterns.

        Args:
            symbol: Filter by symbol (optional)
            timeframe: Filter by timeframe (optional)
            pattern_type: Filter by pattern type (optional)

        Returns:
            Dictionary with pattern summary
        """
        patterns = db_manager.get_valid_patterns(
            symbol=symbol,
            pattern_type=pattern_type,
            timeframe=timeframe
        )

        # Group by direction
        bullish = [p for p in patterns if p.direction == 'bullish']
        bearish = [p for p in patterns if p.direction == 'bearish']

        # Group by symbol if not filtering by symbol
        by_symbol = {}
        for pattern in patterns:
            if pattern.symbol not in by_symbol:
                by_symbol[pattern.symbol] = []
            by_symbol[pattern.symbol].append(pattern)

        summary = {
            'total': len(patterns),
            'bullish': len(bullish),
            'bearish': len(bearish),
            'by_symbol': {
                sym: len(pats) for sym, pats in by_symbol.items()
            },
            'patterns': patterns
        }

        return summary


# Global detector instance
pattern_detector = PatternDetector()
