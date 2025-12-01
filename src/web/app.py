"""
Web dashboard for CryptoFlowScanner.
Displays patterns, signals, and interactive charts.
"""
from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
import pandas as pd
from datetime import datetime, timedelta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly
import json

from src.data.storage import db_manager
from src.patterns.detector import pattern_detector
from src.analysis.confluence import confluence_analyzer
from src.config.settings import settings
from src.config.parameters import parameter_manager

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Initialize database
db_manager.initialize()


@app.route('/')
def index():
    """Home page with summary and active signals."""
    return render_template('index.html')


@app.route('/api/summary')
def get_summary():
    """Get summary of patterns and signals."""
    # Get pattern summary
    pattern_summary = pattern_detector.get_pattern_summary()

    # Get confluence summary
    confluence_summary = confluence_analyzer.get_confluence_summary()

    # Get active signals
    active_signals = db_manager.get_active_signals()

    # Format signals for display
    signals_data = []
    for signal in active_signals:
        signals_data.append({
            'id': signal.id,
            'symbol': signal.symbol,
            'direction': signal.direction,
            'entry_price': signal.entry_price,
            'stop_loss': signal.stop_loss,
            'take_profit': signal.take_profit,
            'risk_reward': signal.risk_reward_ratio,
            'confluence': signal.confluence_count,
            'timeframe': signal.primary_timeframe,
            'created_at': signal.created_at.strftime('%Y-%m-%d %H:%M'),
            'notified': signal.notified
        })

    # Get timeframe breakdown
    timeframe_data = {}
    for symbol in settings.SYMBOLS[:10]:  # Limit to first 10 for summary
        timeframe_data[symbol] = {}
        for tf in settings.TIMEFRAMES:
            patterns = db_manager.get_valid_patterns(symbol=symbol, timeframe=tf)
            bullish = len([p for p in patterns if p.direction == 'bullish'])
            bearish = len([p for p in patterns if p.direction == 'bearish'])
            timeframe_data[symbol][tf] = {
                'bullish': bullish,
                'bearish': bearish,
                'total': bullish + bearish
            }

    return jsonify({
        'patterns': {
            'total': pattern_summary['total'],
            'bullish': pattern_summary['bullish'],
            'bearish': pattern_summary['bearish'],
            'by_symbol': pattern_summary['by_symbol']
        },
        'signals': {
            'total': confluence_summary['total_signals'],
            'long': confluence_summary['long_signals'],
            'short': confluence_summary['short_signals'],
            'data': signals_data
        },
        'timeframe_breakdown': timeframe_data
    })


@app.route('/api/chart/<symbol>/<timeframe>')
def get_chart(symbol, timeframe):
    """Get chart data for a symbol/timeframe."""
    # Get candles
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(days=7)  # Last 7 days

    candles = db_manager.get_candles(
        symbol=symbol,
        timeframe=timeframe,
        start_time=start_time,
        end_time=end_time
    )

    if not candles:
        return jsonify({'error': 'No data available'}), 404

    # Convert to DataFrame
    df = pd.DataFrame([{
        'timestamp': c.timestamp,
        'open': c.open,
        'high': c.high,
        'low': c.low,
        'close': c.close,
        'volume': c.volume
    } for c in candles])

    # Get patterns for this symbol/timeframe
    patterns = db_manager.get_valid_patterns(symbol=symbol, timeframe=timeframe)

    # Create candlestick chart
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.7, 0.3],
        subplot_titles=(f'{symbol} - {timeframe}', 'Volume')
    )

    # Add candlestick
    fig.add_trace(
        go.Candlestick(
            x=df['timestamp'],
            open=df['open'],
            high=df['high'],
            low=df['low'],
            close=df['close'],
            name='Price',
            increasing_line_color='#10b981',
            decreasing_line_color='#ef4444'
        ),
        row=1, col=1
    )

    # Add FVG boxes
    for pattern in patterns:
        if pattern.gap_top and pattern.gap_bottom:
            color = 'rgba(16, 185, 129, 0.2)' if pattern.direction == 'bullish' else 'rgba(239, 68, 68, 0.2)'
            border_color = '#10b981' if pattern.direction == 'bullish' else '#ef4444'

            # Add FVG rectangle
            fig.add_shape(
                type='rect',
                x0=pattern.start_timestamp,
                x1=end_time,  # Extend to current time
                y0=pattern.gap_bottom,
                y1=pattern.gap_top,
                fillcolor=color,
                line=dict(color=border_color, width=1, dash='dash'),
                row=1, col=1
            )

            # Add entry line
            fig.add_shape(
                type='line',
                x0=pattern.start_timestamp,
                x1=end_time,
                y0=pattern.entry_price,
                y1=pattern.entry_price,
                line=dict(color=border_color, width=2),
                row=1, col=1
            )

            # Add TP/SL lines
            fig.add_shape(
                type='line',
                x0=pattern.start_timestamp,
                x1=end_time,
                y0=pattern.take_profit,
                y1=pattern.take_profit,
                line=dict(color='green', width=1, dash='dot'),
                row=1, col=1
            )

            fig.add_shape(
                type='line',
                x0=pattern.start_timestamp,
                x1=end_time,
                y0=pattern.stop_loss,
                y1=pattern.stop_loss,
                line=dict(color='red', width=1, dash='dot'),
                row=1, col=1
            )

    # Add volume bars
    colors = ['#10b981' if close >= open else '#ef4444'
              for close, open in zip(df['close'], df['open'])]

    fig.add_trace(
        go.Bar(
            x=df['timestamp'],
            y=df['volume'],
            name='Volume',
            marker_color=colors,
            showlegend=False
        ),
        row=2, col=1
    )

    # Update layout
    fig.update_layout(
        template='plotly_dark',
        xaxis_rangeslider_visible=False,
        height=800,
        margin=dict(l=50, r=50, t=50, b=50),
        hovermode='x unified'
    )

    fig.update_xaxes(title_text='Time', row=2, col=1)
    fig.update_yaxes(title_text='Price', row=1, col=1)
    fig.update_yaxes(title_text='Volume', row=2, col=1)

    # Convert to JSON
    chart_json = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

    return jsonify({'chart': chart_json})


@app.route('/api/symbols')
def get_symbols():
    """Get list of configured symbols."""
    return jsonify({'symbols': settings.SYMBOLS})


@app.route('/api/timeframes')
def get_timeframes():
    """Get list of configured timeframes."""
    return jsonify({'timeframes': settings.TIMEFRAMES})


@app.route('/api/parameters/<symbol>/<timeframe>')
def get_parameters(symbol, timeframe):
    """Get parameters for a symbol/timeframe."""
    params = parameter_manager.get_parameters(symbol, timeframe)
    return jsonify(params.to_dict())


@app.route('/symbol/<symbol>')
def symbol_page(symbol):
    """Symbol detail page."""
    return render_template('symbol.html', symbol=symbol)


@app.route('/signals')
def signals_page():
    """Active signals page."""
    return render_template('signals.html')


@app.route('/parameters')
def parameters_page():
    """Parameter configuration page."""
    return render_template('parameters.html')


def main():
    """Run the Flask application."""
    print("\n" + "=" * 60)
    print("CryptoFlowScanner Web Dashboard")
    print("=" * 60)
    print(f"\nStarting server at http://{settings.WEB_HOST}:{settings.WEB_PORT}")
    print(f"Debug mode: {settings.WEB_DEBUG}")
    print("\nPress Ctrl+C to stop")
    print("=" * 60 + "\n")

    app.run(
        host=settings.WEB_HOST,
        port=settings.WEB_PORT,
        debug=settings.WEB_DEBUG
    )


if __name__ == '__main__':
    main()
