# CryptoFlowScanner

A sophisticated cryptocurrency trading system for detecting market imbalances (Fair Value Gaps) across multiple timeframes with backtesting capabilities and automated notifications.

## Features

- **Multi-Timeframe Analysis**: Scans 1m, 5m, 15m, 1H, 4H, and 1D timeframes simultaneously
- **Fair Value Gap (FVG) Detection**: Identifies imbalances in price action
- **Confluence Detection**: Finds opportunities when multiple timeframes align
- **Backtesting Engine**: Test strategies against historical data
- **Email Notifications**: Get trade setup alerts (entry, TP, SL) via email
- **Web Dashboard**: Visual interface with charts and opportunity summary
- **Scalable Architecture**: Ready for future automated trading via exchange APIs
- **Top 20-50 Crypto Support**: Focus on the most liquid cryptocurrencies

## Architecture

### Data Collection
- Uses `ccxt` library for exchange-agnostic data collection
- Stores 1-minute candles and aggregates to other timeframes
- SQLite database for local development (easily upgradable to PostgreSQL)

### Pattern Detection
- Modular pattern system (starting with FVG)
- Easy to add new patterns later
- Configurable detection parameters

### Trading Approach
- Phase 1: Manual trading with limit orders via notifications
- Phase 2: Automated trading via exchange API (planned)

## Quick Start

```bash
# Clone the repository
git clone https://github.com/pier0074/crypto-flow-scanner.git
cd crypto-flow-scanner

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run setup (creates .env and initializes database)
python setup.py

# Edit .env with your settings (especially email notifications)
# Then collect some historical data (this may take a few minutes)
python scripts/collect_data.py --symbols BTC/USDT ETH/USDT --days 30

# Scan for patterns and get notifications
python scripts/scan_patterns.py --notify --summary
```

## Installation

See [Quick Start](#quick-start) above for the fastest way to get started.

### Manual Installation

```bash
# Clone and setup virtual environment
git clone https://github.com/pier0074/crypto-flow-scanner.git
cd crypto-flow-scanner
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy and configure environment variables
cp .env.example .env
# Edit .env with your settings
```

## Configuration

Edit `.env` file with your settings:

```env
# Exchange settings
EXCHANGE=binance
SYMBOLS=BTC/USDT,ETH/USDT,BNB/USDT

# Notification settings
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
NOTIFICATION_EMAIL=your-email@gmail.com

# Trading parameters
POSITION_SIZE_PERCENT=2.0
MAX_RISK_PERCENT=1.0
STOP_LOSS_ATR_MULTIPLIER=1.5

# Backtesting
BACKTEST_START_DATE=2024-01-01
BACKTEST_END_DATE=2024-12-01
```

## Usage

### 1. Collect Historical Data

```bash
python scripts/collect_data.py --symbols BTC/USDT ETH/USDT --days 90
```

### 2. Run Pattern Scanner

```bash
# Scan for opportunities and send notifications
python scripts/scan_patterns.py --notify

# Scan specific symbols
python scripts/scan_patterns.py --symbols BTC/USDT ETH/USDT
```

### 3. Run Backtesting

```bash
python scripts/backtest.py --pattern fvg --start-date 2024-01-01 --end-date 2024-12-01
```

### 4. Start Web Dashboard

```bash
python -m src.web.app
# Open browser to http://localhost:5000
```

## Project Structure

```
crypto-flow-scanner/
├── src/                    # Source code
│   ├── data/              # Data collection and storage
│   ├── patterns/          # Pattern detection algorithms
│   ├── analysis/          # Multi-timeframe and confluence analysis
│   ├── backtesting/       # Backtesting engine
│   ├── notifications/     # Email notification system
│   ├── web/               # Web dashboard
│   └── config/            # Configuration management
├── scripts/               # Executable scripts
├── tests/                 # Unit tests
├── data/                  # SQLite database and cache
└── logs/                  # Application logs
```

## Roadmap

- [x] Project setup and architecture
- [x] Data collection module (ccxt integration)
- [x] FVG pattern detection
- [x] Multi-timeframe analysis
- [x] Confluence detection
- [x] Backtesting engine
- [x] Email notifications
- [x] Configuration management
- [x] Executable scripts
- [ ] Web dashboard with charts
- [ ] Additional patterns (liquidity sweeps, order blocks)
- [ ] Exchange API integration for automated trading
- [ ] Mobile notifications (Telegram/Discord)
- [ ] Machine learning pattern optimization
- [ ] Real-time WebSocket data streaming
- [ ] Advanced risk management features

## Contributing

This is a personal trading project. Use at your own risk.

## Disclaimer

This software is for educational purposes only. Trading cryptocurrencies carries significant risk. Never trade with money you cannot afford to lose. Always do your own research and consider seeking advice from a licensed financial advisor.

## License

MIT License
