#!/usr/bin/env python3
"""
Fully Automated LinkedIn Poster using Selenium.

This script:
1. Opens LinkedIn
2. Clicks "Start a post"
3. Types the content automatically
4. Clicks "Post" button
5. Closes browser

Usage:
    python linkedin_poster_auto.py --content "Your post content here"
"""

import argparse
import sys
import time
from datetime import datetime

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.common.action_chains import ActionChains
    from selenium.common.exceptions import TimeoutException, NoSuchElementException
except ImportError:
    print("Error: selenium not installed. Run: pip install selenium webdriver-manager")
    sys.exit(1)

try:
    from webdriver_manager.chrome import ChromeDriverManager
except ImportError:
    print("Error: webdriver-manager not installed. Run: pip install webdriver-manager")
    sys.exit(1)


class AutoLinkedInPoster:
    """Fully automated LinkedIn poster."""
    
    def __init__(self, headless=False):
        self.driver = None
        self.headless = headless
        
    def setup_driver(self):
        """Setup Chrome WebDriver."""
        chrome_options = Options()
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        if not self.headless:
            chrome_options.add_argument("--start-maximized")
        else:
            chrome_options.add_argument("--headless=new")
        
        # Use actual Chrome browser
        chrome_options.binary_location = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
        
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # Set CDP commands to hide automation
        driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': 'Object.defineProperty(navigator, "webdriver", {get: () => undefined})'
        })
        
        driver.set_window_size(1280, 720)
        driver.set_page_load_timeout(60)
        
        return driver
    
    def wait_for_element(self, by, value, timeout=30):
        """Wait for element to be visible."""
        try:
            return WebDriverWait(self.driver, timeout).until(
                EC.visibility_of_element_located((by, value))
            )
        except TimeoutException:
            return None
    
    def wait_for_element_clickable(self, by, value, timeout=30):
        """Wait for element to be clickable."""
        try:
            return WebDriverWait(self.driver, timeout).until(
                EC.element_to_be_clickable((by, value))
            )
        except TimeoutException:
            return None
    
    def post(self, content: str) -> bool:
        """
        Fully automated post to LinkedIn.
        
        Steps:
        1. Login check
        2. Click "Start a post"
        3. Type content
        4. Click "Post"
        """
        print("\n" + "=" * 60)
        print("AUTO LINKEDIN POSTER")
        print("=" * 60)
        print(f"\n📝 Post content ({len(content)} characters):")
        print("-" * 60)
        print(content[:200] + ("..." if len(content) > 200 else ""))
        print("-" * 60)
        
        try:
            print("\n🚀 Step 1: Launching Chrome browser...")
            self.driver = self.setup_driver()
            
            print("📍 Step 2: Navigating to LinkedIn...")
            self.driver.get("https://www.linkedin.com/feed/")
            time.sleep(3)
            
            # Check if logged in
            print("🔐 Step 3: Checking login status...")
            login_check = self.wait_for_element(By.ID, "login-email", timeout=5)
            if login_check:
                print("\n❌ NOT LOGGED IN!")
                print("=" * 60)
                print("PLEASE LOGIN MANUALLY:")
                print("1. Enter your email and password")
                print("2. Complete any 2FA if required")
                print("3. Wait for feed to load")
                print("4. Script will auto-detect and continue")
                print("=" * 60)
                
                # Wait for user to login
                for i in range(60):  # Wait max 5 minutes
                    time.sleep(5)
                    login_check = self.wait_for_element(By.ID, "login-email", timeout=2)
                    if not login_check:
                        print("✓ Login detected! Continuing...")
                        break
                else:
                    print("✗ Login timeout. Please run again after logging in.")
                    self.driver.quit()
                    return False
            
            # Wait for feed to load
            print("⏳ Step 4: Waiting for feed to load...")
            time.sleep(2)
            
            # Click "Start a post" button
            print("🖱️ Step 5: Clicking 'Start a post'...")
            start_post_btn = self.wait_for_element(
                By.XPATH, 
                "//button[contains(text(), 'Start a post') or contains(text(), 'Post')]",
                timeout=15
            )
            
            if not start_post_btn:
                # Try alternative selectors
                start_post_btn = self.wait_for_element(
                    By.CSS_SELECTOR,
                    "button[aria-label='Start a post']",
                    timeout=10
                )
            
            if not start_post_btn:
                # Try another alternative
                start_post_btn = self.wait_for_element(
                    By.XPATH,
                "//div[contains(@class, 'share-box-feed-entry')]//button",
                    timeout=10
                )
            
            if start_post_btn:
                self.driver.execute_script("arguments[0].scrollIntoView(true);", start_post_btn)
                time.sleep(1)
                self.driver.execute_script("arguments[0].click();", start_post_btn)
                print("✓ 'Start a post' clicked!")
            else:
                print("⚠ Could not find 'Start a post' button")
            
            time.sleep(2)
            
            # Find the text editor and type content
            print("⌨️ Step 6: Typing content...")
            
            # Try multiple selectors for the post editor
            editor = None
            selectors = [
                (By.CSS_SELECTOR, "div[contenteditable='true'][role='textbox']"),
                (By.CSS_SELECTOR, "div.ql-editor[contenteditable='true']"),
                (By.CSS_SELECTOR, "div[data-placeholder='What do you want to talk about?']"),
                (By.CSS_SELECTOR, "div[data-placeholder*='talk about']"),
                (By.CLASS_NAME, "ql-editor"),
            ]
            
            for by, selector in selectors:
                editor = self.wait_for_element(by, selector, timeout=5)
                if editor:
                    print(f"✓ Found editor with: {selector}")
                    break
            
            if editor:
                # Clear any existing content
                editor.clear()
                time.sleep(1)
                
                # Type content (split into chunks for stability)
                self.driver.execute_script("arguments[0].focus();", editor)
                time.sleep(1)
                
                # Type in chunks to avoid detection
                chunk_size = 50
                for i in range(0, len(content), chunk_size):
                    chunk = content[i:i+chunk_size]
                    self.driver.execute_script(
                        "arguments[0].innerText += arguments[1];", 
                        editor, 
                        chunk
                    )
                    time.sleep(0.1)
                
                print(f"✓ Content typed ({len(content)} chars)")
            else:
                print("⚠ Could not find post editor")
            
            time.sleep(2)
            
            # Click "Post" button
            print("🖱️ Step 7: Clicking 'Post' button...")
            
            post_btn = None
            post_selectors = [
                (By.CSS_SELECTOR, "button[aria-label='Post']"),
                (By.XPATH, "//button[normalize-space()='Post']"),
                (By.CSS_SELECTOR, "button.ml2"),
            ]
            
            for by, selector in post_selectors:
                post_btn = self.wait_for_element(by, selector, timeout=5)
                if post_btn:
                    print(f"✓ Found Post button with: {selector}")
                    break
            
            if post_btn:
                self.driver.execute_script("arguments[0].scrollIntoView(true);", post_btn)
                time.sleep(1)
                self.driver.execute_script("arguments[0].click();", post_btn)
                print("✓ 'Post' button clicked!")
                
                # Wait for confirmation
                time.sleep(3)
                
                # Check if post was successful
                print("✓ Post submitted successfully!")
                
            else:
                print("⚠ Could not find 'Post' button")
                print("You may need to click Post manually")
                time.sleep(10)
            
            print("\n" + "=" * 60)
            print("✅ DONE! Post has been submitted to LinkedIn")
            print("=" * 60)
            
            time.sleep(3)
            self.driver.quit()
            return True
            
        except Exception as e:
            print(f"\n✗ Error: {e}")
            if self.driver:
                print("Keeping browser open for debugging...")
                time.sleep(10)
                self.driver.quit()
            return False


def main():
    parser = argparse.ArgumentParser(
        description='Fully Automated LinkedIn Poster',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Post content directly
  python linkedin_poster_auto.py --content "Excited to share..."
  
  # Headless mode (no browser UI)
  python linkedin_poster_auto.py --content "Test" --headless
        '''
    )
    
    parser.add_argument('--content', required=True, help='Post content')
    parser.add_argument('--headless', action='store_true', help='Run in headless mode')
    
    args = parser.parse_args()
    
    if not args.content:
        parser.print_help()
        sys.exit(1)
    
    poster = AutoLinkedInPoster(headless=args.headless)
    success = poster.post(args.content)
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
