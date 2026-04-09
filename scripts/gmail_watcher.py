"""
Gmail Watcher - Monitor Gmail for new important emails.

This watcher continuously monitors your Gmail inbox for unread, important emails
and creates action files in the Needs_Action folder for Qwen Code to process.

Features:
- Monitors Gmail for unread, important emails
- Tracks processed emails to avoid duplicates
- Creates structured .md action files with email metadata
- Supports keyword-based priority filtering
- Automatic OAuth2 authentication with Gmail API

Usage:
    python gmail_watcher.py /path/to/vault

Setup:
    1. Ensure credentials.json exists in vault root
    2. Run: python gmail_watcher.py /path/to/vault --auth
    3. Complete OAuth flow in browser
    4. Run: python gmail_watcher.py /path/to/vault
"""

import os
import sys
import json
import time
import logging
import base64
from pathlib import Path
from datetime import datetime
from email import message_from_bytes
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Import base watcher
sys.path.insert(0, str(Path(__file__).parent))
from base_watcher import BaseWatcher

# Gmail API scopes
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly',
          'https://www.googleapis.com/auth/gmail.modify']

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


class GmailWatcher(BaseWatcher):
    """
    Gmail Watcher - Monitors Gmail for new important emails.
    
    Creates action files in Needs_Action folder for each new email.
    """
    
    def __init__(self, vault_path: str, credentials_path: str = None, 
                 check_interval: int = 120):
        """
        Initialize the Gmail watcher.
        
        Args:
            vault_path: Path to the Obsidian vault root
            credentials_path: Path to credentials.json (default: vault/credentials.json)
            check_interval: How often to check for new emails (in seconds)
        """
        super().__init__(vault_path, check_interval)
        
        self.vault_path = Path(vault_path).resolve()
        self.credentials_path = Path(credentials_path) if credentials_path else self.vault_path / 'credentials.json'
        self.token_path = self.vault_path / 'token.json'
        self.processed_file = self.vault_path / '.gmail_processed.json'
        
        # Keywords for priority detection
        self.high_priority_keywords = [
            'urgent', 'asap', 'invoice', 'payment', 'important',
            'deadline', 'emergency', 'critical', 'attention'
        ]
        
        # Load processed email IDs
        self._load_processed_ids()
        
        # Initialize Gmail service
        self.service = None
        self._authenticate()
    
    def _load_processed_ids(self):
        """Load set of already processed email IDs."""
        if self.processed_file.exists():
            try:
                with open(self.processed_file, 'r') as f:
                    data = json.load(f)
                    self.processed_ids = set(data.get('processed_ids', []))
                    # Keep only last 1000 IDs
                    if len(self.processed_ids) > 1000:
                        self.processed_ids = set(list(self.processed_ids)[-1000:])
            except (json.JSONDecodeError, IOError):
                self.processed_ids = set()
        else:
            self.processed_ids = set()
    
    def _save_processed_ids(self):
        """Save processed email IDs to file."""
        ids_list = list(self.processed_ids)[-1000:]
        with open(self.processed_file, 'w') as f:
            json.dump({'processed_ids': ids_list, 'updated': datetime.now().isoformat()}, f)
    
    def _authenticate(self):
        """Authenticate with Gmail API using OAuth2."""
        creds = None
        
        # Load existing token
        if self.token_path.exists():
            try:
                creds = Credentials.from_authorized_user_file(self.token_path, SCOPES)
                self.logger.info('Loaded existing OAuth token')
            except Exception as e:
                self.logger.warning(f'Failed to load token: {e}')
        
        # Refresh or get new credentials
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                    self.logger.info('Refreshed OAuth token')
                except Exception as e:
                    self.logger.warning(f'Failed to refresh token: {e}')
                    creds = None
            
            if not creds:
                if not self.credentials_path.exists():
                    self.logger.error(f'Credentials file not found: {self.credentials_path}')
                    self.logger.error('Please ensure credentials.json exists in vault root')
                    raise FileNotFoundError(f'Credentials not found: {self.credentials_path}')
                
                self.logger.info('Starting OAuth flow...')
                try:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_path, SCOPES)
                    creds = flow.run_local_server(port=0, open_browser=False)
                    
                    # Save credentials
                    with open(self.token_path, 'w') as f:
                        f.write(creds.to_json())
                    self.logger.info(f'OAuth token saved to: {self.token_path}')
                except Exception as e:
                    self.logger.error(f'OAuth flow failed: {e}')
                    self.logger.info('To authenticate, run: python gmail_watcher.py <vault> --auth')
                    raise
        
        # Build Gmail service
        try:
            self.service = build('gmail', 'v1', credentials=creds)
            self.logger.info('Gmail service initialized')
        except Exception as e:
            self.logger.error(f'Failed to build Gmail service: {e}')
            raise
    
    def _decode_snippet(self, snippet: str) -> str:
        """Decode Gmail snippet from base64."""
        try:
            # Gmail uses URL-safe base64 encoding
            return base64.urlsafe_b64decode(snippet + '==').decode('utf-8', errors='replace')
        except:
            return snippet
    
    def _get_email_details(self, msg_id: str) -> dict:
        """Get full email details."""
        try:
            message = self.service.users().messages().get(
                userId='me', id=msg_id, format='metadata',
                metadataHeaders=['From', 'To', 'Subject', 'Date']
            ).execute()
            
            headers = {h['name'].lower(): h['value'] for h in message['payload']['headers']}
            
            return {
                'id': msg_id,
                'from': headers.get('from', 'Unknown'),
                'to': headers.get('to', ''),
                'subject': headers.get('subject', 'No Subject'),
                'date': headers.get('date', ''),
                'snippet': self._decode_snippet(message.get('snippet', ''))
            }
        except Exception as e:
            self.logger.error(f'Failed to get email details: {e}')
            return None
    
    def _check_priority(self, email: dict) -> str:
        """Determine email priority based on keywords."""
        text = f"{email['subject']} {email['snippet']}".lower()
        
        matches = [kw for kw in self.high_priority_keywords if kw in text]
        
        if len(matches) >= 2:
            return 'high'
        elif len(matches) == 1:
            return 'medium'
        return 'low'
    
    def check_for_updates(self) -> list:
        """
        Check for new unread, important emails.
        
        Returns:
            List of new email details
        """
        if not self.service:
            self.logger.warning('Gmail service not available')
            return []
        
        try:
            # Search for unread emails
            results = self.service.users().messages().list(
                userId='me',
                q='is:unread',
                maxResults=20
            ).execute()
            
            messages = results.get('messages', [])
            new_emails = []
            
            for msg in messages:
                msg_id = msg['id']
                
                # Skip already processed
                if msg_id in self.processed_ids:
                    continue
                
                # Get email details
                email = self._get_email_details(msg_id)
                if email:
                    email['priority'] = self._check_priority(email)
                    new_emails.append(email)
                    self.processed_ids.add(msg_id)
            
            # Save processed IDs
            if new_emails:
                self._save_processed_ids()
                self.logger.info(f'Found {len(new_emails)} new emails')
            
            return new_emails
            
        except HttpError as e:
            if e.resp.status == 401:
                self.logger.warning('Authentication expired, re-authenticating...')
                try:
                    self._authenticate()
                except:
                    pass
            else:
                self.logger.error(f'Gmail API error: {e}')
            return []
        except Exception as e:
            self.logger.error(f'Error checking emails: {e}')
            return []
    
    def create_action_file(self, email: dict) -> Path:
        """
        Create a .md action file for the email.
        
        Args:
            email: Email details dictionary
            
        Returns:
            Path to created file
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"EMAIL_{email['id']}_{timestamp}.md"
        filepath = self.needs_action / filename
        
        # Extract sender email
        sender_email = email['from']
        if '<' in sender_email:
            sender_email = sender_email.split('<')[1].strip('>')
        
        content = f'''---
type: email
from: {email['from']}
from_email: {sender_email}
subject: {email['subject']}
received: {datetime.now().isoformat()}
priority: {email['priority']}
status: pending
gmail_id: {email['id']}
---

# Email: {email['subject']}

## Details
- **From:** {email['from']}
- **Received:** {email['date']}
- **Priority:** {email['priority']}

## Content
{email['snippet']}

## Suggested Actions
- [ ] Read full email in Gmail
- [ ] Determine required response
- [ ] Draft reply if needed
- [ ] Archive after processing

## Links
- [View in Gmail](https://mail.google.com/mail/u/0/#inbox/{email['id']})
'''
        
        filepath.write_text(content, encoding='utf-8')
        self.logger.info(f'Created action file: {filename}')
        return filepath
    
    def mark_as_read(self, email_id: str):
        """Mark email as read in Gmail."""
        if self.service:
            try:
                self.service.users().messages().modify(
                    userId='me', id=email_id, body={'removeLabelIds': ['UNREAD']}
                ).execute()
                self.logger.info(f'Marked email {email_id} as read')
            except Exception as e:
                self.logger.error(f'Failed to mark email as read: {e}')


def run_auth_flow(vault_path: str):
    """Run OAuth authentication flow."""
    vault = Path(vault_path).resolve()
    credentials_path = vault / 'credentials.json'
    token_path = vault / 'token.json'
    
    if not credentials_path.exists():
        print(f"Error: credentials.json not found at {credentials_path}")
        print("Please ensure your Google OAuth credentials file exists.")
        sys.exit(1)
    
    print("Gmail OAuth Authentication")
    print("=" * 40)
    print(f"Credentials: {credentials_path}")
    print(f"Token will be saved to: {token_path}")
    print()
    print("Opening browser for authentication...")
    print()
    
    try:
        flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
        creds = flow.run_local_server(port=0, open_browser=True)
        
        # Save token
        with open(token_path, 'w') as f:
            f.write(creds.to_json())
        
        print()
        print("✓ Authentication successful!")
        print(f"✓ Token saved to: {token_path}")
        print()
        print("You can now run the Gmail Watcher:")
        print(f"  python gmail_watcher.py {vault_path}")
        
    except Exception as e:
        print(f"✗ Authentication failed: {e}")
        sys.exit(1)


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Gmail Watcher - Monitor Gmail for new emails',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  python gmail_watcher.py /path/to/vault           # Start watching
  python gmail_watcher.py /path/to/vault --auth    # Run authentication
  python gmail_watcher.py /path/to/vault -i 60     # Check every 60 seconds
        '''
    )
    parser.add_argument('vault', help='Path to Obsidian vault')
    parser.add_argument('--auth', action='store_true', help='Run OAuth authentication')
    parser.add_argument('-i', '--interval', type=int, default=120, 
                       help='Check interval in seconds (default: 120)')
    parser.add_argument('--once', action='store_true', help='Run once and exit')
    
    args = parser.parse_args()
    
    vault_path = Path(args.vault).resolve()
    
    if not vault_path.exists():
        print(f"Error: Vault path does not exist: {vault_path}")
        sys.exit(1)
    
    # Handle authentication
    if args.auth:
        run_auth_flow(str(vault_path))
        return
    
    # Check credentials exist
    credentials_path = vault_path / 'credentials.json'
    if not credentials_path.exists():
        print(f"Error: credentials.json not found at {credentials_path}")
        print()
        print("To set up Gmail Watcher:")
        print("1. Create a Google Cloud project")
        print("2. Enable Gmail API")
        print("3. Create OAuth 2.0 credentials (Desktop app)")
        print("4. Download credentials.json to vault root")
        print("5. Run: python gmail_watcher.py <vault> --auth")
        sys.exit(1)
    
    print("Gmail Watcher - Silver Tier")
    print("=" * 40)
    print(f"Vault: {vault_path}")
    print(f"Interval: {args.interval}s")
    print(f"Credentials: {credentials_path}")
    print()
    
    try:
        watcher = GmailWatcher(str(vault_path), check_interval=args.interval)
        
        if args.once:
            # Run once
            print("Checking for new emails...")
            emails = watcher.check_for_updates()
            print(f"Found {len(emails)} new emails")
            for email in emails:
                filepath = watcher.create_action_file(email)
                print(f"  Created: {filepath.name}")
        else:
            # Run continuously
            print("Watching for new emails. Press Ctrl+C to stop.")
            print()
            watcher.run()
            
    except FileNotFoundError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
