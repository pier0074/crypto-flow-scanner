"""
Setup script for CryptoFlowScanner.
Initializes the database and checks configuration.
"""
import sys
import os

# Add to path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.data.storage import db_manager
from src.config.settings import settings


def main():
    """Setup and initialize CryptoFlowScanner."""
    print("\n" + "=" * 60)
    print("CryptoFlowScanner Setup")
    print("=" * 60 + "\n")

    # Check if .env file exists
    if not os.path.exists('.env'):
        print("⚠ No .env file found!")
        print("\nCreating .env from .env.example...")

        if os.path.exists('.env.example'):
            import shutil
            shutil.copy('.env.example', '.env')
            print("✓ Created .env file")
            print("\n⚠ Please edit .env file with your settings before continuing")
            print("  - Set your email notification settings (SMTP_USER, SMTP_PASSWORD, etc.)")
            print("  - Configure your preferred symbols and timeframes")
            print("  - Adjust risk management parameters\n")
            return
        else:
            print("Error: .env.example not found")
            return

    # Validate configuration
    print("Validating configuration...")
    if settings.validate():
        print("✓ Configuration valid\n")
        settings.display()
    else:
        print("\n⚠ Please fix configuration errors in .env file\n")
        return

    # Initialize database
    print("Initializing database...")
    try:
        db_manager.initialize()
        print("✓ Database initialized\n")
    except Exception as e:
        print(f"Error initializing database: {e}\n")
        return

    # Create necessary directories
    print("Creating directories...")
    os.makedirs('data', exist_ok=True)
    os.makedirs('logs', exist_ok=True)
    print("✓ Directories created\n")

    print("=" * 60)
    print("Setup Complete!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Collect historical data:")
    print("   python scripts/collect_data.py --days 30")
    print("\n2. Scan for patterns:")
    print("   python scripts/scan_patterns.py --notify")
    print("\n3. Run a backtest:")
    print("   python scripts/backtest.py --symbol BTC/USDT --timeframe 1h")
    print("\n4. (Optional) Start web dashboard:")
    print("   python -m src.web.app")
    print("=" * 60 + "\n")


if __name__ == '__main__':
    main()
