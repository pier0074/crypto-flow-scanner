"""
Pattern scanning script.
Scans for trading patterns and generates signals with confluence detection.
"""
import argparse
import sys
import os
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.patterns.detector import pattern_detector
from src.analysis.confluence import confluence_analyzer
from src.notifications.email_sender import email_notifier
from src.data.storage import db_manager
from src.config.settings import settings


def main():
    """Main function for pattern scanning."""
    parser = argparse.ArgumentParser(description='Scan for trading patterns and generate signals')

    parser.add_argument(
        '--symbols',
        nargs='+',
        help='Symbols to scan (space-separated). Default: from settings'
    )

    parser.add_argument(
        '--timeframes',
        nargs='+',
        help='Timeframes to scan (space-separated). Default: from settings'
    )

    parser.add_argument(
        '--patterns',
        nargs='+',
        choices=['fvg', 'all'],
        default=['fvg'],
        help='Pattern types to detect (default: fvg)'
    )

    parser.add_argument(
        '--notify',
        action='store_true',
        help='Send email notifications for new signals'
    )

    parser.add_argument(
        '--summary',
        action='store_true',
        help='Display summary of detected patterns and signals'
    )

    parser.add_argument(
        '--daily-summary',
        action='store_true',
        help='Send daily summary email'
    )

    args = parser.parse_args()

    # Initialize database
    db_manager.initialize()

    # Display configuration
    settings.display()

    symbols = args.symbols if args.symbols else settings.SYMBOLS
    timeframes = args.timeframes if args.timeframes else settings.TIMEFRAMES
    pattern_types = None if 'all' in args.patterns else args.patterns

    print(f"\n{'=' * 60}")
    print(f"Pattern Scanner Started")
    print(f"{'=' * 60}")
    print(f"Symbols: {len(symbols)}")
    print(f"Timeframes: {', '.join(timeframes)}")
    print(f"Patterns: {', '.join(pattern_types) if pattern_types else 'all'}")
    print(f"Notifications: {'Enabled' if args.notify else 'Disabled'}")
    print(f"{'=' * 60}\n")

    try:
        # Step 1: Detect patterns
        print(f"[1/3] Detecting patterns...\n")
        pattern_results = pattern_detector.scan_all_symbols(
            symbols=symbols,
            timeframes=timeframes,
            pattern_types=pattern_types
        )

        total_patterns = sum(len(patterns) for patterns in pattern_results.values())
        print(f"✓ Detected {total_patterns} patterns\n")

        # Step 2: Analyze confluence and generate signals
        print(f"[2/3] Analyzing confluence...\n")
        signal_results = confluence_analyzer.scan_all_symbols_for_confluence(
            symbols=symbols,
            save_to_db=True
        )

        total_signals = sum(len(signals) for signals in signal_results.values())
        print(f"✓ Generated {total_signals} signals with confluence\n")

        # Step 3: Send notifications
        if args.notify and total_signals > 0:
            print(f"[3/3] Sending notifications...\n")

            if not settings.SEND_NOTIFICATIONS:
                print("⚠ Notifications are disabled in settings")
                print("Set SEND_NOTIFICATIONS=true in .env to enable\n")
            else:
                sent_count = email_notifier.notify_unnotified_signals()
                print(f"✓ Sent {sent_count} notifications\n")
        else:
            print(f"[3/3] Skipping notifications\n")

        # Display summary if requested
        if args.summary:
            display_summary(pattern_results, signal_results)

        # Send daily summary if requested
        if args.daily_summary:
            print("Sending daily summary...")
            active_signals = db_manager.get_active_signals()
            email_notifier.send_daily_summary(active_signals, total_patterns)

        print(f"\n{'=' * 60}")
        print("✓ Pattern scanning completed successfully!")
        print(f"{'=' * 60}")
        print(f"Total patterns detected: {total_patterns}")
        print(f"Total signals generated: {total_signals}")
        print(f"{'=' * 60}\n")

    except KeyboardInterrupt:
        print("\n\nPattern scanning interrupted by user")
        sys.exit(1)

    except Exception as e:
        print(f"\n\nError during pattern scanning: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def display_summary(pattern_results, signal_results):
    """Display detailed summary of results."""
    print(f"\n{'=' * 80}")
    print("PATTERN SUMMARY")
    print(f"{'=' * 80}\n")

    pattern_summary = pattern_detector.get_pattern_summary()
    print(f"Total patterns: {pattern_summary['total']}")
    print(f"Bullish patterns: {pattern_summary['bullish']}")
    print(f"Bearish patterns: {pattern_summary['bearish']}\n")

    print("Patterns by symbol:")
    for symbol, count in pattern_summary['by_symbol'].items():
        if count > 0:
            print(f"  {symbol}: {count}")

    print(f"\n{'=' * 80}")
    print("SIGNAL SUMMARY")
    print(f"{'=' * 80}\n")

    all_signals = []
    for signals in signal_results.values():
        all_signals.extend(signals)

    if all_signals:
        confluence_analyzer.display_signals(all_signals)
    else:
        print("No signals generated (no sufficient confluence)\n")

    # Show confluence summary
    confluence_summary = confluence_analyzer.get_confluence_summary()

    print(f"\nActive signals: {confluence_summary['total_signals']}")
    print(f"Long signals: {confluence_summary['long_signals']}")
    print(f"Short signals: {confluence_summary['short_signals']}")

    if confluence_summary['high_confluence']:
        print(f"\n⭐ High confluence signals (>{settings.MIN_TIMEFRAME_CONFLUENCE} TFs):")
        for signal in confluence_summary['high_confluence']:
            print(f"  {signal.symbol} {signal.direction.upper()} - {signal.confluence_count} timeframes")

    print()


if __name__ == '__main__':
    main()
