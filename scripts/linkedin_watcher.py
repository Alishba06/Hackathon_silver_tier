"""
LinkedIn Watcher - Monitor LinkedIn for notifications and messages.

This watcher monitors LinkedIn for new notifications, connection requests,
and messages that might require attention (leads, opportunities, etc.).

Features:
- Monitors LinkedIn notifications via Playwright
- Detects keywords indicating business opportunities
- Creates action files in Needs_Action folder
- Tracks processed items to avoid duplicates
- Human-in-the-loop approval for posting

Usage:
    python linkedin_watcher.py /path/to/vault

Setup:
    1. Run: python linkedin_watcher.py /path/to/vault --setup
    2. Log in to LinkedIn manually in the browser
    3. Wait for feed to load completely
    4. Close browser when done
    5. Run: python linkedin_watcher.py /path/to/vault
"""

import os
import sys
import json
import time
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
except ImportError:
    print("Error: playwright not installed. Run: pip install playwright")
    print("Then run: playwright install chromium")
    sys.exit(1)

# Import base watcher
sys.path.insert(0, str(Path(__file__).parent))
from base_watcher import BaseWatcher

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


class LinkedInWatcher(BaseWatcher):
    """
    LinkedIn Watcher - Monitors LinkedIn for notifications and opportunities.
    
    Creates action files in Needs_Action folder for items requiring attention.
    """
    
    def __init__(self, vault_path: str, check_interval: int = 300,
                 headless: bool = True):
        """
        Initialize the LinkedIn watcher.
        
        Args:
            vault_path: Path to the Obsidian vault root
            check_interval: How often to check (in seconds, default: 300 = 5 min)
            headless: Run browser in headless mode
        """
        super().__init__(vault_path, check_interval)
        
        self.vault_path = Path(vault_path).resolve()
        self.session_path = self.vault_path / '.linkedin_session'
        self.processed_file = self.vault_path / '.linkedin_processed.json'
        self.headless = headless
        
        # Keywords for business opportunities
        self.opportunity_keywords = [
            'hiring', 'opportunity', 'project', 'freelance',
            'consulting', 'contract', 'position', 'role',
            'looking for', 'recommend', 'referral', 'collaboration',
            'partnership', 'client', 'lead', 'business'
        ]
        
        # Load processed items
        self._load_processed_ids()
    
    def _load_processed_ids(self):
        """Load set of already processed item IDs."""
        if self.processed_file.exists():
            try:
                with open(self.processed_file, 'r') as f:
                    data = json.load(f)
                    self.processed_ids = set(data.get('processed_ids', []))
                    if len(self.processed_ids) > 500:
                        self.processed_ids = set(list(self.processed_ids)[-500:])
            except:
                self.processed_ids = set()
        else:
            self.processed_ids = set()
    
    def _save_processed_ids(self):
        """Save processed item IDs to file."""
        ids_list = list(self.processed_ids)[-500:]
        with open(self.processed_file, 'w') as f:
            json.dump({'processed_ids': ids_list, 'updated': datetime.now().isoformat()}, f)
    
    def _check_keywords(self, text: str) -> List[str]:
        """Check if text contains opportunity keywords."""
        text_lower = text.lower()
        return [kw for kw in self.opportunity_keywords if kw in text_lower]
    
    def _get_priority(self, keywords: List[str], item_type: str) -> str:
        """Determine priority based on keywords and type."""
        if item_type == 'message':
            return 'high'
        if len(keywords) >= 2:
            return 'high'
        elif len(keywords) == 1:
            return 'medium'
        return 'low'
    
    def check_for_updates(self) -> list:
        """
        Check LinkedIn for new notifications and opportunities.
        
        Returns:
            List of new items requiring attention
        """
        items = []
        
        try:
            with sync_playwright() as p:
                # Launch browser with persistent context - use user-data-dir for better session
                browser = p.chromium.launch_persistent_context(
                    self.session_path,
                    headless=self.headless,
                    args=[
                        '--disable-blink-features=AutomationControlled',
                        '--disable-dev-shm-usage',
                        '--no-sandbox'
                    ],
                    ignore_default_args=['--enable-automation'],
                    channel='chrome'  # Use installed Chrome for better session support
                )
                
                page = browser.pages[0]

                # Navigate to LinkedIn feed
                self.logger.info("Navigating to LinkedIn...")
                page.goto('https://www.linkedin.com/feed/', timeout=90000)
                page.wait_for_timeout(5000)  # Extra wait for dynamic content

                # Check if logged in by looking at URL
                if 'login' in page.url or 'checkpoint' in page.url:
                    self.logger.error("Not logged in to LinkedIn. Run --setup first.")
                    browser.close()
                    return []

                # Get recent posts from feed
                try:
                    # Wait for feed content
                    page.wait_for_selector('div.feed-shared-update-v2, div.scaffold-layout__list', timeout=10000)
                    
                    # LinkedIn feed posts - multiple selector fallbacks
                    notification_elements = page.query_selector_all(
                        'div.feed-shared-update-v2'
                    )
                    
                    # Fallback: try alternative selector
                    if not notification_elements:
                        notification_elements = page.query_selector_all(
                            'div.scaffold-layout__list > div[id^="ember"]'
                        )

                    self.logger.info(f"Found {len(notification_elements)} feed items")

                    for notif in notification_elements[:15]:  # Check first 15
                        try:
                            # Get post text - try multiple selectors
                            text_elem = notif.query_selector('div.feed-shared-text-view')
                            if not text_elem:
                                text_elem = notif.query_selector('span.t-14')
                            if not text_elem:
                                text_elem = notif.query_selector('div.update-components-text')

                            if text_elem:
                                text = text_elem.inner_text()[:500]  # Limit text length

                                # Skip empty or very short texts
                                if len(text.strip()) < 20:
                                    continue

                                # Generate ID
                                item_id = f"feed_{hash(text) % 1000000}"

                                # Skip processed
                                if item_id in self.processed_ids:
                                    continue

                                # Check for keywords
                                keywords = self._check_keywords(text)

                                if keywords:
                                    # Determine type
                                    item_type = 'feed_post'
                                    if 'message' in text.lower():
                                        item_type = 'message'
                                    elif 'connection' in text.lower() or 'connected' in text.lower():
                                        item_type = 'connection'
                                    elif 'hiring' in text.lower() or 'job' in text.lower():
                                        item_type = 'job_posting'

                                    items.append({
                                        'id': item_id,
                                        'type': item_type,
                                        'text': text,
                                        'keywords': keywords,
                                        'priority': self._get_priority(keywords, item_type),
                                        'timestamp': datetime.now()
                                    })

                                    self.processed_ids.add(item_id)
                        except Exception as e:
                            self.logger.debug(f"Error processing feed item: {e}")
                            continue

                except Exception as e:
                    self.logger.debug(f"Error getting feed items: {e}")
                
                browser.close()
                
                if items:
                    self._save_processed_ids()
                    self.logger.info(f"Found {len(items)} relevant LinkedIn items")
                    
        except Exception as e:
            self.logger.error(f"Error checking LinkedIn: {e}")
        
        return items
    
    def create_action_file(self, item: dict) -> Path:
        """
        Create a .md action file for the LinkedIn item.
        
        Args:
            item: Item details dictionary
            
        Returns:
            Path to created file
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"LINKEDIN_{item['type']}_{timestamp}.md"
        filepath = self.needs_action / filename
        
        content = f'''---
type: linkedin
subtype: {item['type']}
received: {datetime.now().isoformat()}
priority: {item['priority']}
status: pending
keywords: {json.dumps(item['keywords'])}
---

# LinkedIn {item['type'].title()}

## Details
- **Type:** {item['type']}
- **Priority:** {item['priority']}
- **Keywords:** {', '.join(item['keywords'])}

## Content
{item['text']}

## Suggested Actions
- [ ] Review notification on LinkedIn
- [ ] Determine if action needed
- [ ] Respond or engage if appropriate
- [ ] Log business opportunity if relevant

## Links
- [View on LinkedIn](https://www.linkedin.com/notifications/)
'''
        
        filepath.write_text(content, encoding='utf-8')
        self.logger.info(f'Created action file: {filename}')
        return filepath


class LinkedInPoster:
    """
    LinkedIn Poster - Create and post content to LinkedIn.
    
    Requires human approval before posting.
    """
    
    def __init__(self, vault_path: str):
        self.vault_path = Path(vault_path).resolve()
        self.session_path = self.vault_path / '.linkedin_session'
        self.pending_approval = self.vault_path / 'Pending_Approval'
        self.logs = self.vault_path / 'Logs'
        
        # Ensure directories exist
        self.pending_approval.mkdir(parents=True, exist_ok=True)
        self.logs.mkdir(parents=True, exist_ok=True)
        
        self.logger = logging.getLogger('LinkedInPoster')
    
    def create_post_draft(self, content: str, schedule_time: str = None) -> Path:
        """
        Create a draft post for approval.
        
        Args:
            content: Post content
            schedule_time: Optional scheduled time
            
        Returns:
            Path to draft file
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"LINKEDIN_POST_{timestamp}.md"
        filepath = self.pending_approval / filename
        
        content_md = f'''---
type: approval_request
action: linkedin_post
content_preview: {content[:100]}...
created: {datetime.now().isoformat()}
status: pending
scheduled: {schedule_time if schedule_time else 'immediate'}
---

# LinkedIn Post - Approval Required

## Post Content
{content}

## Details
- **Created:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- **Scheduled:** {schedule_time if schedule_time else 'Immediate'}
- **Character Count:** {len(content)}

## To Approve
Move this file to `/Approved` folder to post.

## To Reject
Move this file to `/Rejected` folder with reason.

---
*Created by LinkedIn Poster - Silver Tier*
'''
        
        filepath.write_text(content_md, encoding='utf-8')
        self.logger.info(f'Created post draft: {filename}')
        return filepath
    
    def post_to_linkedin(self, content: str) -> bool:
        """
        Post content to LinkedIn.
        
        Args:
            content: Post content
            
        Returns:
            True if successful
        """
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch_persistent_context(
                    self.session_path,
                    headless=False,  # Keep visible for debugging
                    args=['--disable-blink-features=AutomationControlled']
                )
                
                page = browser.pages[0]
                
                # Navigate to LinkedIn
                self.logger.info("Navigating to LinkedIn...")
                page.goto('https://www.linkedin.com/feed/', timeout=60000)
                
                # Wait for page to load
                page.wait_for_selector('[data-testid="update-posts"]', timeout=15000)
                
                # Click "Start a post"
                self.logger.info("Clicking 'Start a post'...")
                start_post = page.wait_for_selector('button:has-text("Start a post")', timeout=10000)
                start_post.click()
                page.wait_for_timeout(2000)
                
                # Find text field and type content
                self.logger.info("Entering post content...")
                text_field = page.query_selector('[contenteditable="true"][role="textbox"]')
                
                if text_field:
                    text_field.click()
                    page.wait_for_timeout(500)
                    
                    # Type content
                    for char in content[:3000]:  # LinkedIn limit
                        text_field.type(char, delay=30)
                        if char == '\n':
                            page.wait_for_timeout(100)
                    
                    # Click "Post"
                    self.logger.info("Clicking 'Post'...")
                    post_button = page.query_selector('button:has-text("Post")')
                    
                    if post_button:
                        post_button.click()
                        page.wait_for_timeout(5000)
                        
                        self.logger.info("Post submitted successfully!")
                        self._log_post(content)
                        browser.close()
                        return True
                    else:
                        self.logger.error("'Post' button not found")
                else:
                    self.logger.error("Text field not found")
                
                browser.close()
                return False
                
        except Exception as e:
            self.logger.error(f"Error posting to LinkedIn: {e}")
            return False
    
    def _log_post(self, content: str):
        """Log posted content."""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'action': 'linkedin_post',
            'content_preview': content[:200],
            'status': 'posted'
        }
        
        log_file = self.logs / f'linkedin_{datetime.now().strftime("%Y%m%d")}.json'
        
        logs = []
        if log_file.exists():
            try:
                logs = json.loads(log_file.read_text())
            except:
                logs = []
        
        logs.append(log_entry)
        log_file.write_text(json.dumps(logs, indent=2))


def run_setup(vault_path: str):
    """Run LinkedIn session setup."""
    vault = Path(vault_path).resolve()
    session_path = vault / '.linkedin_session'
    
    print("LinkedIn Session Setup")
    print("=" * 40)
    print(f"Session will be saved to: {session_path}")
    print()
    print("Instructions:")
    print("1. A browser window will open with LinkedIn")
    print("2. Log in with your credentials")
    print("3. Complete any 2FA if enabled")
    print("4. Wait for your feed to load completely")
    print("5. Close the browser window when done")
    print()
    print("Starting browser in 3 seconds...")
    time.sleep(3)
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch_persistent_context(
                session_path,
                headless=False,
                args=['--disable-blink-features=AutomationControlled']
            )
            
            page = browser.pages[0]
            print("\nOpening LinkedIn...")
            page.goto('https://www.linkedin.com/', timeout=60000)
            
            print("\nWaiting for you to log in...")
            print("Close the browser when your feed has loaded.")
            
            try:
                page.wait_for_event('close', timeout=600000)  # 10 min timeout
            except:
                print("\nTimeout reached. Closing browser...")
            
            browser.close()
        
        print("\n✓ Session saved successfully!")
        print(f"✓ Session location: {session_path}")
        print()
        print("You can now run the LinkedIn Watcher:")
        print(f"  python linkedin_watcher.py {vault_path}")
        
    except Exception as e:
        print(f"\n✗ Setup failed: {e}")
        sys.exit(1)


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='LinkedIn Watcher - Monitor LinkedIn for opportunities',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  python linkedin_watcher.py /path/to/vault           # Start watching
  python linkedin_watcher.py /path/to/vault --setup   # Setup session
  python linkedin_watcher.py /path/to/vault --once    # Check once and exit
        '''
    )
    parser.add_argument('vault', help='Path to Obsidian vault')
    parser.add_argument('--setup', action='store_true', help='Run session setup')
    parser.add_argument('-i', '--interval', type=int, default=300,
                       help='Check interval in seconds (default: 300)')
    parser.add_argument('--once', action='store_true', help='Run once and exit')
    parser.add_argument('--visible', action='store_true', help='Run in visible mode')
    
    args = parser.parse_args()
    
    vault_path = Path(args.vault).resolve()
    
    if not vault_path.exists():
        print(f"Error: Vault path does not exist: {vault_path}")
        sys.exit(1)
    
    # Handle setup
    if args.setup:
        run_setup(str(vault_path))
        return
    
    # Check session exists
    session_path = vault_path / '.linkedin_session'
    if not session_path.exists():
        print(f"Warning: LinkedIn session not found")
        print("Run setup first: python linkedin_watcher.py <vault> --setup")
        print()
    
    print("LinkedIn Watcher - Silver Tier")
    print("=" * 40)
    print(f"Vault: {vault_path}")
    print(f"Interval: {args.interval}s")
    print(f"Mode: {'Visible' if args.visible else 'Headless'}")
    print()
    
    try:
        watcher = LinkedInWatcher(
            str(vault_path),
            check_interval=args.interval,
            headless=not args.visible
        )
        
        if args.once:
            # Run once
            print("Checking LinkedIn...")
            items = watcher.check_for_updates()
            print(f"Found {len(items)} relevant items")
            for item in items:
                filepath = watcher.create_action_file(item)
                print(f"  Created: {filepath.name}")
        else:
            # Run continuously
            print("Watching LinkedIn. Press Ctrl+C to stop.")
            print()
            watcher.run()
            
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
