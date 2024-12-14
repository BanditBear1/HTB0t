import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from pytz import timezone
from logging_config import logger

def send_email_notification(subject: str, message: str):
    """Send an email notification."""
    try:
        smtp_server = os.getenv("SMTP_SERVER")
        smtp_port = int(os.getenv("SMTP_PORT"))
        smtp_username = os.getenv("SMTP_USERNAME")
        smtp_password = os.getenv("SMTP_PASSWORD")
        notification_email = os.getenv("NOTIFICATION_EMAIL")

        if not all([smtp_server, smtp_port, smtp_username, smtp_password, notification_email]):
            logger.error("Email configuration missing. Please check .env file.")
            return

        msg = MIMEMultipart()
        msg["From"] = smtp_username
        msg["To"] = notification_email
        msg["Subject"] = f"HTBot Alert: {subject}"

        # Add timestamp
        ny_time = datetime.now(timezone("America/New_York")).strftime("%Y-%m-%d %H:%M:%S %Z")
        body = f"Time: {ny_time}\n\n{message}"
        
        msg.attach(MIMEText(body, "plain"))

        # Connect to SMTP server
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(smtp_username, smtp_password)
        
        # Send email
        server.send_message(msg)
        server.quit()
        
        logger.info(f"Email notification sent: {subject}")
    except Exception as e:
        logger.error(f"Failed to send email notification: {str(e)}")

def format_trade_entry_message(trend: int, contracts: list, prices: dict) -> str:
    """Format trade entry notification message."""
    direction = "LONG" if trend == 1 else "SHORT"
    message = f"New Trade Entry - {direction} Position\n\n"
    
    for contract in contracts:
        price = prices.get(contract.id, "N/A")
        message += f"Contract: {contract.symbol} {contract.strike} {contract.right}\n"
        message += f"Action: {'BUY' if contract.id == contracts[1].id else 'SELL'}\n"
        message += f"Price: {price}\n\n"
    
    return message

def format_trade_exit_message(pnl: float, duration: str) -> str:
    """Format trade exit notification message."""
    return f"Trade Exit\n\nP&L: ${pnl:.2f}\nTrade Duration: {duration}"
