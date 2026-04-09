#!/usr/bin/env python3
"""
Simple LinkedIn Poster - Posts content with human assistance.

This version:
1. Opens LinkedIn in a visible browser
2. You stay logged in normally
3. Script creates the post, you click "Post"

Usage:
    python simple_linkedin_poster.py --vault . --content "Your post content here"
    python simple_linkedin_poster.py --vault . --file path/to/approved_post.md
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


class SimpleLinkedInPoster:
    """Post to LinkedIn with browser visible for human oversight."""
    
    def __init__(self, vault_path: str):
        self.vault_path = Path(vault_path).resolve()
        self.session_path = self.vault_path / '.linkedin_session'
        self.logs_path = self.vault_path / 'Logs'
        self.approved_path = self.vault_path / 'Approved'
        self.done_path = self.vault_path / 'Done'
        
        # Ensure directories exist
        self.logs_path.mkdir(parents=True, exist_ok=True)
        
        self.logger = None
        self._setup_logging()
    
    def _setup_logging(self):
        import logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger('SimpleLinkedInPoster')
    
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
    
    def post(self, content: str, wait_for_manual_post: bool = True):
        """
        Open LinkedIn and prepare post.

        Args:
            content: The post content
            wait_for_manual_post: If True, wait for user to click Post button
        """
        print("\n" + "=" * 60)
        print("LINKEDIN POST HELPER")
        print("=" * 60)
        print(f"\nPost content ({len(content)} characters):")
        print("-" * 60)
        print(content[:500] + ("..." if len(content) > 500 else ""))
        print("-" * 60)

        try:
            with sync_playwright() as p:
                # Launch visible browser with slower args for stability
                self.logger.info("Launching browser...")
                browser = p.chromium.launch_persistent_context(
                    self.session_path,
                    headless=False,  # Always visible
                    slow_mo=1000,  # Slow down operations by 1000ms
                    timeout=60000,
                    args=[
                        '--disable-blink-features=AutomationControlled',
                        '--start-maximized',
                        '--disable-gpu'
                    ]
                )

                # Wait for browser to stabilize
                time.sleep(2)
                
                page = browser.pages[0] if browser.pages else browser.new_page()

                # Navigate to LinkedIn
                self.logger.info("Navigating to LinkedIn...")
                page.goto('https://www.linkedin.com/feed/', timeout=90000)
                
                print("\n✓ LinkedIn opened in browser")
                print("  Wait for page to load completely...")
                
                # Wait for feed to load
                try:
                    page.wait_for_selector('[data-testid="update-posts"]', timeout=15000)
                except PlaywrightTimeout:
                    print("  ⚠ Page might still be loading, continuing anyway...")
                
                print("\n" + "=" * 60)
                print("INSTRUCTIONS:")
                print("=" * 60)
                print("1. Click 'Start a post' button at the top of the feed")
                print("2. Copy the content shown above (Ctrl+C)")
                print("3. Paste it into the post composer (Ctrl+V)")
                print("4. Add any images/hashtags if needed")
                print("5. Click 'Post' when ready")
                print("\n" + "=" * 60)
                
                # Copy content to clipboard alternative - display it clearly
                print("\n📋 POST CONTENT (copy this):")
                print("=" * 60)
                print(content)
                print("=" * 60)
                
                if wait_for_manual_post:
                    print("\n⏳ Waiting for you to post manually...")
                    print("   Close the browser when you're done.")
                    
                    try:
                        page.wait_for_event('close', timeout=600000)  # 10 min
                    except:
                        print("\n⚠ Timeout - closing browser")
                
                browser.close()
                
                self._log_action('prepared', content)
                print("\n✓ Done! Content was prepared for posting.")
                
        except Exception as e:
            self.logger.error(f"Error: {e}")
            self._log_action('error', content, str(e))
            print(f"\n✗ Error: {e}")
            return False
        
        return True
    
    def post_from_file(self, filepath: Path) -> bool:
        """Post content from an approved markdown file."""
        if not filepath.exists():
            print(f"✗ File not found: {filepath}")
            return False
        
        print(f"\nReading post from: {filepath.name}")
        content = self._parse_markdown_file(filepath)
        
        if not content:
            print("✗ No content found in file")
            return False
        
        success = self.post(content)
        
        if success:
            # Move file to Done
            dest = self.done_path / filepath.name
            self.done_path.mkdir(parents=True, exist_ok=True)
            filepath.rename(dest)
            print(f"\n✓ Moved file to: {dest}")
        
        return success


def main():
    parser = argparse.ArgumentParser(
        description='Simple LinkedIn Poster - Human-assisted posting',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Post custom content
  python simple_linkedin_poster.py --vault . --content "Excited to share..."
  
  # Post from approved file
  python simple_linkedin_poster.py --vault . --file Approved/LINKEDIN_POST_20260228.md
  
  # Just open LinkedIn (no content)
  python simple_linkedin_poster.py --vault . --open-only
        '''
    )
    
    parser.add_argument('--vault', required=True, help='Path to vault')
    parser.add_argument('--content', help='Post content directly')
    parser.add_argument('--file', help='Path to markdown file with post')
    parser.add_argument('--open-only', action='store_true', help='Just open LinkedIn')
    
    args = parser.parse_args()
    
    poster = SimpleLinkedInPoster(args.vault)
    
    if args.open_only:
        # Just open LinkedIn
        print("\nOpening LinkedIn...")
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
        poster.post(args.content)
    
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
