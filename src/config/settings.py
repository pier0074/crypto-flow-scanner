"""
Configuration management for CryptoFlowScanner.
Loads settings from environment variables with sensible defaults.
"""
import os
from typing import List
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Settings:
    """Application settings loaded from environment variables."""

    # Exchange settings
    EXCHANGE: str = os.getenv('EXCHANGE', 'binance')
    SYMBOLS: List[str] = os.getenv('SYMBOLS', 'BTC/USDT,ETH/USDT').split(',')
    TIMEFRAMES: List[str] = os.getenv('TIMEFRAMES', '1m,5m,15m,1h,4h,1d').split(',')

    # Email notification settings
    SMTP_HOST: str = os.getenv('SMTP_HOST', 'smtp.gmail.com')
    SMTP_PORT: int = int(os.getenv('SMTP_PORT', '587'))
    SMTP_USER: str = os.getenv('SMTP_USER', '')
    SMTP_PASSWORD: str = os.getenv('SMTP_PASSWORD', '')
    NOTIFICATION_EMAIL: str = os.getenv('NOTIFICATION_EMAIL', '')
    SEND_NOTIFICATIONS: bool = os.getenv('SEND_NOTIFICATIONS', 'false').lower() == 'true'

    # Trading parameters
    POSITION_SIZE_PERCENT: float = float(os.getenv('POSITION_SIZE_PERCENT', '2.0'))
    MAX_RISK_PERCENT: float = float(os.getenv('MAX_RISK_PERCENT', '1.0'))
    STOP_LOSS_ATR_MULTIPLIER: float = float(os.getenv('STOP_LOSS_ATR_MULTIPLIER', '1.5'))
    TAKE_PROFIT_RR_RATIO: float = float(os.getenv('TAKE_PROFIT_RR_RATIO', '2.0'))

    # FVG detection settings
    FVG_MIN_GAP_PERCENT: float = float(os.getenv('FVG_MIN_GAP_PERCENT', '0.1'))
    FVG_MAX_AGE_CANDLES: int = int(os.getenv('FVG_MAX_AGE_CANDLES', '50'))
    FVG_VOLUME_CONFIRMATION: bool = os.getenv('FVG_VOLUME_CONFIRMATION', 'true').lower() == 'true'

    # Confluence settings
    MIN_TIMEFRAME_CONFLUENCE: int = int(os.getenv('MIN_TIMEFRAME_CONFLUENCE', '3'))

    # Backtesting settings
    BACKTEST_START_DATE: str = os.getenv('BACKTEST_START_DATE', '2024-01-01')
    BACKTEST_END_DATE: str = os.getenv('BACKTEST_END_DATE', '2024-12-01')
    BACKTEST_INITIAL_CAPITAL: float = float(os.getenv('BACKTEST_INITIAL_CAPITAL', '10000'))

    # Data collection
    INITIAL_HISTORICAL_DAYS: int = int(os.getenv('INITIAL_HISTORICAL_DAYS', '90'))
    UPDATE_INTERVAL_SECONDS: int = int(os.getenv('UPDATE_INTERVAL_SECONDS', '60'))

    # Web dashboard
    WEB_HOST: str = os.getenv('WEB_HOST', '0.0.0.0')
    WEB_PORT: int = int(os.getenv('WEB_PORT', '5000'))
    WEB_DEBUG: bool = os.getenv('WEB_DEBUG', 'true').lower() == 'true'

    # Logging
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE: str = os.getenv('LOG_FILE', 'logs/crypto_flow_scanner.log')

    # Database
    DATABASE_URL: str = os.getenv('DATABASE_URL', 'sqlite:///data/crypto_flow_scanner.db')

    @classmethod
    def validate(cls) -> bool:
        """Validate that required settings are configured."""
        errors = []

        if cls.SEND_NOTIFICATIONS:
            if not cls.SMTP_USER:
                errors.append("SMTP_USER is required when notifications are enabled")
            if not cls.SMTP_PASSWORD:
                errors.append("SMTP_PASSWORD is required when notifications are enabled")
            if not cls.NOTIFICATION_EMAIL:
                errors.append("NOTIFICATION_EMAIL is required when notifications are enabled")

        if not cls.SYMBOLS:
            errors.append("At least one symbol must be configured")

        if not cls.TIMEFRAMES:
            errors.append("At least one timeframe must be configured")

        if errors:
            for error in errors:
                print(f"Configuration Error: {error}")
            return False

        return True

    @classmethod
    def get_timeframe_minutes(cls, timeframe: str) -> int:
        """Convert timeframe string to minutes."""
        timeframe_map = {
            '1m': 1,
            '5m': 5,
            '15m': 15,
            '30m': 30,
            '1h': 60,
            '4h': 240,
            '1d': 1440,
            '1w': 10080
        }
        return timeframe_map.get(timeframe.lower(), 1)

    @classmethod
    def display(cls):
        """Display current configuration (hiding sensitive data)."""
        print("\n=== CryptoFlowScanner Configuration ===")
        print(f"Exchange: {cls.EXCHANGE}")
        print(f"Symbols: {', '.join(cls.SYMBOLS[:5])}{'...' if len(cls.SYMBOLS) > 5 else ''} ({len(cls.SYMBOLS)} total)")
        print(f"Timeframes: {', '.join(cls.TIMEFRAMES)}")
        print(f"Notifications: {'Enabled' if cls.SEND_NOTIFICATIONS else 'Disabled'}")
        print(f"Position Size: {cls.POSITION_SIZE_PERCENT}%")
        print(f"Max Risk: {cls.MAX_RISK_PERCENT}%")
        print(f"Min Confluence: {cls.MIN_TIMEFRAME_CONFLUENCE} timeframes")
        print("=" * 40 + "\n")


# Create settings instance
settings = Settings()
