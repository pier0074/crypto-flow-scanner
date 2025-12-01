"""
Base pattern detection class.
All pattern detectors inherit from this base class.
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Optional
import pandas as pd
from datetime import datetime

from src.data.models import Pattern
from src.config.parameters import parameter_manager


class BasePattern(ABC):
    """Abstract base class for pattern detection."""

    def __init__(self):
        """Initialize pattern detector."""
        self.pattern_type = self.__class__.__name__.lower().replace('pattern', '')

    @abstractmethod
    def detect(
        self,
        df: pd.DataFrame,
        symbol: str,
        timeframe: str
    ) -> List[Pattern]:
        """
        Detect patterns in the given DataFrame.

        Args:
            df: DataFrame with OHLCV data (indexed by timestamp)
            symbol: Trading pair symbol
            timeframe: Timeframe string

        Returns:
            List of detected Pattern objects
        """
        pass

    def calculate_stop_loss(
        self,
        entry_price: float,
        direction: str,
        symbol: str = None,
        timeframe: str = None,
        atr: float = None,
        pattern_data: Dict = None
    ) -> float:
        """
        Calculate stop loss price.

        Args:
            entry_price: Entry price
            direction: 'bullish' or 'bearish'
            symbol: Trading pair symbol (for dynamic parameters)
            timeframe: Timeframe string (for dynamic parameters)
            atr: Average True Range (if available)
            pattern_data: Pattern-specific data for SL calculation

        Returns:
            Stop loss price
        """
        # Get dynamic parameters
        params = parameter_manager.get_parameters(symbol, timeframe)

        if atr:
            multiplier = params.risk.stop_loss_atr_multiplier
            if direction == 'bullish':
                return entry_price - (atr * multiplier)
            else:
                return entry_price + (atr * multiplier)

        # Default: 2% stop loss
        if direction == 'bullish':
            return entry_price * 0.98
        else:
            return entry_price * 1.02

    def calculate_take_profit(
        self,
        entry_price: float,
        stop_loss: float,
        direction: str,
        symbol: str = None,
        timeframe: str = None,
        risk_reward_ratio: float = None
    ) -> float:
        """
        Calculate take profit price based on risk-reward ratio.

        Args:
            entry_price: Entry price
            stop_loss: Stop loss price
            direction: 'bullish' or 'bearish'
            symbol: Trading pair symbol (for dynamic parameters)
            timeframe: Timeframe string (for dynamic parameters)
            risk_reward_ratio: R:R ratio (override, default from parameters)

        Returns:
            Take profit price
        """
        # Get dynamic parameters
        params = parameter_manager.get_parameters(symbol, timeframe)
        rr_ratio = risk_reward_ratio or params.risk.take_profit_rr_ratio
        risk = abs(entry_price - stop_loss)

        if direction == 'bullish':
            return entry_price + (risk * rr_ratio)
        else:
            return entry_price - (risk * rr_ratio)

    def calculate_atr(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """
        Calculate Average True Range.

        Args:
            df: DataFrame with OHLCV data
            period: ATR period

        Returns:
            Series with ATR values
        """
        high = df['high']
        low = df['low']
        close = df['close'].shift(1)

        tr1 = high - low
        tr2 = abs(high - close)
        tr3 = abs(low - close)

        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()

        return atr

    def is_pattern_valid(
        self,
        pattern: Pattern,
        current_price: float,
        current_timestamp: datetime
    ) -> bool:
        """
        Check if a pattern is still valid (not filled/invalidated).

        Args:
            pattern: Pattern object
            current_price: Current market price
            current_timestamp: Current timestamp

        Returns:
            True if pattern is still valid
        """
        # Check if pattern has been marked as invalid
        if not pattern.is_valid:
            return False

        # Get dynamic parameters for this pattern
        params = parameter_manager.get_parameters(pattern.symbol, pattern.timeframe)

        # Check age (for FVG patterns)
        if pattern.pattern_type == 'fvg':
            age_candles = (current_timestamp - pattern.start_timestamp).total_seconds() / 60
            max_age = params.fvg.max_age_candles

            if age_candles > max_age:
                return False

        # Pattern-specific validation (to be overridden)
        return self._validate_pattern_specific(pattern, current_price)

    def _validate_pattern_specific(
        self,
        pattern: Pattern,
        current_price: float
    ) -> bool:
        """
        Pattern-specific validation logic.
        Override this in subclasses.

        Args:
            pattern: Pattern object
            current_price: Current market price

        Returns:
            True if pattern is still valid
        """
        return True

    def get_pattern_info(self, pattern: Pattern) -> Dict:
        """
        Get human-readable pattern information.

        Args:
            pattern: Pattern object

        Returns:
            Dictionary with pattern information
        """
        return {
            'type': pattern.pattern_type,
            'direction': pattern.direction,
            'symbol': pattern.symbol,
            'timeframe': pattern.timeframe,
            'entry': pattern.entry_price,
            'stop_loss': pattern.stop_loss,
            'take_profit': pattern.take_profit,
            'risk_reward': round(
                abs(pattern.take_profit - pattern.entry_price) / abs(pattern.entry_price - pattern.stop_loss),
                2
            ),
            'timestamp': pattern.start_timestamp,
            'valid': pattern.is_valid
        }
