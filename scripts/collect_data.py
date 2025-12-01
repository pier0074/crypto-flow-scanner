"""
Data collection script.
Fetches historical OHLCV data from exchanges and stores in database.
"""
import argparse
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.data.collector import collector
from src.data.storage import db_manager
from src.config.settings import settings


def main():
    """Main function for data collection."""
    parser = argparse.ArgumentParser(description='Collect historical cryptocurrency data')

    parser.add_argument(
        '--symbols',
        nargs='+',
        help='Symbols to collect (space-separated). Default: from settings'
    )

    parser.add_argument(
        '--timeframes',
        nargs='+',
        help='Timeframes to collect (space-separated). Default: from settings'
    )

    parser.add_argument(
        '--days',
        type=int,
        default=settings.INITIAL_HISTORICAL_DAYS,
        help=f'Number of days of historical data (default: {settings.INITIAL_HISTORICAL_DAYS})'
    )

    parser.add_argument(
        '--aggregate',
        action='store_true',
        help='Aggregate 1m candles to higher timeframes instead of fetching directly'
    )

    parser.add_argument(
        '--update',
        action='store_true',
        help='Only update latest data instead of full historical fetch'
    )

    args = parser.parse_args()

    # Initialize database
    db_manager.initialize()

    # Display configuration
    settings.display()

    symbols = args.symbols if args.symbols else settings.SYMBOLS
    timeframes = args.timeframes if args.timeframes else settings.TIMEFRAMES

    print(f"\n{'=' * 60}")
    print(f"Data Collection Started")
    print(f"{'=' * 60}")
    print(f"Symbols: {len(symbols)}")
    print(f"Timeframes: {', '.join(timeframes)}")
    print(f"Days: {args.days}")
    print(f"Mode: {'Update' if args.update else 'Full Historical'}")
    print(f"{'=' * 60}\n")

    try:
        if args.update:
            # Update mode: fetch only latest candles
            print("Updating with latest data...\n")

            for symbol in symbols:
                print(f"\nUpdating {symbol}...")

                for timeframe in timeframes:
                    try:
                        collector.update_latest_data(
                            symbol=symbol,
                            timeframe=timeframe,
                            save_to_db=True
                        )
                    except Exception as e:
                        print(f"Error updating {symbol} {timeframe}: {e}")

        elif args.aggregate:
            # Aggregate mode: fetch 1m and aggregate to higher timeframes
            print("Fetching 1m data and aggregating...\n")

            for symbol in symbols:
                print(f"\n{'=' * 40}")
                print(f"Processing {symbol}")
                print(f"{'=' * 40}")

                # Fetch 1m data
                print(f"Fetching 1m candles...")
                collector.fetch_historical_data(
                    symbol=symbol,
                    timeframe='1m',
                    days=args.days,
                    save_to_db=True
                )

                # Aggregate to higher timeframes
                for timeframe in timeframes:
                    if timeframe != '1m':
                        print(f"Aggregating to {timeframe}...")
                        collector.aggregate_candles(
                            source_timeframe='1m',
                            target_timeframe=timeframe,
                            symbol=symbol,
                            save_to_db=True
                        )

        else:
            # Full historical mode
            collector.collect_all_symbols(
                symbols=symbols,
                timeframes=timeframes,
                days=args.days
            )

        print(f"\n{'=' * 60}")
        print("✓ Data collection completed successfully!")
        print(f"{'=' * 60}\n")

    except KeyboardInterrupt:
        print("\n\nData collection interrupted by user")
        sys.exit(1)

    except Exception as e:
        print(f"\n\nError during data collection: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
