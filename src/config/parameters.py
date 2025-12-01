"""
Dynamic parameter configuration system.
Allows per-symbol and per-timeframe parameter overrides.
"""
import json
import os
from typing import Dict, Optional, Any
from dataclasses import dataclass, asdict

from src.config.settings import settings


@dataclass
class RiskParameters:
    """Risk management parameters."""
    max_risk_percent: float = 1.0
    stop_loss_atr_multiplier: float = 1.5
    take_profit_rr_ratio: float = 2.0
    position_size_percent: float = 2.0


@dataclass
class FVGParameters:
    """FVG detection parameters."""
    min_gap_percent: float = 0.1
    max_age_candles: int = 50
    volume_confirmation: bool = True


@dataclass
class TradingParameters:
    """Combined trading parameters."""
    risk: RiskParameters
    fvg: FVGParameters

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            'risk': asdict(self.risk),
            'fvg': asdict(self.fvg)
        }


class ParameterManager:
    """Manages dynamic trading parameters with symbol/timeframe overrides."""

    def __init__(self, config_file: str = 'data/parameters.json'):
        """
        Initialize parameter manager.

        Args:
            config_file: Path to JSON config file for parameter overrides
        """
        self.config_file = config_file
        self.overrides = {}  # symbol -> timeframe -> parameters
        self.load_overrides()

    def load_overrides(self):
        """Load parameter overrides from config file."""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    data = json.load(f)
                    self.overrides = data.get('overrides', {})
                print(f"Loaded parameter overrides from {self.config_file}")
            except Exception as e:
                print(f"Error loading parameter overrides: {e}")
                self.overrides = {}
        else:
            self.overrides = {}

    def save_overrides(self):
        """Save parameter overrides to config file."""
        try:
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            with open(self.config_file, 'w') as f:
                json.dump({'overrides': self.overrides}, f, indent=2)
            print(f"Saved parameter overrides to {self.config_file}")
        except Exception as e:
            print(f"Error saving parameter overrides: {e}")

    def get_default_parameters(self) -> TradingParameters:
        """Get default parameters from settings."""
        return TradingParameters(
            risk=RiskParameters(
                max_risk_percent=settings.MAX_RISK_PERCENT,
                stop_loss_atr_multiplier=settings.STOP_LOSS_ATR_MULTIPLIER,
                take_profit_rr_ratio=settings.TAKE_PROFIT_RR_RATIO,
                position_size_percent=settings.POSITION_SIZE_PERCENT
            ),
            fvg=FVGParameters(
                min_gap_percent=settings.FVG_MIN_GAP_PERCENT,
                max_age_candles=settings.FVG_MAX_AGE_CANDLES,
                volume_confirmation=settings.FVG_VOLUME_CONFIRMATION
            )
        )

    def get_parameters(
        self,
        symbol: Optional[str] = None,
        timeframe: Optional[str] = None
    ) -> TradingParameters:
        """
        Get parameters with optional symbol/timeframe overrides.

        Priority order:
        1. Symbol + Timeframe specific
        2. Symbol specific (all timeframes)
        3. Timeframe specific (all symbols)
        4. Default from settings

        Args:
            symbol: Trading pair symbol (optional)
            timeframe: Timeframe string (optional)

        Returns:
            TradingParameters with appropriate overrides applied
        """
        # Start with defaults
        params = self.get_default_parameters()

        # Apply global timeframe overrides
        if timeframe and 'timeframes' in self.overrides:
            if timeframe in self.overrides['timeframes']:
                params = self._merge_parameters(params, self.overrides['timeframes'][timeframe])

        # Apply symbol-level overrides
        if symbol and 'symbols' in self.overrides:
            if symbol in self.overrides['symbols']:
                symbol_config = self.overrides['symbols'][symbol]

                # Apply general symbol override
                if 'default' in symbol_config:
                    params = self._merge_parameters(params, symbol_config['default'])

                # Apply symbol+timeframe override
                if timeframe and 'timeframes' in symbol_config:
                    if timeframe in symbol_config['timeframes']:
                        params = self._merge_parameters(params, symbol_config['timeframes'][timeframe])

        return params

    def _merge_parameters(
        self,
        base: TradingParameters,
        overrides: Dict[str, Any]
    ) -> TradingParameters:
        """Merge override parameters with base parameters."""
        # Deep copy to avoid modifying original
        risk_dict = asdict(base.risk)
        fvg_dict = asdict(base.fvg)

        # Apply overrides
        if 'risk' in overrides:
            risk_dict.update(overrides['risk'])

        if 'fvg' in overrides:
            fvg_dict.update(overrides['fvg'])

        return TradingParameters(
            risk=RiskParameters(**risk_dict),
            fvg=FVGParameters(**fvg_dict)
        )

    def set_symbol_parameters(
        self,
        symbol: str,
        parameters: Dict[str, Any],
        timeframe: Optional[str] = None
    ):
        """
        Set parameter overrides for a symbol.

        Args:
            symbol: Trading pair symbol
            parameters: Dictionary of parameters to override
            timeframe: Optional specific timeframe
        """
        if 'symbols' not in self.overrides:
            self.overrides['symbols'] = {}

        if symbol not in self.overrides['symbols']:
            self.overrides['symbols'][symbol] = {}

        if timeframe:
            if 'timeframes' not in self.overrides['symbols'][symbol]:
                self.overrides['symbols'][symbol]['timeframes'] = {}
            self.overrides['symbols'][symbol]['timeframes'][timeframe] = parameters
        else:
            self.overrides['symbols'][symbol]['default'] = parameters

        self.save_overrides()

    def set_timeframe_parameters(
        self,
        timeframe: str,
        parameters: Dict[str, Any]
    ):
        """
        Set parameter overrides for a timeframe (applies to all symbols).

        Args:
            timeframe: Timeframe string
            parameters: Dictionary of parameters to override
        """
        if 'timeframes' not in self.overrides:
            self.overrides['timeframes'] = {}

        self.overrides['timeframes'][timeframe] = parameters
        self.save_overrides()

    def remove_symbol_parameters(
        self,
        symbol: str,
        timeframe: Optional[str] = None
    ):
        """Remove parameter overrides for a symbol."""
        if 'symbols' not in self.overrides or symbol not in self.overrides['symbols']:
            return

        if timeframe:
            if 'timeframes' in self.overrides['symbols'][symbol]:
                self.overrides['symbols'][symbol]['timeframes'].pop(timeframe, None)
        else:
            self.overrides['symbols'].pop(symbol, None)

        self.save_overrides()

    def get_all_overrides(self) -> Dict:
        """Get all parameter overrides."""
        return self.overrides

    def display_parameters(
        self,
        symbol: Optional[str] = None,
        timeframe: Optional[str] = None
    ):
        """Display parameters with current overrides."""
        params = self.get_parameters(symbol, timeframe)

        context = []
        if symbol:
            context.append(f"Symbol: {symbol}")
        if timeframe:
            context.append(f"Timeframe: {timeframe}")

        print(f"\n{'=' * 60}")
        print(f"Trading Parameters {f'({', '.join(context)})' if context else '(Default)'}")
        print(f"{'=' * 60}")

        print("\nRisk Management:")
        print(f"  Max Risk: {params.risk.max_risk_percent}%")
        print(f"  Position Size: {params.risk.position_size_percent}%")
        print(f"  Stop Loss Multiplier: {params.risk.stop_loss_atr_multiplier}x ATR")
        print(f"  Take Profit R:R: {params.risk.take_profit_rr_ratio}")

        print("\nFVG Detection:")
        print(f"  Min Gap Size: {params.fvg.min_gap_percent}%")
        print(f"  Max Age: {params.fvg.max_age_candles} candles")
        print(f"  Volume Confirmation: {params.fvg.volume_confirmation}")

        print(f"{'=' * 60}\n")


# Global parameter manager instance
parameter_manager = ParameterManager()


# Example usage and configuration
def setup_example_overrides():
    """Example of how to set up parameter overrides."""
    # BTC: More conservative on lower timeframes
    parameter_manager.set_symbol_parameters(
        'BTC/USDT',
        {
            'risk': {'max_risk_percent': 0.5},
            'fvg': {'min_gap_percent': 0.15}
        },
        timeframe='1m'
    )

    # ETH: More aggressive take profit
    parameter_manager.set_symbol_parameters(
        'ETH/USDT',
        {
            'risk': {'take_profit_rr_ratio': 3.0}
        }
    )

    # All 1m timeframes: Require larger gaps
    parameter_manager.set_timeframe_parameters(
        '1m',
        {
            'fvg': {
                'min_gap_percent': 0.2,
                'max_age_candles': 20
            }
        }
    )
