"""
Data collection module for fetching OHLCV candles from cryptocurrency exchanges.
Uses ccxt library for exchange-agnostic data collection.
"""
import ccxt
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import time

from src.config.settings import settings
from src.data.storage import db_manager


class DataCollector:
    """Collects OHLCV data from cryptocurrency exchanges."""

    def __init__(self, exchange_name: str = None):
        """
        Initialize data collector.

        Args:
            exchange_name: Name of the exchange (default from settings)
        """
        self.exchange_name = exchange_name or settings.EXCHANGE
        self.exchange = self._initialize_exchange()

    def _initialize_exchange(self):
        """Initialize the exchange connection."""
        exchange_class = getattr(ccxt, self.exchange_name)
        exchange = exchange_class({
            'enableRateLimit': True,  # Respect exchange rate limits
            'options': {
                'defaultType': 'spot',  # Use spot market
            }
        })

        # Test connection
        try:
            exchange.load_markets()
            print(f"Connected to {self.exchange_name}")
            return exchange
        except Exception as e:
            print(f"Error connecting to {self.exchange_name}: {e}")
            raise

    def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str = '1m',
        since: Optional[datetime] = None,
        limit: int = 1000
    ) -> List[Dict]:
        """
        Fetch OHLCV data from exchange.

        Args:
            symbol: Trading pair (e.g., 'BTC/USDT')
            timeframe: Timeframe string (e.g., '1m', '5m', '1h')
            since: Start datetime
            limit: Maximum number of candles to fetch

        Returns:
            List of candle dictionaries
        """
        try:
            # Convert datetime to timestamp if provided
            since_timestamp = None
            if since:
                since_timestamp = int(since.timestamp() * 1000)

            # Fetch OHLCV data
            ohlcv = self.exchange.fetch_ohlcv(
                symbol=symbol,
                timeframe=timeframe,
                since=since_timestamp,
                limit=limit
            )

            # Convert to list of dictionaries
            candles = []
            for candle in ohlcv:
                candles.append({
                    'timestamp': datetime.fromtimestamp(candle[0] / 1000),
                    'open': float(candle[1]),
                    'high': float(candle[2]),
                    'low': float(candle[3]),
                    'close': float(candle[4]),
                    'volume': float(candle[5])
                })

            return candles

        except Exception as e:
            print(f"Error fetching OHLCV for {symbol} {timeframe}: {e}")
            return []

    def fetch_historical_data(
        self,
        symbol: str,
        timeframe: str,
        days: int,
        save_to_db: bool = True
    ) -> pd.DataFrame:
        """
        Fetch historical data for a specified number of days.
        Handles pagination to fetch all data.

        Args:
            symbol: Trading pair
            timeframe: Timeframe string
            days: Number of days of historical data
            save_to_db: Whether to save to database

        Returns:
            DataFrame with OHLCV data
        """
        print(f"Fetching {days} days of {timeframe} data for {symbol}...")

        # Calculate start time
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=days)

        all_candles = []
        current_time = start_time

        # Fetch data in batches
        while current_time < end_time:
            candles = self.fetch_ohlcv(
                symbol=symbol,
                timeframe=timeframe,
                since=current_time,
                limit=1000
            )

            if not candles:
                break

            all_candles.extend(candles)

            # Move to next batch
            current_time = candles[-1]['timestamp'] + timedelta(minutes=1)

            # Rate limiting
            time.sleep(self.exchange.rateLimit / 1000)

        print(f"Fetched {len(all_candles)} candles for {symbol} {timeframe}")

        # Save to database if requested
        if save_to_db and all_candles:
            saved_count = db_manager.save_candles(all_candles, symbol, timeframe)
            print(f"Saved {saved_count} new candles to database")

        # Convert to DataFrame
        if all_candles:
            df = pd.DataFrame(all_candles)
            df.set_index('timestamp', inplace=True)
            return df
        else:
            return pd.DataFrame()

    def update_latest_data(
        self,
        symbol: str,
        timeframe: str,
        save_to_db: bool = True
    ) -> List[Dict]:
        """
        Update with the latest candles since the last stored candle.

        Args:
            symbol: Trading pair
            timeframe: Timeframe string
            save_to_db: Whether to save to database

        Returns:
            List of new candles
        """
        # Get the latest candle timestamp from database
        latest_timestamp = db_manager.get_latest_candle_timestamp(symbol, timeframe)

        if latest_timestamp:
            # Fetch candles since the latest timestamp
            since = latest_timestamp + timedelta(minutes=1)
        else:
            # No data exists, fetch last 1000 candles
            since = datetime.utcnow() - timedelta(days=1)

        candles = self.fetch_ohlcv(
            symbol=symbol,
            timeframe=timeframe,
            since=since,
            limit=1000
        )

        if save_to_db and candles:
            saved_count = db_manager.save_candles(candles, symbol, timeframe)
            print(f"Updated {symbol} {timeframe}: {saved_count} new candles")

        return candles

    def aggregate_candles(
        self,
        source_timeframe: str,
        target_timeframe: str,
        symbol: str,
        save_to_db: bool = True
    ) -> int:
        """
        Aggregate candles from smaller timeframe to larger timeframe.
        For example, aggregate 1m candles to 5m, 15m, 1h, etc.

        Args:
            source_timeframe: Source timeframe (e.g., '1m')
            target_timeframe: Target timeframe (e.g., '5m', '1h')
            symbol: Trading pair
            save_to_db: Whether to save aggregated candles

        Returns:
            Number of candles aggregated
        """
        # Get source candles from database
        candles = db_manager.get_candles(symbol, source_timeframe)

        if not candles:
            return 0

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

        # Resample to target timeframe
        target_minutes = settings.get_timeframe_minutes(target_timeframe)
        resampled = df.resample(f'{target_minutes}T').agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }).dropna()

        # Convert back to list of dicts
        aggregated_candles = []
        for timestamp, row in resampled.iterrows():
            aggregated_candles.append({
                'timestamp': timestamp,
                'open': float(row['open']),
                'high': float(row['high']),
                'low': float(row['low']),
                'close': float(row['close']),
                'volume': float(row['volume'])
            })

        # Save to database
        if save_to_db and aggregated_candles:
            saved_count = db_manager.save_candles(aggregated_candles, symbol, target_timeframe)
            print(f"Aggregated {symbol} {source_timeframe} -> {target_timeframe}: {saved_count} candles")
            return saved_count

        return len(aggregated_candles)

    def get_top_symbols(self, quote_currency: str = 'USDT', limit: int = 50) -> List[str]:
        """
        Get top symbols by 24h volume.

        Args:
            quote_currency: Quote currency (e.g., 'USDT')
            limit: Number of symbols to return

        Returns:
            List of symbol strings
        """
        try:
            tickers = self.exchange.fetch_tickers()

            # Filter by quote currency and sort by volume
            filtered = [
                (symbol, ticker)
                for symbol, ticker in tickers.items()
                if symbol.endswith(f'/{quote_currency}') and ticker.get('quoteVolume')
            ]

            sorted_symbols = sorted(
                filtered,
                key=lambda x: x[1]['quoteVolume'],
                reverse=True
            )

            return [symbol for symbol, _ in sorted_symbols[:limit]]

        except Exception as e:
            print(f"Error fetching top symbols: {e}")
            return []

    def collect_all_symbols(
        self,
        symbols: Optional[List[str]] = None,
        timeframes: Optional[List[str]] = None,
        days: int = None
    ):
        """
        Collect historical data for multiple symbols and timeframes.

        Args:
            symbols: List of symbols (default from settings)
            timeframes: List of timeframes (default from settings)
            days: Number of days to collect (default from settings)
        """
        symbols = symbols or settings.SYMBOLS
        timeframes = timeframes or settings.TIMEFRAMES
        days = days or settings.INITIAL_HISTORICAL_DAYS

        total_symbols = len(symbols)
        total_timeframes = len(timeframes)

        print(f"\n=== Starting data collection ===")
        print(f"Symbols: {total_symbols}")
        print(f"Timeframes: {total_timeframes}")
        print(f"Days: {days}")
        print(f"Total operations: {total_symbols * total_timeframes}\n")

        for idx, symbol in enumerate(symbols, 1):
            print(f"\n[{idx}/{total_symbols}] Processing {symbol}")

            for timeframe in timeframes:
                try:
                    self.fetch_historical_data(
                        symbol=symbol,
                        timeframe=timeframe,
                        days=days,
                        save_to_db=True
                    )

                    # Rate limiting between requests
                    time.sleep(self.exchange.rateLimit / 1000)

                except Exception as e:
                    print(f"Error collecting {symbol} {timeframe}: {e}")
                    continue

        print(f"\n=== Data collection complete ===\n")


# Global collector instance
collector = DataCollector()
