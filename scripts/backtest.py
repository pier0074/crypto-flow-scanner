"""
Backtesting script.
Tests trading strategies on historical data.
"""
import argparse
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.backtesting.engine import backtest_engine
from src.data.storage import db_manager
from src.config.settings import settings


def main():
    """Main function for backtesting."""
    parser = argparse.ArgumentParser(description='Backtest trading strategies')

    parser.add_argument(
        '--symbol',
        required=True,
        help='Symbol to backtest (e.g., BTC/USDT)'
    )

    parser.add_argument(
        '--timeframe',
        default='1h',
        help='Timeframe to backtest (default: 1h)'
    )

    parser.add_argument(
        '--start-date',
        default=settings.BACKTEST_START_DATE,
        help=f'Start date YYYY-MM-DD (default: {settings.BACKTEST_START_DATE})'
    )

    parser.add_argument(
        '--end-date',
        default=settings.BACKTEST_END_DATE,
        help=f'End date YYYY-MM-DD (default: {settings.BACKTEST_END_DATE})'
    )

    parser.add_argument(
        '--capital',
        type=float,
        default=settings.BACKTEST_INITIAL_CAPITAL,
        help=f'Initial capital (default: {settings.BACKTEST_INITIAL_CAPITAL})'
    )

    parser.add_argument(
        '--pattern',
        choices=['fvg'],
        default='fvg',
        help='Pattern type to backtest (default: fvg)'
    )

    args = parser.parse_args()

    # Initialize database
    db_manager.initialize()

    print(f"\n{'=' * 60}")
    print(f"CryptoFlowScanner Backtesting")
    print(f"{'=' * 60}\n")

    try:
        # Check if we have data for this symbol/timeframe
        candles = db_manager.get_candles(
            symbol=args.symbol,
            timeframe=args.timeframe,
            limit=10
        )

        if not candles:
            print(f"Error: No data found for {args.symbol} {args.timeframe}")
            print(f"\nPlease run data collection first:")
            print(f"python scripts/collect_data.py --symbols {args.symbol} --timeframes {args.timeframe}\n")
            sys.exit(1)

        # Run backtest
        if args.pattern == 'fvg':
            result = backtest_engine.backtest_fvg_strategy(
                symbol=args.symbol,
                timeframe=args.timeframe,
                start_date=args.start_date,
                end_date=args.end_date
            )

            if result:
                print("✓ Backtest completed and saved to database")

                # Display trade history
                if backtest_engine.trades:
                    print(f"\n{'=' * 80}")
                    print("TRADE HISTORY")
                    print(f"{'=' * 80}")
                    print(f"{'#':<4} {'Direction':<8} {'Entry':<12} {'Exit':<12} {'P&L':<12} {'Reason':<12}")
                    print(f"{'=' * 80}")

                    for idx, trade in enumerate(backtest_engine.trades[:20], 1):  # Show first 20 trades
                        pnl_str = f"${trade['pnl']:,.2f}" if trade['pnl'] else "Open"
                        print(
                            f"{idx:<4} "
                            f"{trade['direction']:<8} "
                            f"{trade['entry_price']:<12.8f} "
                            f"{trade['exit_price']:<12.8f} "
                            f"{pnl_str:<12} "
                            f"{trade['exit_reason']:<12}"
                        )

                    if len(backtest_engine.trades) > 20:
                        print(f"\n... and {len(backtest_engine.trades) - 20} more trades")

                    print(f"{'=' * 80}\n")

        else:
            print(f"Pattern type '{args.pattern}' not implemented yet")
            sys.exit(1)

    except KeyboardInterrupt:
        print("\n\nBacktest interrupted by user")
        sys.exit(1)

    except Exception as e:
        print(f"\n\nError during backtesting: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
