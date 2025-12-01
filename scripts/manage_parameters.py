"""
Parameter management script.
Allows viewing and setting dynamic parameters per symbol/timeframe.
"""
import argparse
import sys
import os
import json

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.config.parameters import parameter_manager


def main():
    """Main function for parameter management."""
    parser = argparse.ArgumentParser(description='Manage dynamic trading parameters')

    parser.add_argument(
        '--view',
        action='store_true',
        help='View current parameters'
    )

    parser.add_argument(
        '--symbol',
        help='Symbol to configure'
    )

    parser.add_argument(
        '--timeframe',
        help='Timeframe to configure'
    )

    parser.add_argument(
        '--set-risk',
        help='Set risk parameters (JSON format): {"max_risk_percent": 1.0, ...}'
    )

    parser.add_argument(
        '--set-fvg',
        help='Set FVG parameters (JSON format): {"min_gap_percent": 0.1, ...}'
    )

    parser.add_argument(
        '--remove',
        action='store_true',
        help='Remove parameter overrides for symbol/timeframe'
    )

    parser.add_argument(
        '--list-all',
        action='store_true',
        help='List all parameter overrides'
    )

    parser.add_argument(
        '--examples',
        action='store_true',
        help='Show parameter configuration examples'
    )

    args = parser.parse_args()

    if args.examples:
        show_examples()
        return

    if args.list_all:
        list_all_overrides()
        return

    if args.view:
        parameter_manager.display_parameters(args.symbol, args.timeframe)
        return

    if args.remove:
        if not args.symbol:
            print("Error: --symbol required with --remove")
            sys.exit(1)

        parameter_manager.remove_symbol_parameters(args.symbol, args.timeframe)
        print(f"✓ Removed parameter overrides for {args.symbol}" +
              (f" {args.timeframe}" if args.timeframe else ""))
        return

    if args.set_risk or args.set_fvg:
        if not args.symbol and not args.timeframe:
            print("Error: --symbol or --timeframe required when setting parameters")
            sys.exit(1)

        parameters = {}

        if args.set_risk:
            try:
                parameters['risk'] = json.loads(args.set_risk)
            except json.JSONDecodeError as e:
                print(f"Error parsing risk parameters: {e}")
                sys.exit(1)

        if args.set_fvg:
            try:
                parameters['fvg'] = json.loads(args.set_fvg)
            except json.JSONDecodeError as e:
                print(f"Error parsing FVG parameters: {e}")
                sys.exit(1)

        if args.symbol:
            parameter_manager.set_symbol_parameters(args.symbol, parameters, args.timeframe)
            print(f"✓ Set parameters for {args.symbol}" +
                  (f" {args.timeframe}" if args.timeframe else ""))
        elif args.timeframe:
            parameter_manager.set_timeframe_parameters(args.timeframe, parameters)
            print(f"✓ Set parameters for all symbols on {args.timeframe}")

        # Show the new parameters
        parameter_manager.display_parameters(args.symbol, args.timeframe)
        return

    # Default: show help
    parser.print_help()


def list_all_overrides():
    """List all parameter overrides."""
    overrides = parameter_manager.get_all_overrides()

    print("\n" + "=" * 60)
    print("Parameter Overrides")
    print("=" * 60)

    if not overrides:
        print("\nNo parameter overrides configured")
        print("All symbols/timeframes use default parameters\n")
        return

    # Timeframe-level overrides
    if 'timeframes' in overrides and overrides['timeframes']:
        print("\nTimeframe-Level Overrides (apply to all symbols):")
        print("-" * 60)
        for tf, params in overrides['timeframes'].items():
            print(f"\n  {tf}:")
            print(f"    {json.dumps(params, indent=4)}")

    # Symbol-level overrides
    if 'symbols' in overrides and overrides['symbols']:
        print("\nSymbol-Level Overrides:")
        print("-" * 60)
        for symbol, config in overrides['symbols'].items():
            print(f"\n  {symbol}:")

            if 'default' in config:
                print("    All timeframes:")
                print(f"      {json.dumps(config['default'], indent=6)}")

            if 'timeframes' in config:
                for tf, params in config['timeframes'].items():
                    print(f"    {tf}:")
                    print(f"      {json.dumps(params, indent=6)}")

    print("\n" + "=" * 60 + "\n")


def show_examples():
    """Show parameter configuration examples."""
    print("\n" + "=" * 60)
    print("Parameter Configuration Examples")
    print("=" * 60)

    print("\n1. View default parameters:")
    print("   python scripts/manage_parameters.py --view")

    print("\n2. View parameters for specific symbol:")
    print("   python scripts/manage_parameters.py --view --symbol BTC/USDT")

    print("\n3. Set more conservative risk for BTC on 1m timeframe:")
    print('   python scripts/manage_parameters.py --symbol BTC/USDT --timeframe 1m \\')
    print('     --set-risk \'{"max_risk_percent": 0.5, "position_size_percent": 1.0}\'')

    print("\n4. Require larger gaps for all 1m timeframes:")
    print('   python scripts/manage_parameters.py --timeframe 1m \\')
    print('     --set-fvg \'{"min_gap_percent": 0.2, "max_age_candles": 20}\'')

    print("\n5. Set aggressive take profit for ETH:")
    print('   python scripts/manage_parameters.py --symbol ETH/USDT \\')
    print('     --set-risk \'{"take_profit_rr_ratio": 3.0}\'')

    print("\n6. Disable volume confirmation for volatile coins:")
    print('   python scripts/manage_parameters.py --symbol DOGE/USDT \\')
    print('     --set-fvg \'{"volume_confirmation": false}\'')

    print("\n7. List all overrides:")
    print("   python scripts/manage_parameters.py --list-all")

    print("\n8. Remove overrides for a symbol:")
    print("   python scripts/manage_parameters.py --remove --symbol BTC/USDT")

    print("\n9. Remove timeframe-specific override:")
    print("   python scripts/manage_parameters.py --remove --symbol BTC/USDT --timeframe 1m")

    print("\n" + "=" * 60)
    print("\nAvailable Parameters:")
    print("=" * 60)

    print("\nRisk Parameters:")
    print("  - max_risk_percent: Maximum risk per trade (default: 1.0)")
    print("  - position_size_percent: Position size as % of capital (default: 2.0)")
    print("  - stop_loss_atr_multiplier: SL distance in ATR (default: 1.5)")
    print("  - take_profit_rr_ratio: Risk/reward ratio (default: 2.0)")

    print("\nFVG Parameters:")
    print("  - min_gap_percent: Minimum gap size (default: 0.1)")
    print("  - max_age_candles: Max candles before expiry (default: 50)")
    print("  - volume_confirmation: Require volume spike (default: true)")

    print("\n" + "=" * 60 + "\n")


if __name__ == '__main__':
    main()
