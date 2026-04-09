#!/usr/bin/env python3
"""
Email Sender - Sends emails via Gmail API
Uses existing OAuth credentials from gmail_watcher.py
"""

import argparse
import base64
import json
import sys
from email.mime.text import MIMEText
from pathlib import Path
from datetime import datetime

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


def get_gmail_service(vault_path: Path):
    """Initialize Gmail API service with OAuth"""
    token_path = vault_path / "token.json"
    credentials_path = vault_path / "credentials.json"
    
    creds = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(token_path)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            with open(token_path, "w") as f:
                f.write(creds.to_json())
        else:
            print("Error: No valid Gmail credentials found")
            print("Run: python scripts/gmail_watcher.py . --auth")
            sys.exit(1)
    
    return build("gmail", "v1", credentials=creds)


def send_email(service, to: str, subject: str, body: str, in_reply_to: str = None):
    """Send an email via Gmail API"""
    message = MIMEText(body)
    message["to"] = to
    message["from"] = "me"
    message["subject"] = subject
    
    if in_reply_to:
        message["In-Reply-To"] = in_reply_to
        message["References"] = in_reply_to
    
    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
    
    try:
        sent_message = service.users().messages().send(
            userId="me",
            body={"raw": raw_message}
        ).execute()
        print(f"[OK] Email sent successfully!")
        print(f"  Message ID: {sent_message['id']}")
        print(f"  Thread ID: {sent_message['threadId']}")
        return sent_message
    except HttpError as error:
        print(f"[ERROR] Error sending email: {error}")
        raise


def process_approved_email(vault_path: Path, approval_file: Path):
    """Process an approved email and send it"""
    # Read the approval file
    with open(approval_file, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Parse frontmatter (simple YAML-like parsing)
    lines = content.split("\n")
    frontmatter_end = 0
    for i, line in enumerate(lines):
        if line.strip() == "---" and i > 0:
            frontmatter_end = i
            break
    
    frontmatter = {}
    in_frontmatter = False
    for line in lines[1:frontmatter_end]:
        if ":" in line:
            key, value = line.split(":", 1)
            frontmatter[key.strip()] = value.strip()
    
    # Find the draft reply section
    draft_start = content.find("## Draft Reply")
    if draft_start == -1:
        print("[ERROR] No draft reply found in approval file")
        sys.exit(1)
    
    code_block_start = content.find("```", draft_start)
    code_block_end = content.find("```", code_block_start + 3)
    
    if code_block_start == -1 or code_block_end == -1:
        print("[ERROR] Draft reply not properly formatted")
        sys.exit(1)
    
    draft = content[code_block_start + 3:code_block_end].strip()
    
    # Parse draft headers
    to_email = frontmatter.get("from_email", "")
    subject = frontmatter.get("subject", "")
    if not subject.startswith("Re:"):
        subject = f"Re: {subject}"
    
    # Extract body from draft (skip headers like "To:", "Subject:")
    draft_lines = draft.split("\n")
    body_lines = []
    skip_headers = True
    for line in draft_lines:
        if skip_headers and (line.startswith("To:") or line.startswith("Subject:")):
            continue
        if skip_headers and line.strip() == "":
            continue
        skip_headers = False
        body_lines.append(line)
    
    body = "\n".join(body_lines)
    
    # Get Gmail service
    service = get_gmail_service(vault_path)
    
    # Send the email
    print(f"Sending email to: {to_email}")
    print(f"Subject: {subject}")
    print("---")
    send_email(service, to_email, subject, body, frontmatter.get("gmail_id"))
    
    # Move to Done folder
    done_path = vault_path / "Done" / approval_file.name
    approval_file.rename(done_path)
    print(f"[OK] Moved to Done/")


def main():
    parser = argparse.ArgumentParser(description="Send approved emails via Gmail API")
    parser.add_argument("vault_path", type=Path, help="Path to the AI Employee vault")
    parser.add_argument("approval_file", type=Path, nargs="?", help="Specific approval file to process")
    parser.add_argument("--all", action="store_true", help="Process all approved emails")
    
    args = parser.parse_args()
    
    vault_path = args.vault_path.resolve()
    approved_path = vault_path / "Approved"
    
    if args.approval_file:
        # Process specific file
        process_approved_email(vault_path, args.approval_file)
    elif args.all:
        # Process all approved emails
        if not approved_path.exists():
            print("No Approved folder found")
            return
        
        for approval_file in approved_path.glob("EMAIL_*.md"):
            print(f"\nProcessing: {approval_file.name}")
            try:
                process_approved_email(vault_path, approval_file)
            except Exception as e:
                print(f"✗ Error: {e}")
    else:
        print("Usage:")
        print(f"  python {sys.argv[0]} <vault_path> <approval_file>  # Send specific email")
        print(f"  python {sys.argv[0]} <vault_path> --all            # Send all approved emails")


if __name__ == "__main__":
    main()
