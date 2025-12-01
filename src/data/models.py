"""
Database models for CryptoFlowScanner.
Uses SQLAlchemy ORM for database operations.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Index, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()


class Candle(Base):
    """OHLCV candle data for a specific symbol and timeframe."""

    __tablename__ = 'candles'

    id = Column(Integer, primary_key=True)
    symbol = Column(String(20), nullable=False, index=True)
    timeframe = Column(String(5), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)

    # OHLCV data
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Float, nullable=False)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)

    # Composite index for efficient queries
    __table_args__ = (
        Index('idx_symbol_timeframe_timestamp', 'symbol', 'timeframe', 'timestamp'),
    )

    def __repr__(self):
        return f"<Candle {self.symbol} {self.timeframe} {self.timestamp} O:{self.open} H:{self.high} L:{self.low} C:{self.close}>"


class Pattern(Base):
    """Detected trading patterns (FVG, liquidity sweeps, etc.)."""

    __tablename__ = 'patterns'

    id = Column(Integer, primary_key=True)
    symbol = Column(String(20), nullable=False, index=True)
    timeframe = Column(String(5), nullable=False, index=True)
    pattern_type = Column(String(20), nullable=False, index=True)  # 'fvg', 'liquidity_sweep', etc.
    direction = Column(String(10), nullable=False)  # 'bullish' or 'bearish'

    # Pattern specific data
    start_timestamp = Column(DateTime, nullable=False, index=True)
    end_timestamp = Column(DateTime, nullable=True)

    # Price levels
    entry_price = Column(Float, nullable=False)
    stop_loss = Column(Float, nullable=False)
    take_profit = Column(Float, nullable=False)

    # FVG specific fields
    gap_top = Column(Float, nullable=True)  # Top of the fair value gap
    gap_bottom = Column(Float, nullable=True)  # Bottom of the fair value gap
    gap_size_percent = Column(Float, nullable=True)  # Gap size as percentage

    # Pattern validity
    is_valid = Column(Boolean, default=True)  # Pattern still unfilled/valid
    filled_timestamp = Column(DateTime, nullable=True)  # When pattern was filled/invalidated

    # Confluence
    confluence_count = Column(Integer, default=1)  # Number of timeframes with same signal
    confluence_timeframes = Column(String(100), nullable=True)  # e.g., "5m,15m,1h"

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Composite index
    __table_args__ = (
        Index('idx_symbol_timeframe_pattern_timestamp', 'symbol', 'timeframe', 'pattern_type', 'start_timestamp'),
        Index('idx_valid_patterns', 'is_valid', 'pattern_type', 'symbol'),
    )

    def __repr__(self):
        return f"<Pattern {self.pattern_type} {self.direction} {self.symbol} {self.timeframe} @ {self.start_timestamp}>"


class Signal(Base):
    """Trading signals generated from patterns with confluence."""

    __tablename__ = 'signals'

    id = Column(Integer, primary_key=True)
    symbol = Column(String(20), nullable=False, index=True)
    direction = Column(String(10), nullable=False)  # 'long' or 'short'

    # Pattern references
    pattern_ids = Column(String(200), nullable=False)  # Comma-separated pattern IDs
    primary_timeframe = Column(String(5), nullable=False)
    confluence_count = Column(Integer, nullable=False)

    # Trade setup
    entry_price = Column(Float, nullable=False)
    stop_loss = Column(Float, nullable=False)
    take_profit = Column(Float, nullable=False)
    risk_reward_ratio = Column(Float, nullable=False)

    # Position sizing
    position_size_percent = Column(Float, nullable=False)
    risk_amount_percent = Column(Float, nullable=False)

    # Signal status
    status = Column(String(20), default='active')  # 'active', 'triggered', 'closed', 'expired'
    notified = Column(Boolean, default=False)
    notification_sent_at = Column(DateTime, nullable=True)

    # Execution tracking (for future automated trading)
    triggered_at = Column(DateTime, nullable=True)
    trigger_price = Column(Float, nullable=True)
    closed_at = Column(DateTime, nullable=True)
    close_price = Column(Float, nullable=True)
    pnl_percent = Column(Float, nullable=True)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Indexes
    __table_args__ = (
        Index('idx_active_signals', 'status', 'symbol', 'created_at'),
        Index('idx_unnotified_signals', 'notified', 'status'),
    )

    def __repr__(self):
        return f"<Signal {self.symbol} {self.direction} {self.status} confluence:{self.confluence_count}>"


class BacktestResult(Base):
    """Results from backtesting strategies."""

    __tablename__ = 'backtest_results'

    id = Column(Integer, primary_key=True)

    # Backtest configuration
    strategy_name = Column(String(50), nullable=False)
    symbol = Column(String(20), nullable=False)
    timeframe = Column(String(5), nullable=False)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    initial_capital = Column(Float, nullable=False)

    # Performance metrics
    total_trades = Column(Integer, nullable=False)
    winning_trades = Column(Integer, nullable=False)
    losing_trades = Column(Integer, nullable=False)
    win_rate = Column(Float, nullable=False)

    # P&L metrics
    total_pnl = Column(Float, nullable=False)
    total_pnl_percent = Column(Float, nullable=False)
    avg_win_percent = Column(Float, nullable=False)
    avg_loss_percent = Column(Float, nullable=False)
    largest_win = Column(Float, nullable=False)
    largest_loss = Column(Float, nullable=False)

    # Risk metrics
    max_drawdown = Column(Float, nullable=False)
    sharpe_ratio = Column(Float, nullable=True)
    profit_factor = Column(Float, nullable=True)

    # Final capital
    final_capital = Column(Float, nullable=False)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<BacktestResult {self.strategy_name} {self.symbol} {self.timeframe} WR:{self.win_rate:.1%} PnL:{self.total_pnl_percent:.1%}>"


class SystemLog(Base):
    """System logs for monitoring and debugging."""

    __tablename__ = 'system_logs'

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    level = Column(String(10), nullable=False)  # 'INFO', 'WARNING', 'ERROR', 'DEBUG'
    module = Column(String(50), nullable=False)
    message = Column(String(500), nullable=False)
    details = Column(String(2000), nullable=True)

    def __repr__(self):
        return f"<SystemLog {self.level} {self.module} @ {self.timestamp}>"
