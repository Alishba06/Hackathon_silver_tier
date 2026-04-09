#!/usr/bin/env python3
"""
Quick LinkedIn Session Setup - No prompts, just opens browser.

Usage:
    python setup_linkedin.py
"""

import sys
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("Error: playwright not installed. Run: pip install playwright")
    print("Then run: playwright install chromium")
    sys.exit(1)


def main():
    vault_path = Path(__file__).parent.parent.resolve()
    session_path = vault_path / '.linkedin_session'
    
    print("=" * 60)
    print("LINKEDIN SESSION SETUP")
    print("=" * 60)
    print(f"\nSession will be saved to: {session_path}")
    print("\nINSTRUCTIONS:")
    print("1. A browser window will open with LinkedIn")
    print("2. Log in with your credentials")
    print("3. Complete any 2FA if enabled")
    print("4. Wait for your feed to load completely")
    print("5. Close the browser window when done")
    print("\n" + "=" * 60)
    print("\nOpening browser now...\n")
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch_persistent_context(
                session_path,
                headless=False,
                args=['--disable-blink-features=AutomationControlled']
            )
            
            page = browser.pages[0]
            page.goto('https://www.linkedin.com/', timeout=60000)
            
            print("✓ Browser opened. Log in to LinkedIn...")
            print("✓ Close the browser when your feed has loaded.")
            
            # Wait for browser to close (up to 10 minutes)
            try:
                page.wait_for_event('close', timeout=600000)
            except:
                print("\n⚠ Timeout reached. Closing browser...")
            
            browser.close()
        
        print("\n" + "=" * 60)
        print("✓ SESSION SAVED SUCCESSFULLY!")
        print(f"✓ Location: {session_path}")
        print("=" * 60)
        print("\nYou can now run the LinkedIn Watcher:")
        print(f"  python scripts/linkedin_watcher.py .")
        print("\nOr test it with:")
        print(f"  python scripts/linkedin_watcher.py . --once --visible")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n✗ Setup failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
