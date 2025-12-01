"""
Email notification system for sending trading signals.
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List
from datetime import datetime

from src.data.models import Signal
from src.data.storage import db_manager
from src.config.settings import settings


class EmailNotifier:
    """Sends email notifications for trading signals."""

    def __init__(self):
        """Initialize email notifier."""
        self.smtp_host = settings.SMTP_HOST
        self.smtp_port = settings.SMTP_PORT
        self.smtp_user = settings.SMTP_USER
        self.smtp_password = settings.SMTP_PASSWORD
        self.notification_email = settings.NOTIFICATION_EMAIL
        self.enabled = settings.SEND_NOTIFICATIONS

    def send_signal_notification(self, signal: Signal) -> bool:
        """
        Send email notification for a trading signal.

        Args:
            signal: Signal object to notify about

        Returns:
            True if sent successfully, False otherwise
        """
        if not self.enabled:
            print("Notifications disabled in settings")
            return False

        if not all([self.smtp_user, self.smtp_password, self.notification_email]):
            print("Email settings not configured")
            return False

        try:
            # Create email content
            subject = self._create_subject(signal)
            body = self._create_body(signal)

            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.smtp_user
            msg['To'] = self.notification_email

            # Attach both plain text and HTML versions
            text_part = MIMEText(body, 'plain')
            html_part = MIMEText(self._create_html_body(signal), 'html')

            msg.attach(text_part)
            msg.attach(html_part)

            # Send email
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)

            print(f"✓ Notification sent for {signal.symbol} {signal.direction.upper()}")

            # Mark signal as notified
            db_manager.mark_signal_notified(signal.id)

            return True

        except Exception as e:
            print(f"Error sending notification: {e}")
            return False

    def send_batch_notifications(self, signals: List[Signal]) -> int:
        """
        Send notifications for multiple signals.

        Args:
            signals: List of Signal objects

        Returns:
            Number of successfully sent notifications
        """
        if not signals:
            return 0

        sent_count = 0

        for signal in signals:
            if self.send_signal_notification(signal):
                sent_count += 1

        return sent_count

    def send_daily_summary(self, signals: List[Signal], patterns_count: int) -> bool:
        """
        Send a daily summary email with all active signals.

        Args:
            signals: List of active signals
            patterns_count: Total number of patterns detected

        Returns:
            True if sent successfully
        """
        if not self.enabled:
            return False

        try:
            subject = f"CryptoFlowScanner Daily Summary - {datetime.now().strftime('%Y-%m-%d')}"
            body = self._create_summary_body(signals, patterns_count)

            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.smtp_user
            msg['To'] = self.notification_email

            text_part = MIMEText(body, 'plain')
            html_part = MIMEText(self._create_summary_html_body(signals, patterns_count), 'html')

            msg.attach(text_part)
            msg.attach(html_part)

            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)

            print(f"✓ Daily summary sent")
            return True

        except Exception as e:
            print(f"Error sending daily summary: {e}")
            return False

    def notify_unnotified_signals(self) -> int:
        """
        Find and send notifications for all unnotified signals.

        Returns:
            Number of notifications sent
        """
        unnotified = db_manager.get_unnotified_signals()

        if not unnotified:
            print("No new signals to notify")
            return 0

        print(f"Found {len(unnotified)} unnotified signals")

        return self.send_batch_notifications(unnotified)

    def _create_subject(self, signal: Signal) -> str:
        """Create email subject line."""
        direction_emoji = "🟢" if signal.direction == 'long' else "🔴"
        return f"{direction_emoji} {signal.symbol} {signal.direction.upper()} Signal - Confluence: {signal.confluence_count}"

    def _create_body(self, signal: Signal) -> str:
        """Create plain text email body."""
        risk_percent = abs(signal.entry_price - signal.stop_loss) / signal.entry_price * 100
        reward_percent = abs(signal.take_profit - signal.entry_price) / signal.entry_price * 100

        body = f"""
CryptoFlowScanner Trading Signal
{'=' * 50}

Symbol: {signal.symbol}
Direction: {signal.direction.upper()}
Primary Timeframe: {signal.primary_timeframe}
Confluence: {signal.confluence_count} timeframes

TRADE SETUP:
{'=' * 50}

Entry Price: {signal.entry_price:.8f}
Stop Loss:   {signal.stop_loss:.8f} ({risk_percent:.2f}% risk)
Take Profit: {signal.take_profit:.8f} ({reward_percent:.2f}% reward)

Risk/Reward Ratio: {signal.risk_reward_ratio:.2f}

POSITION SIZING:
{'=' * 50}

Recommended Position Size: {signal.position_size_percent}% of capital
Maximum Risk: {signal.risk_amount_percent}% of capital

INSTRUCTIONS:
{'=' * 50}

1. Place a LIMIT {signal.direction.upper()} order at: {signal.entry_price:.8f}
2. Set stop loss at: {signal.stop_loss:.8f}
3. Set take profit at: {signal.take_profit:.8f}
4. Position size: {signal.position_size_percent}% of your capital

IMPORTANT NOTES:
- This signal has confluence across {signal.confluence_count} timeframes
- Always use proper risk management
- Never risk more than {signal.risk_amount_percent}% of your capital
- This is not financial advice - trade at your own risk

Signal detected at: {signal.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}

{'=' * 50}
Generated by CryptoFlowScanner
"""
        return body

    def _create_html_body(self, signal: Signal) -> str:
        """Create HTML email body."""
        risk_percent = abs(signal.entry_price - signal.stop_loss) / signal.entry_price * 100
        reward_percent = abs(signal.take_profit - signal.entry_price) / signal.entry_price * 100

        direction_color = "#10b981" if signal.direction == 'long' else "#ef4444"
        direction_emoji = "🟢" if signal.direction == 'long' else "🔴"

        html = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: {direction_color}; color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }}
        .content {{ background: #f9fafb; padding: 20px; border: 1px solid #e5e7eb; }}
        .trade-setup {{ background: white; padding: 15px; margin: 10px 0; border-radius: 6px; border-left: 4px solid {direction_color}; }}
        .price-row {{ display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #e5e7eb; }}
        .label {{ font-weight: bold; }}
        .value {{ color: {direction_color}; font-family: monospace; }}
        .warning {{ background: #fef3c7; padding: 15px; margin: 10px 0; border-radius: 6px; border-left: 4px solid #f59e0b; }}
        .footer {{ text-align: center; padding: 20px; color: #6b7280; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{direction_emoji} {signal.symbol} {signal.direction.upper()} SIGNAL</h1>
            <p>Confluence: {signal.confluence_count} timeframes | Timeframe: {signal.primary_timeframe}</p>
        </div>

        <div class="content">
            <div class="trade-setup">
                <h3>Trade Setup</h3>
                <div class="price-row">
                    <span class="label">Entry Price:</span>
                    <span class="value">{signal.entry_price:.8f}</span>
                </div>
                <div class="price-row">
                    <span class="label">Stop Loss:</span>
                    <span class="value">{signal.stop_loss:.8f} ({risk_percent:.2f}% risk)</span>
                </div>
                <div class="price-row">
                    <span class="label">Take Profit:</span>
                    <span class="value">{signal.take_profit:.8f} ({reward_percent:.2f}% reward)</span>
                </div>
                <div class="price-row">
                    <span class="label">Risk/Reward:</span>
                    <span class="value">{signal.risk_reward_ratio:.2f}</span>
                </div>
            </div>

            <div class="trade-setup">
                <h3>Position Sizing</h3>
                <div class="price-row">
                    <span class="label">Position Size:</span>
                    <span class="value">{signal.position_size_percent}% of capital</span>
                </div>
                <div class="price-row">
                    <span class="label">Maximum Risk:</span>
                    <span class="value">{signal.risk_amount_percent}% of capital</span>
                </div>
            </div>

            <div class="trade-setup">
                <h3>Instructions</h3>
                <ol>
                    <li>Place a LIMIT {signal.direction.upper()} order at: <strong>{signal.entry_price:.8f}</strong></li>
                    <li>Set stop loss at: <strong>{signal.stop_loss:.8f}</strong></li>
                    <li>Set take profit at: <strong>{signal.take_profit:.8f}</strong></li>
                    <li>Position size: <strong>{signal.position_size_percent}%</strong> of your capital</li>
                </ol>
            </div>

            <div class="warning">
                <strong>⚠️ Important Notes:</strong>
                <ul>
                    <li>This signal has confluence across {signal.confluence_count} timeframes</li>
                    <li>Always use proper risk management</li>
                    <li>Never risk more than {signal.risk_amount_percent}% of your capital</li>
                    <li>This is not financial advice - trade at your own risk</li>
                </ul>
            </div>
        </div>

        <div class="footer">
            <p>Signal detected at: {signal.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
            <p>Generated by CryptoFlowScanner</p>
        </div>
    </div>
</body>
</html>
"""
        return html

    def _create_summary_body(self, signals: List[Signal], patterns_count: int) -> str:
        """Create plain text summary body."""
        long_signals = [s for s in signals if s.direction == 'long']
        short_signals = [s for s in signals if s.direction == 'short']

        body = f"""
CryptoFlowScanner Daily Summary
{'=' * 50}

Date: {datetime.now().strftime('%Y-%m-%d')}

OVERVIEW:
Total Active Signals: {len(signals)}
Long Signals: {len(long_signals)}
Short Signals: {len(short_signals)}
Total Patterns Detected: {patterns_count}

ACTIVE SIGNALS:
{'=' * 50}
"""

        for signal in signals:
            body += f"""
{signal.symbol} - {signal.direction.upper()}
  Entry: {signal.entry_price:.8f}
  SL: {signal.stop_loss:.8f}
  TP: {signal.take_profit:.8f}
  R:R: {signal.risk_reward_ratio:.2f}
  Confluence: {signal.confluence_count}
  Timeframe: {signal.primary_timeframe}

"""

        body += f"""
{'=' * 50}
Generated by CryptoFlowScanner
"""
        return body

    def _create_summary_html_body(self, signals: List[Signal], patterns_count: int) -> str:
        """Create HTML summary body."""
        long_signals = [s for s in signals if s.direction == 'long']
        short_signals = [s for s in signals if s.direction == 'short']

        signals_html = ""
        for signal in signals:
            color = "#10b981" if signal.direction == 'long' else "#ef4444"
            signals_html += f"""
            <div style="background: white; padding: 15px; margin: 10px 0; border-radius: 6px; border-left: 4px solid {color};">
                <h3>{signal.symbol} - {signal.direction.upper()}</h3>
                <p><strong>Entry:</strong> {signal.entry_price:.8f}</p>
                <p><strong>SL:</strong> {signal.stop_loss:.8f} | <strong>TP:</strong> {signal.take_profit:.8f}</p>
                <p><strong>R:R:</strong> {signal.risk_reward_ratio:.2f} | <strong>Confluence:</strong> {signal.confluence_count} | <strong>TF:</strong> {signal.primary_timeframe}</p>
            </div>
            """

        html = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: #3b82f6; color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }}
        .content {{ background: #f9fafb; padding: 20px; border: 1px solid #e5e7eb; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>CryptoFlowScanner Daily Summary</h1>
            <p>{datetime.now().strftime('%Y-%m-%d')}</p>
        </div>
        <div class="content">
            <div style="background: white; padding: 15px; margin: 10px 0; border-radius: 6px;">
                <h3>Overview</h3>
                <p><strong>Total Active Signals:</strong> {len(signals)}</p>
                <p><strong>Long Signals:</strong> {len(long_signals)} | <strong>Short Signals:</strong> {len(short_signals)}</p>
                <p><strong>Total Patterns Detected:</strong> {patterns_count}</p>
            </div>

            <h3>Active Signals</h3>
            {signals_html}
        </div>
    </div>
</body>
</html>
"""
        return html


# Global email notifier instance
email_notifier = EmailNotifier()
