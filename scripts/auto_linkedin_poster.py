#!/usr/bin/env python3
"""
Auto LinkedIn Poster - Fully automated posting to LinkedIn.

This version:
1. Opens LinkedIn in visible browser
2. Clicks "Start a post" automatically
3. Types the content
4. Clicks "Post" button
5. You just watch it happen (or intervene if needed)

Usage:
    python auto_linkedin_poster.py --vault . --content "Your post content here"
    python auto_linkedin_poster.py --vault . --file path/to/approved_post.md
"""

import argparse
import json
import sys
import time
from pathlib import Path
from datetime import datetime

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
except ImportError:
    print("Error: playwright not installed. Run: pip install playwright")
    print("Then run: playwright install chromium")
    sys.exit(1)


class AutoLinkedInPoster:
    """Automatically post to LinkedIn with browser visible for oversight."""
    
    def __init__(self, vault_path: str):
        self.vault_path = Path(vault_path).resolve()
        self.session_path = self.vault_path / '.linkedin_session'
        self.logs_path = self.vault_path / 'Logs'
        self.approved_path = self.vault_path / 'Approved'
        self.done_path = self.vault_path / 'Done'
        
        # Ensure directories exist
        self.logs_path.mkdir(parents=True, exist_ok=True)
        self.done_path.mkdir(parents=True, exist_ok=True)
        
        self.logger = None
        self._setup_logging()
    
    def _setup_logging(self):
        import logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger('AutoLinkedInPoster')
    
    def _log_action(self, status: str, content_preview: str, error: str = None):
        """Log posting action to JSON file."""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'action': 'linkedin_post',
            'status': status,
            'content_preview': content_preview[:200],
        }
        if error:
            log_entry['error'] = error
        
        log_file = self.logs_path / f'linkedin_{datetime.now().strftime("%Y%m%d")}.json'
        
        logs = []
        if log_file.exists():
            try:
                logs = json.loads(log_file.read_text())
            except:
                logs = []
        
        logs.append(log_entry)
        log_file.write_text(json.dumps(logs, indent=2))
    
    def _parse_markdown_file(self, filepath: Path) -> str:
        """Extract post content from markdown file."""
        content = filepath.read_text(encoding='utf-8')
        
        # Find content after "## Post Content" or "## Content"
        lines = content.split('\n')
        in_content = False
        post_lines = []
        
        for line in lines:
            if line.startswith('## Post Content') or line.startswith('## Content'):
                in_content = True
                continue
            if in_content:
                if line.startswith('##') and line.strip():
                    break
                post_lines.append(line)
        
        if post_lines:
            return '\n'.join(post_lines).strip()
        
        # Fallback: return everything after frontmatter
        if content.startswith('---'):
            parts = content.split('---', 2)
            if len(parts) >= 3:
                return parts[2].strip()
        
        return content.strip()
    
    def _wait_for_selector(self, page, selector: str, timeout: int = 10000, description: str = None):
        """Wait for a selector with better error messages."""
        try:
            element = page.wait_for_selector(selector, timeout=timeout)
            return element
        except PlaywrightTimeout:
            msg = f"Timeout waiting for: {description or selector}"
            self.logger.warning(msg)
            return None
    
    def post(self, content: str) -> bool:
        """
        Automatically post content to LinkedIn.
        
        Args:
            content: The post content
        
        Returns:
            True if successful
        """
        print("\n" + "=" * 60)
        print("AUTO LINKEDIN POSTER")
        print("=" * 60)
        print(f"\n📝 Post content ({len(content)} characters):")
        print("-" * 60)
        print(content)
        print("-" * 60)
        
        success = False
        
        try:
            with sync_playwright() as p:
                # Launch visible browser
                self.logger.info("Launching browser...")
                print("\n🌐 Launching browser...")
                browser = p.chromium.launch_persistent_context(
                    self.session_path,
                    headless=False,  # Always visible so you can see what's happening
                    args=[
                        '--disable-blink-features=AutomationControlled',
                        '--disable-dev-shm-usage',
                        '--no-sandbox'
                    ],
                    ignore_default_args=['--enable-automation']
                )
                
                page = browser.pages[0]
                
                # Navigate to LinkedIn
                self.logger.info("Navigating to LinkedIn...")
                print("🔗 Navigating to LinkedIn...")
                page.goto('https://www.linkedin.com/feed/', timeout=90000)
                
                # Wait longer for page to fully load
                print("⏳ Waiting for page to load...")
                page.wait_for_timeout(8000)  # Wait 8 seconds for dynamic content
                
                # Check if we're on feed page
                current_url = page.url
                if 'login' in current_url or 'checkpoint' in current_url:
                    print("\n❌ Not logged in! Please run setup first:")
                    print("   python scripts/setup_linkedin.py")
                    browser.close()
                    return False
                
                print("✓ LinkedIn feed loaded")
                
                # Step 1: Click "Start a post" button
                print("\n📍 Step 1: Clicking 'Start a post'...")
                self.logger.info("Looking for 'Start a post' button...")
                
                start_post_btn = self._wait_for_selector(
                    page, 
                    'button:has-text("Start a post")',
                    timeout=10000,
                    description="Start a post button"
                )
                
                if not start_post_btn:
                    # Try alternative selectors
                    start_post_btn = self._wait_for_selector(
                        page,
                        'button[data-testid="update-posts-create-post"]',
                        timeout=5000,
                        description="Alternative post button"
                    )
                
                if start_post_btn:
                    start_post_btn.click()
                    print("✓ Clicked 'Start a post'")
                    page.wait_for_timeout(3000)  # Wait for modal to open
                else:
                    print("❌ Could not find 'Start a post' button")
                    self.logger.error("Start a post button not found")
                    browser.close()
                    return False
                
                # Step 2: Find the text input field and type content
                print("\n📝 Step 2: Entering post content...")
                self.logger.info("Looking for text input field...")
                
                # LinkedIn uses a contenteditable div for the post composer
                text_field = self._wait_for_selector(
                    page,
                    '[contenteditable="true"][role="textbox"]',
                    timeout=10000,
                    description="Post text field"
                )
                
                if not text_field:
                    # Try alternative selectors
                    text_field = self._wait_for_selector(
                        page,
                        'div[aria-label*="post"]',
                        timeout=5000,
                        description="Alternative text field"
                    )
                
                if text_field:
                    # Click to focus
                    text_field.click()
                    page.wait_for_timeout(500)
                    
                    # Type content character by character (slower = more human-like)
                    print(f"   Typing {len(content)} characters...")
                    
                    # Split into lines for better handling
                    lines = content.split('\n')
                    for i, line in enumerate(lines):
                        # Type the line
                        for char in line:
                            text_field.type(char, delay=20 + (i * 2))  # Vary delay slightly
                        # Handle newlines
                        if i < len(lines) - 1:
                            text_field.type('Enter')
                            page.wait_for_timeout(150)
                    
                    print("✓ Content entered")
                    page.wait_for_timeout(2000)
                else:
                    print("❌ Could not find text input field")
                    self.logger.error("Text input field not found")
                    browser.close()
                    return False
                
                # Step 3: Click "Post" button
                print("\n🚀 Step 3: Posting...")
                self.logger.info("Looking for 'Post' button...")
                
                # Wait a bit for the Post button to become enabled
                page.wait_for_timeout(2000)
                
                post_btn = self._wait_for_selector(
                    page,
                    'button:has-text("Post")',
                    timeout=10000,
                    description="Post button"
                )
                
                if not post_btn:
                    # Try alternative selectors
                    post_btn = self._wait_for_selector(
                        page,
                        'button[data-testid*="post"]',
                        timeout=5000,
                        description="Alternative post button"
                    )
                
                if post_btn:
                    # Check if button is enabled
                    is_disabled = post_btn.get_attribute('disabled')
                    if is_disabled:
                        print("⚠ Post button is disabled, waiting...")
                        page.wait_for_timeout(5000)
                    
                    print("   Clicking 'Post' button...")
                    post_btn.click()
                    page.wait_for_timeout(5000)
                    
                    print("✓ Post submitted!")
                    success = True
                    self._log_action('success', content)
                else:
                    print("❌ Could not find 'Post' button")
                    self.logger.error("Post button not found")
                    self._log_action('failed', content, "Post button not found")
                
                # Wait a moment then close
                page.wait_for_timeout(2000)
                browser.close()
                
        except Exception as e:
            self.logger.error(f"Error: {e}")
            self._log_action('error', content, str(e))
            print(f"\n❌ Error: {e}")
            return False
        
        if success:
            print("\n" + "=" * 60)
            print("✅ SUCCESS! Your post has been published to LinkedIn")
            print("=" * 60)
        else:
            print("\n" + "=" * 60)
            print("⚠ Post was not completed. Check the messages above.")
            print("=" * 60)
        
        return success
    
    def post_from_file(self, filepath: Path) -> bool:
        """Post content from an approved markdown file."""
        if not filepath.exists():
            print(f"✗ File not found: {filepath}")
            return False
        
        print(f"\n📄 Reading post from: {filepath.name}")
        content = self._parse_markdown_file(filepath)
        
        if not content:
            print("✗ No content found in file")
            return False
        
        success = self.post(content)
        
        if success:
            # Move file to Done
            dest = self.done_path / filepath.name
            filepath.rename(dest)
            print(f"\n✓ Moved file to: {dest}")
        
        return success


def main():
    parser = argparse.ArgumentParser(
        description='Auto LinkedIn Poster - Fully automated posting',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Post custom content
  python auto_linkedin_poster.py --vault . --content "Excited to share..."
  
  # Post from approved file
  python auto_linkedin_poster.py --vault . --file Approved/LINKEDIN_POST_20260228.md
  
  # Just open LinkedIn (no posting)
  python auto_linkedin_poster.py --vault . --open-only
        '''
    )
    
    parser.add_argument('--vault', required=True, help='Path to vault')
    parser.add_argument('--content', help='Post content directly')
    parser.add_argument('--file', help='Path to markdown file with post')
    parser.add_argument('--open-only', action='store_true', help='Just open LinkedIn')
    
    args = parser.parse_args()
    
    poster = AutoLinkedInPoster(args.vault)
    
    if args.open_only:
        # Just open LinkedIn
        print("\n🌐 Opening LinkedIn...")
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch_persistent_context(
                    poster.session_path,
                    headless=False,
                    args=['--disable-blink-features=AutomationControlled']
                )
                page = browser.pages[0]
                page.goto('https://www.linkedin.com/feed/', timeout=60000)
                print("✓ LinkedIn opened. Close browser when done.")
                page.wait_for_event('close', timeout=600000)
                browser.close()
        except Exception as e:
            print(f"✗ Error: {e}")
            sys.exit(1)
    
    elif args.content:
        # Post custom content
        success = poster.post(args.content)
        sys.exit(0 if success else 1)
    
    elif args.file:
        # Post from file
        filepath = Path(args.file)
        if not filepath.is_absolute():
            filepath = poster.vault_path / filepath
        
        success = poster.post_from_file(filepath)
        sys.exit(0 if success else 1)
    
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()
