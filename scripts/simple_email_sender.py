#!/usr/bin/env python3
r"""
Simple Email Sender using SMTP.

No browser automation needed - sends email directly via Gmail SMTP.

Usage:
    python scripts\simple_email_sender.py "recipient@example.com" "Subject" "Body"

Setup (First Time):
    1. Enable 2-Factor Authentication on your Gmail account
    2. Generate an App Password: https://myaccount.google.com/apppasswords
    3. Create .env file with:
        GMAIL_USER=your_email@gmail.com
        GMAIL_PASSWORD=your_app_password
"""

import argparse
import smtplib
import sys
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

# Try to load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


class SimpleEmailSender:
    """Send emails via Gmail SMTP."""
    
    def __init__(self, email: str = None, password: str = None):
        self.email = email or os.getenv('GMAIL_USER')
        self.password = password or os.getenv('GMAIL_PASSWORD')
        self.smtp_server = 'smtp.gmail.com'
        self.smtp_port = 587
        
    def send(self, to: str, subject: str, body: str, html: bool = False) -> bool:
        """
        Send an email.
        
        Args:
            to: Recipient email address
            subject: Email subject
            body: Email body content
            html: If True, send as HTML email
            
        Returns:
            True if sent successfully, False otherwise
        """
        if not self.email or not self.password:
            print("\n❌ ERROR: Gmail credentials not found!")
            print("\nSetup Instructions:")
            print("=" * 60)
            print("1. Enable 2-Factor Authentication on your Gmail")
            print("2. Generate App Password:")
            print("   https://myaccount.google.com/apppasswords")
            print("3. Create .env file in project root with:")
            print("   GMAIL_USER=your_email@gmail.com")
            print("   GMAIL_PASSWORD=your_app_password")
            print("=" * 60)
            return False
        
        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.email
            msg['To'] = to
            msg['Subject'] = subject
            msg['Date'] = datetime.now().strftime('%a, %d %b %Y %H:%M:%S %z')
            
            # Attach body
            msg_type = 'html' if html else 'plain'
            msg.attach(MIMEText(body, msg_type, 'utf-8'))
            
            # Connect and send
            print("\n" + "=" * 60)
            print("SENDING EMAIL")
            print("=" * 60)
            print(f"From:    {self.email}")
            print(f"To:      {to}")
            print(f"Subject: {subject}")
            print(f"Body:    {body[:100]}{'...' if len(body) > 100 else ''}")
            print("-" * 60)
            
            print("\n📡 Connecting to Gmail SMTP server...")
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.ehlo()
            server.starttls()
            server.ehlo()
            
            print("🔐 Logging in...")
            server.login(self.email, self.password)
            
            print("📤 Sending email...")
            server.send_message(msg)
            
            print("✅ Email sent successfully!")
            
            server.quit()
            
            print("=" * 60)
            return True
            
        except smtplib.SMTPAuthenticationError:
            print("\n❌ Authentication failed!")
            print("   - Check your App Password")
            print("   - Make sure 2FA is enabled")
            return False
            
        except smtplib.SMTPConnectError:
            print("\n❌ Could not connect to Gmail SMTP server")
            print("   - Check your internet connection")
            return False
            
        except Exception as e:
            print(f"\n❌ Error: {e}")
            return False


def main():
    parser = argparse.ArgumentParser(
        description='Simple Email Sender via Gmail SMTP',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Send email
  python simple_email_sender.py "recipient@example.com" "Subject" "Body text"
  
  # With environment variables (create .env file first)
  GMAIL_USER=your_email@gmail.com
  GMAIL_PASSWORD=your_app_password
        '''
    )
    
    parser.add_argument('to', help='Recipient email address')
    parser.add_argument('subject', help='Email subject')
    parser.add_argument('body', help='Email body')
    parser.add_argument('--html', action='store_true', help='Send as HTML')
    parser.add_argument('--email', help='Sender Gmail address (or use GMAIL_USER env)')
    parser.add_argument('--password', help='App password (or use GMAIL_PASSWORD env)')
    
    args = parser.parse_args()
    
    sender = SimpleEmailSender(
        email=args.email,
        password=args.password
    )
    
    success = sender.send(args.to, args.subject, args.body, html=args.html)
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
