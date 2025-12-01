"""
Fair Value Gap (FVG) Pattern Detection.

A Fair Value Gap (also called imbalance) occurs when:
- Bullish FVG: The high of candle[i-2] < low of candle[i], leaving a gap with candle[i-1] in between
- Bearish FVG: The low of candle[i-2] > high of candle[i], leaving a gap with candle[i-1] in between

These gaps represent areas where price moved so quickly that it created an imbalance,
which the market often returns to fill.
"""
from typing import List, Dict
import pandas as pd
from datetime import datetime

from src.patterns.base import BasePattern
from src.data.models import Pattern
from src.config.parameters import parameter_manager


class FVGPattern(BasePattern):
    """Fair Value Gap pattern detector."""

    def __init__(self):
        """Initialize FVG detector."""
        super().__init__()

    def detect(
        self,
        df: pd.DataFrame,
        symbol: str,
        timeframe: str
    ) -> List[Pattern]:
        """
        Detect Fair Value Gaps in the given DataFrame.

        Args:
            df: DataFrame with OHLCV data (indexed by timestamp)
            symbol: Trading pair symbol
            timeframe: Timeframe string

        Returns:
            List of detected Pattern objects
        """
        if len(df) < 3:
            return []

        # Get dynamic parameters for this symbol/timeframe
        params = parameter_manager.get_parameters(symbol, timeframe)
        min_gap_percent = params.fvg.min_gap_percent
        volume_confirmation = params.fvg.volume_confirmation

        patterns = []

        # Calculate ATR for stop loss
        atr_series = self.calculate_atr(df)

        # Detect FVGs (start from index 2 since we need 3 candles)
        for i in range(2, len(df)):
            candle_0 = df.iloc[i - 2]  # First candle
            candle_1 = df.iloc[i - 1]  # Middle candle
            candle_2 = df.iloc[i]      # Third candle

            timestamp_0 = df.index[i - 2]
            timestamp_2 = df.index[i]

            # Check for Bullish FVG
            bullish_fvg = self._detect_bullish_fvg(
                candle_0, candle_1, candle_2,
                timestamp_2, symbol, timeframe, atr_series.iloc[i]
            )
            if bullish_fvg:
                patterns.append(bullish_fvg)

            # Check for Bearish FVG
            bearish_fvg = self._detect_bearish_fvg(
                candle_0, candle_1, candle_2,
                timestamp_2, symbol, timeframe, atr_series.iloc[i]
            )
            if bearish_fvg:
                patterns.append(bearish_fvg)

        return patterns

    def _detect_bullish_fvg(
        self,
        candle_0: pd.Series,
        candle_1: pd.Series,
        candle_2: pd.Series,
        timestamp: datetime,
        symbol: str,
        timeframe: str,
        atr: float
    ) -> Pattern:
        """
        Detect a bullish Fair Value Gap.

        Bullish FVG conditions:
        - candle_0['high'] < candle_2['low'] (gap exists)
        - Strong upward movement (candle_2 is bullish)
        - Optional: Volume confirmation on candle_2
        """
        gap_bottom = candle_0['high']
        gap_top = candle_2['low']

        # Check if gap exists
        if gap_bottom >= gap_top:
            return None

        # Calculate gap size as percentage
        gap_size = gap_top - gap_bottom
        gap_size_percent = (gap_size / gap_bottom) * 100

        # Get parameters for this symbol/timeframe
        params = parameter_manager.get_parameters(symbol, timeframe)

        # Check if gap meets minimum size requirement
        if gap_size_percent < params.fvg.min_gap_percent:
            return None

        # Check if candle_2 is bullish
        if candle_2['close'] <= candle_2['open']:
            return None

        # Volume confirmation (optional)
        if params.fvg.volume_confirmation:
            # Check if candle_2 has higher volume than candle_1
            if candle_2['volume'] <= candle_1['volume']:
                return None

        # Calculate trade levels
        # Entry: Middle of the gap (or bottom of gap for more conservative entry)
        entry_price = (gap_bottom + gap_top) / 2
        # Alternative conservative entry: gap_bottom

        # Stop loss: Below the gap
        stop_loss = self.calculate_stop_loss(
            entry_price=gap_bottom,
            direction='bullish',
            symbol=symbol,
            timeframe=timeframe,
            atr=atr
        )

        # Take profit based on R:R ratio
        take_profit = self.calculate_take_profit(
            entry_price=entry_price,
            stop_loss=stop_loss,
            direction='bullish',
            symbol=symbol,
            timeframe=timeframe
        )

        # Create Pattern object
        pattern = Pattern(
            symbol=symbol,
            timeframe=timeframe,
            pattern_type='fvg',
            direction='bullish',
            start_timestamp=timestamp,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            gap_top=gap_top,
            gap_bottom=gap_bottom,
            gap_size_percent=gap_size_percent,
            is_valid=True
        )

        return pattern

    def _detect_bearish_fvg(
        self,
        candle_0: pd.Series,
        candle_1: pd.Series,
        candle_2: pd.Series,
        timestamp: datetime,
        symbol: str,
        timeframe: str,
        atr: float
    ) -> Pattern:
        """
        Detect a bearish Fair Value Gap.

        Bearish FVG conditions:
        - candle_0['low'] > candle_2['high'] (gap exists)
        - Strong downward movement (candle_2 is bearish)
        - Optional: Volume confirmation on candle_2
        """
        gap_top = candle_0['low']
        gap_bottom = candle_2['high']

        # Check if gap exists
        if gap_top <= gap_bottom:
            return None

        # Calculate gap size as percentage
        gap_size = gap_top - gap_bottom
        gap_size_percent = (gap_size / gap_top) * 100

        # Get parameters for this symbol/timeframe
        params = parameter_manager.get_parameters(symbol, timeframe)

        # Check if gap meets minimum size requirement
        if gap_size_percent < params.fvg.min_gap_percent:
            return None

        # Check if candle_2 is bearish
        if candle_2['close'] >= candle_2['open']:
            return None

        # Volume confirmation (optional)
        if params.fvg.volume_confirmation:
            # Check if candle_2 has higher volume than candle_1
            if candle_2['volume'] <= candle_1['volume']:
                return None

        # Calculate trade levels
        # Entry: Middle of the gap (or top of gap for more conservative entry)
        entry_price = (gap_bottom + gap_top) / 2
        # Alternative conservative entry: gap_top

        # Stop loss: Above the gap
        stop_loss = self.calculate_stop_loss(
            entry_price=gap_top,
            direction='bearish',
            symbol=symbol,
            timeframe=timeframe,
            atr=atr
        )

        # Take profit based on R:R ratio
        take_profit = self.calculate_take_profit(
            entry_price=entry_price,
            stop_loss=stop_loss,
            direction='bearish',
            symbol=symbol,
            timeframe=timeframe
        )

        # Create Pattern object
        pattern = Pattern(
            symbol=symbol,
            timeframe=timeframe,
            pattern_type='fvg',
            direction='bearish',
            start_timestamp=timestamp,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            gap_top=gap_top,
            gap_bottom=gap_bottom,
            gap_size_percent=gap_size_percent,
            is_valid=True
        )

        return pattern

    def _validate_pattern_specific(
        self,
        pattern: Pattern,
        current_price: float
    ) -> bool:
        """
        Check if FVG has been filled.

        A bullish FVG is filled when price reaches the gap bottom.
        A bearish FVG is filled when price reaches the gap top.
        """
        if pattern.direction == 'bullish':
            # FVG is filled if price dropped below gap bottom
            if current_price <= pattern.gap_bottom:
                return False
        else:  # bearish
            # FVG is filled if price rose above gap top
            if current_price >= pattern.gap_top:
                return False

        return True

    def get_pattern_info(self, pattern: Pattern) -> Dict:
        """Get FVG-specific information."""
        info = super().get_pattern_info(pattern)

        info.update({
            'gap_top': pattern.gap_top,
            'gap_bottom': pattern.gap_bottom,
            'gap_size_percent': round(pattern.gap_size_percent, 2)
        })

        return info


# Global FVG detector instance
fvg_detector = FVGPattern()
