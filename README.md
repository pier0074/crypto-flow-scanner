# CryptoFlowScanner

A sophisticated cryptocurrency trading system for detecting Fair Value Gaps (market imbalances) across multiple timeframes with backtesting, dynamic parameters, and automated notifications.

**Repository**: https://github.com/pier0074/crypto-flow-scanner

## ✨ Features

- **Fair Value Gap Detection**: Identifies price imbalances across 6 timeframes (1m, 5m, 15m, 1h, 4h, 1d)
- **Multi-Timeframe Confluence**: Alerts when 3+ timeframes align on same direction
- **Dynamic Parameters**: Per-symbol and per-timeframe risk/detection settings
- **Interactive Web Dashboard**: Real-time charts with FVG overlays, signals table
- **Email Notifications**: Detailed trade setups (entry, SL, TP, R:R) sent automatically
- **Backtesting Engine**: Test strategies on historical data with full metrics
- **Exchange-Agnostic**: Works with 100+ exchanges via ccxt library
- **Scalable**: Ready for automated trading via exchange APIs

## 🚀 Quick Start

```bash
# Clone and setup
git clone https://github.com/pier0074/crypto-flow-scanner.git
cd crypto-flow-scanner
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Initialize (creates .env and database)
python setup.py

# Configure .env with your email settings
# Then collect data (takes ~5 min for 2 symbols, 30 days)
python scripts/collect_data.py --symbols BTC/USDT ETH/USDT --days 30

# Scan for patterns and get notifications
python scripts/scan_patterns.py --notify --summary

# Start web dashboard (optional)
python -m src.web.app
# Open http://localhost:5000
```

## ⚙️ Configuration

Key settings in `.env`:

```env
# Symbols and timeframes
SYMBOLS=BTC/USDT,ETH/USDT,BNB/USDT,SOL/USDT
TIMEFRAMES=1m,5m,15m,1h,4h,1d

# Email notifications (use Gmail App Password)
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
NOTIFICATION_EMAIL=your-email@gmail.com
SEND_NOTIFICATIONS=true

# Default parameters (can override per-symbol/timeframe)
MAX_RISK_PERCENT=1.0
TAKE_PROFIT_RR_RATIO=2.0
FVG_MIN_GAP_PERCENT=0.1
MIN_TIMEFRAME_CONFLUENCE=3
```

### Dynamic Parameters

Override parameters for specific symbols or timeframes:

```bash
# Set more conservative risk for BTC on 1m
python scripts/manage_parameters.py --symbol BTC/USDT --timeframe 1m \
  --set-risk '{"max_risk_percent": 0.5}'

# Require larger gaps on all 1m timeframes
python scripts/manage_parameters.py --timeframe 1m \
  --set-fvg '{"min_gap_percent": 0.2, "max_age_candles": 20}'

# View all overrides
python scripts/manage_parameters.py --list-all
```

## 📊 Usage

### Data Collection
```bash
# Full historical fetch
python scripts/collect_data.py --days 90

# Update with latest candles
python scripts/collect_data.py --update

# Aggregate 1m to higher timeframes (faster than fetching each)
python scripts/collect_data.py --aggregate --days 30
```

### Pattern Scanning
```bash
# Scan and notify
python scripts/scan_patterns.py --notify --summary

# Scan specific symbols
python scripts/scan_patterns.py --symbols BTC/USDT ETH/USDT

# Send daily summary
python scripts/scan_patterns.py --daily-summary
```

### Backtesting
```bash
python scripts/backtest.py --symbol BTC/USDT --timeframe 1h \
  --start-date 2024-01-01 --end-date 2024-12-01

# Example output:
# Total Trades: 45
# Win Rate: 62.2%
# Total P&L: +18.5%
# Max Drawdown: 8.3%
# Sharpe Ratio: 1.84
```

### Web Dashboard
```bash
python -m src.web.app
```
Features:
- Real-time pattern/signal overview
- Interactive candlestick charts with FVG overlays
- Multi-timeframe summary table
- Signal detail cards with trade setups

## 📁 Project Structure

```
crypto-flow-scanner/
├── src/
│   ├── data/           # ccxt data collection, SQLite storage
│   ├── patterns/       # FVG detection (extensible)
│   ├── analysis/       # Confluence detection
│   ├── backtesting/    # Strategy backtesting
│   ├── notifications/  # Email system
│   ├── web/            # Flask dashboard + Plotly charts
│   └── config/         # Settings & dynamic parameters
├── scripts/            # CLI tools
│   ├── collect_data.py
│   ├── scan_patterns.py
│   ├── backtest.py
│   └── manage_parameters.py
└── data/               # Database & parameter overrides
```

## 🎯 How It Works

1. **Data Collection**: Fetches OHLCV candles from exchanges (1m base, aggregates to higher TFs)
2. **Pattern Detection**: Scans for FVGs using dynamic parameters per symbol/timeframe
3. **Confluence Analysis**: Identifies when 3+ timeframes show same direction
4. **Signal Generation**: Creates trade setup (entry, SL, TP) based on ATR and R:R ratio
5. **Notification**: Sends HTML email with complete trade instructions
6. **Monitoring**: Web dashboard visualizes all patterns and signals in real-time

### Fair Value Gap (FVG)
A gap occurs when:
- **Bullish FVG**: `candle[0].high < candle[2].low` (price jumped up leaving gap)
- **Bearish FVG**: `candle[0].low > candle[2].high` (price dropped leaving gap)

Markets often return to "fill" these gaps, creating trading opportunities.

## 🔮 Roadmap

**Completed**:
- ✅ FVG detection with volume confirmation
- ✅ Multi-timeframe confluence
- ✅ Dynamic parameter system
- ✅ Email notifications
- ✅ Backtesting engine
- ✅ Web dashboard with charts

**Planned**:
- 🔲 Additional patterns (liquidity sweeps, order blocks, break of structure)
- 🔲 Automated trading via exchange API
- 🔲 Telegram/Discord notifications
- 🔲 Real-time WebSocket streaming
- 🔲 ML pattern optimization

## ⚠️ Disclaimer

This software is for **educational purposes only**. Trading cryptocurrencies carries significant risk. Never trade with money you cannot afford to lose. Always do your own research.

## 📄 License

MIT License
