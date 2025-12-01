"""
Database storage operations for CryptoFlowScanner.
Handles database initialization, session management, and common queries.
"""
import os
from datetime import datetime, timedelta
from typing import List, Optional, Dict
from sqlalchemy import create_engine, and_, or_
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager

from src.data.models import Base, Candle, Pattern, Signal, BacktestResult, SystemLog
from src.config.settings import settings


class DatabaseManager:
    """Manages database connections and operations."""

    def __init__(self, database_url: Optional[str] = None):
        """
        Initialize database manager.

        Args:
            database_url: SQLAlchemy database URL. If None, uses settings.DATABASE_URL
        """
        self.database_url = database_url or settings.DATABASE_URL
        self.engine = None
        self.SessionLocal = None

    def initialize(self):
        """Initialize database engine and create tables if they don't exist."""
        # Ensure data directory exists
        if 'sqlite:///' in self.database_url:
            db_path = self.database_url.replace('sqlite:///', '')
            os.makedirs(os.path.dirname(db_path), exist_ok=True)

        # Create engine
        self.engine = create_engine(
            self.database_url,
            echo=False,  # Set to True for SQL debugging
            connect_args={'check_same_thread': False} if 'sqlite' in self.database_url else {}
        )

        # Create session factory
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

        # Create all tables
        Base.metadata.create_all(bind=self.engine)

        print(f"Database initialized: {self.database_url}")

    @contextmanager
    def get_session(self) -> Session:
        """
        Context manager for database sessions.
        Automatically commits on success and rolls back on error.

        Usage:
            with db_manager.get_session() as session:
                session.add(obj)
        """
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    # ==================== CANDLE OPERATIONS ====================

    def save_candles(self, candles: List[Dict], symbol: str, timeframe: str) -> int:
        """
        Save candles to database, avoiding duplicates.

        Args:
            candles: List of candle dictionaries with keys: timestamp, open, high, low, close, volume
            symbol: Trading pair symbol
            timeframe: Timeframe string (e.g., '1m', '5m')

        Returns:
            Number of candles saved
        """
        with self.get_session() as session:
            saved_count = 0

            for candle_data in candles:
                # Check if candle already exists
                exists = session.query(Candle).filter(
                    and_(
                        Candle.symbol == symbol,
                        Candle.timeframe == timeframe,
                        Candle.timestamp == candle_data['timestamp']
                    )
                ).first()

                if not exists:
                    candle = Candle(
                        symbol=symbol,
                        timeframe=timeframe,
                        timestamp=candle_data['timestamp'],
                        open=candle_data['open'],
                        high=candle_data['high'],
                        low=candle_data['low'],
                        close=candle_data['close'],
                        volume=candle_data['volume']
                    )
                    session.add(candle)
                    saved_count += 1

            return saved_count

    def get_candles(
        self,
        symbol: str,
        timeframe: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> List[Candle]:
        """
        Retrieve candles from database.

        Args:
            symbol: Trading pair symbol
            timeframe: Timeframe string
            start_time: Start datetime (inclusive)
            end_time: End datetime (inclusive)
            limit: Maximum number of candles to return

        Returns:
            List of Candle objects ordered by timestamp
        """
        with self.get_session() as session:
            query = session.query(Candle).filter(
                and_(
                    Candle.symbol == symbol,
                    Candle.timeframe == timeframe
                )
            )

            if start_time:
                query = query.filter(Candle.timestamp >= start_time)

            if end_time:
                query = query.filter(Candle.timestamp <= end_time)

            query = query.order_by(Candle.timestamp.asc())

            if limit:
                query = query.limit(limit)

            return query.all()

    def get_latest_candle_timestamp(self, symbol: str, timeframe: str) -> Optional[datetime]:
        """Get the timestamp of the most recent candle for a symbol/timeframe."""
        with self.get_session() as session:
            result = session.query(Candle.timestamp).filter(
                and_(
                    Candle.symbol == symbol,
                    Candle.timeframe == timeframe
                )
            ).order_by(Candle.timestamp.desc()).first()

            return result[0] if result else None

    # ==================== PATTERN OPERATIONS ====================

    def save_pattern(self, pattern: Pattern) -> Pattern:
        """Save a pattern to database."""
        with self.get_session() as session:
            session.add(pattern)
            session.flush()
            session.refresh(pattern)
            return pattern

    def get_valid_patterns(
        self,
        symbol: Optional[str] = None,
        pattern_type: Optional[str] = None,
        timeframe: Optional[str] = None
    ) -> List[Pattern]:
        """Get all valid (unfilled) patterns."""
        with self.get_session() as session:
            query = session.query(Pattern).filter(Pattern.is_valid == True)

            if symbol:
                query = query.filter(Pattern.symbol == symbol)

            if pattern_type:
                query = query.filter(Pattern.pattern_type == pattern_type)

            if timeframe:
                query = query.filter(Pattern.timeframe == timeframe)

            return query.order_by(Pattern.start_timestamp.desc()).all()

    def invalidate_pattern(self, pattern_id: int, filled_timestamp: datetime):
        """Mark a pattern as invalid/filled."""
        with self.get_session() as session:
            pattern = session.query(Pattern).filter(Pattern.id == pattern_id).first()
            if pattern:
                pattern.is_valid = False
                pattern.filled_timestamp = filled_timestamp

    # ==================== SIGNAL OPERATIONS ====================

    def save_signal(self, signal: Signal) -> Signal:
        """Save a trading signal to database."""
        with self.get_session() as session:
            session.add(signal)
            session.flush()
            session.refresh(signal)
            return signal

    def get_active_signals(self, symbol: Optional[str] = None) -> List[Signal]:
        """Get all active signals."""
        with self.get_session() as session:
            query = session.query(Signal).filter(Signal.status == 'active')

            if symbol:
                query = query.filter(Signal.symbol == symbol)

            return query.order_by(Signal.created_at.desc()).all()

    def get_unnotified_signals(self) -> List[Signal]:
        """Get signals that haven't been notified yet."""
        with self.get_session() as session:
            return session.query(Signal).filter(
                and_(
                    Signal.notified == False,
                    Signal.status == 'active'
                )
            ).all()

    def mark_signal_notified(self, signal_id: int):
        """Mark a signal as notified."""
        with self.get_session() as session:
            signal = session.query(Signal).filter(Signal.id == signal_id).first()
            if signal:
                signal.notified = True
                signal.notification_sent_at = datetime.utcnow()

    def update_signal_status(
        self,
        signal_id: int,
        status: str,
        **kwargs
    ):
        """Update signal status and optional fields."""
        with self.get_session() as session:
            signal = session.query(Signal).filter(Signal.id == signal_id).first()
            if signal:
                signal.status = status
                for key, value in kwargs.items():
                    if hasattr(signal, key):
                        setattr(signal, key, value)

    # ==================== BACKTEST OPERATIONS ====================

    def save_backtest_result(self, result: BacktestResult) -> BacktestResult:
        """Save backtest results to database."""
        with self.get_session() as session:
            session.add(result)
            session.flush()
            session.refresh(result)
            return result

    def get_backtest_results(
        self,
        strategy_name: Optional[str] = None,
        symbol: Optional[str] = None,
        limit: int = 10
    ) -> List[BacktestResult]:
        """Get backtest results."""
        with self.get_session() as session:
            query = session.query(BacktestResult)

            if strategy_name:
                query = query.filter(BacktestResult.strategy_name == strategy_name)

            if symbol:
                query = query.filter(BacktestResult.symbol == symbol)

            return query.order_by(BacktestResult.created_at.desc()).limit(limit).all()

    # ==================== SYSTEM LOG OPERATIONS ====================

    def log(self, level: str, module: str, message: str, details: Optional[str] = None):
        """Add a system log entry."""
        with self.get_session() as session:
            log = SystemLog(
                level=level,
                module=module,
                message=message,
                details=details
            )
            session.add(log)

    def get_recent_logs(self, level: Optional[str] = None, limit: int = 100) -> List[SystemLog]:
        """Get recent system logs."""
        with self.get_session() as session:
            query = session.query(SystemLog)

            if level:
                query = query.filter(SystemLog.level == level)

            return query.order_by(SystemLog.timestamp.desc()).limit(limit).all()


# Global database manager instance
db_manager = DatabaseManager()
