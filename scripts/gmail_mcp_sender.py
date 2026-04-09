#!/usr/bin/env python3
"""
Gmail SMTP Sender - Send emails via Gmail SMTP.
Simple and reliable email sending without browser automation.

Usage:
    python gmail_mcp_sender.py <to_email> <subject> <body>
    python gmail_mcp_sender.py --file <approval_file.md>
"""

import argparse
import os
import smtplib
import sys
from email.message import EmailMessage
from pathlib import Path

# Gmail SMTP configuration
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 465

# Sender credentials (from environment variables for security)
SENDER_EMAIL = os.environ.get("GMAIL_SENDER_EMAIL", "alishbainteligent46@gmail.com")
SENDER_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "")  # Use Gmail App Password


def send_email_via_smtp(to: str, subject: str, body: str) -> bool:
    """Send email via Gmail SMTP."""
    try:
        # Create email message
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = SENDER_EMAIL
        msg["To"] = to
        msg.set_content(body)

        # Connect to Gmail SMTP server and send
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as smtp:
            # Login (requires Gmail App Password, not regular password)
            if SENDER_PASSWORD:
                smtp.login(SENDER_EMAIL, SENDER_PASSWORD)
            # Send the message
            smtp.send_message(msg)

        return True

    except smtplib.SMTPAuthenticationError:
        print("[ERROR] SMTP Authentication failed. Check your Gmail App Password.")
        print("        Generate one at: https://myaccount.google.com/apppasswords")
        return False
    except smtplib.SMTPException as e:
        print(f"[ERROR] SMTP error: {e}")
        return False
    except Exception as e:
        print(f"[ERROR] Unexpected error: {e}")
        return False


def parse_approval_file(filepath: Path) -> tuple:
    """Parse approval file to extract email details."""
    to = "unknown@example.com"
    subject = "No subject"
    body = "No body"

    if not filepath.exists():
        print(f"Error: File not found: {filepath}")
        return to, subject, body

    try:
        content = filepath.read_text(encoding='utf-8')

        # Try to extract from YAML frontmatter
        if '---' in content:
            parts = content.split('---')
            if len(parts) >= 2:
                frontmatter = parts[1].strip()
                for line in frontmatter.split('\n'):
                    if ':' in line:
                        key, value = line.split(':', 1)
                        key = key.strip().lower()
                        value = value.strip()
                        if key == 'to' or key == 'recipient':
                            to = value
                        elif key == 'subject':
                            subject = value

        # Extract body from markdown content
        lines = content.split('\n')
        body_lines = []
        in_body = False
        for line in lines:
            if line.strip() == '---' and in_body:
                in_body = False
            elif line.strip() == '---' and not in_body:
                in_body = True
            elif in_body and line.strip():
                body_lines.append(line)

        if body_lines:
            body = '\n'.join(body_lines)

    except Exception as e:
        print(f"Warning: Could not parse file: {e}")

    return to, subject, body


def main():
    parser = argparse.ArgumentParser(
        description='Send emails via Gmail SMTP',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python gmail_mcp_sender.py user@example.com "Subject" "Body"
  python gmail_mcp_sender.py --file Approved/EMAIL_xxx.md

Environment Variables:
  GMAIL_SENDER_EMAIL   - Sender Gmail address (default: alishbainteligent46@gmail.com)
  GMAIL_APP_PASSWORD   - Gmail App Password (required for sending)

To get a Gmail App Password:
  1. Go to https://myaccount.google.com/apppasswords
  2. Select 'Mail' and your device
  3. Copy the generated 16-character password
  4. Set it as GMAIL_APP_PASSWORD environment variable
"""
    )
    parser.add_argument('to', nargs='?', help='Recipient email')
    parser.add_argument('subject', nargs='?', help='Subject')
    parser.add_argument('body', nargs='?', help='Body')
    parser.add_argument('--file', '-f', type=Path, help='Approval file (Markdown with YAML frontmatter)')
    parser.add_argument('--sender', '-s', type=str, default=None, help='Override sender email')

    args = parser.parse_args()

    # Determine sender email
    sender = args.sender if args.sender else SENDER_EMAIL

    # Get email content from arguments or file
    if args.file:
        to, subject, body = parse_approval_file(args.file)
    elif args.to and args.subject and args.body:
        to, subject, body = args.to, args.subject, args.body
    else:
        print("Error: Provide recipient/subject/body or --file")
        print("\nUsage:")
        print('  python gmail_mcp_sender.py user@example.com "Subject" "Body"')
        print("  python gmail_mcp_sender.py --file Approved/EMAIL_xxx.md")
        sys.exit(1)

    # Validate recipient
    if not to or to == "unknown@example.com":
        print("Error: Recipient email is empty or invalid")
        sys.exit(1)

    # Print email details
    print("=" * 50)
    print("Gmail SMTP Email Sender")
    print("=" * 50)
    print(f"From:    {sender}")
    print(f"To:      {to}")
    print(f"Subject: {subject}")
    print(f"Body:    {body[:100]}{'...' if len(body) > 100 else ''}")
    print("=" * 50)

    # Check if password is set
    password = os.environ.get("GMAIL_APP_PASSWORD", SENDER_PASSWORD)
    if not password:
        print("\n[WARNING] GMAIL_APP_PASSWORD not set!")
        print("Set it using:")
        print('  setx GMAIL_APP_PASSWORD "your-16-char-app-password"')
        print("\nOr create one at: https://myaccount.google.com/apppasswords")
        print("\n[!] Email NOT sent (no password)")
        sys.exit(1)

    # Send email
    print("\nSending email...")
    if send_email_via_smtp(to, subject, body):
        print("\n[✓] Email sent successfully!")
    else:
        print("\n[!] Failed to send email")
        sys.exit(1)


if __name__ == "__main__":
    main()
