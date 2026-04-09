#!/usr/bin/env python3
"""
Gmail Sender with IFRAME Support

This version handles Gmail's iframe-based structure properly.
"""

import argparse
import json
import sys
import io
import time
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')


class MCPClientError(Exception):
    pass


class PlaywrightMCPClient:
    def __init__(self, url="http://localhost:8808"):
        self.base_url = url.rstrip('/')
        self._request_id = 0
        self._session_id = None
        self._initialized = False

    def _next_id(self):
        self._request_id += 1
        return self._request_id

    def _get_url(self):
        return self.base_url + '/mcp'

    def _ensure_initialized(self):
        if self._initialized:
            return
        payload = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "iframe-gmail-sender", "version": "1.0.0"}
            }
        }
        data = json.dumps(payload).encode('utf-8')
        headers = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}
        req = Request(self._get_url(), data=data, headers=headers, method='POST')
        try:
            with urlopen(req, timeout=30) as resp:
                self._session_id = resp.headers.get('Mcp-Session-Id') or resp.headers.get('mcp-session-id')
                print(f"    [INIT] Session: {self._session_id[:8] if self._session_id else 'None'}...")
                _ = resp.read()
        except HTTPError as e:
            if hasattr(e, 'headers') and e.headers:
                self._session_id = e.headers.get('Mcp-Session-Id') or e.headers.get('mcp-session-id')
            raise MCPClientError(f"HTTP {e.code}: {e.read().decode('utf-8') if e.fp else str(e)}")
        except URLError as e:
            raise MCPClientError(f"Connection failed: {e.reason}")
        self._initialized = True
        self._send_notification("notifications/initialized")

    def _send_notification(self, method):
        payload = {"jsonrpc": "2.0", "method": method}
        data = json.dumps(payload).encode('utf-8')
        headers = {"Content-Type": "application/json"}
        if self._session_id:
            headers["mcp-session-id"] = self._session_id
            headers["Mcp-Session-Id"] = self._session_id
        try:
            req = Request(self._get_url(), data=data, headers=headers, method='POST')
            with urlopen(req, timeout=10) as resp:
                new_session = resp.headers.get('Mcp-Session-Id') or resp.headers.get('mcp-session-id')
                if new_session:
                    self._session_id = new_session
        except:
            pass

    def _send_request(self, payload):
        data = json.dumps(payload).encode('utf-8')
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        if self._session_id:
            headers["mcp-session-id"] = self._session_id
            headers["Mcp-Session-Id"] = self._session_id
        
        req = Request(self._get_url(), data=data, headers=headers, method='POST')
        
        try:
            with urlopen(req, timeout=120) as resp:
                new_session_id = resp.headers.get('Mcp-Session-Id') or resp.headers.get('mcp-session-id')
                if new_session_id:
                    self._session_id = new_session_id
                body = resp.read().decode('utf-8')
                if 'data:' in body:
                    for line in body.split('\n'):
                        if line.strip().startswith('data:'):
                            json_str = line.strip()[5:]
                            if json_str and json_str != '[DONE]':
                                return json.loads(json_str)
                return json.loads(body) if body.strip() else {}
        except HTTPError as e:
            if hasattr(e, 'headers') and e.headers:
                new_session = e.headers.get('Mcp-Session-Id') or e.headers.get('mcp-session-id')
                if new_session:
                    self._session_id = new_session
            body = e.read().decode('utf-8') if e.fp else str(e)
            if e.code == 404 and 'session' in body.lower():
                print("    [WARN] Session expired, reinitializing...")
                self._initialized = False
                self._ensure_initialized()
                return self._send_request(payload)
            raise MCPClientError(f"HTTP {e.code}: {body}")
        except URLError as e:
            raise MCPClientError(f"Connection failed: {e.reason}")

    def call_tool(self, name, args=None):
        self._ensure_initialized()
        payload = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "tools/call",
            "params": {"name": name}
        }
        if args:
            payload["params"]["arguments"] = args
        result = self._send_request(payload)
        if "error" in result:
            raise MCPClientError(f"MCP error: {result['error'].get('message')}")
        return result.get("result", {})

    def navigate(self, url):
        return self.call_tool("browser_navigate", {"url": url})

    def snapshot(self):
        return self.call_tool("browser_snapshot", {})

    def run_code(self, code):
        return self.call_tool("browser_run_code", {"code": code})

    def close(self):
        try:
            self.call_tool("browser_close", {})
        except:
            pass


def escape_js_string(s):
    return s.replace('\\', '\\\\').replace("'", "\\'").replace('"', '\\"').replace('\n', '\\n')


def send_email(client, to, subject, body):
    """Send email using Playwright with proper iframe handling."""
    
    print("=" * 60)
    print("Gmail Sender (IFrame Support)")
    print("=" * 60)
    print(f"To: {to}")
    print(f"Subject: {subject}")
    print(f"Body: {body[:80]}{'...' if len(body) > 80 else ''}")
    print("=" * 60)

    # Step 1: Navigate
    print("\n[1/6] Navigating to Gmail...")
    client.navigate("https://mail.google.com/mail/u/0/")
    time.sleep(10)

    # Step 2: Wait for load
    print("[2/6] Waiting for Gmail to load...")
    loaded = False
    for i in range(12):
        snapshot = client.snapshot()
        content = snapshot.get('content', '')
        text = str(content)
        if 'Compose' in text:
            print("    [OK] Gmail loaded (Compose found)")
            loaded = True
            break
        if 'Sign in' in text:
            print("    [WAIT] Login page detected...")
            time.sleep(10)
        else:
            print("    [WAIT] Loading...")
            time.sleep(5)
    
    if not loaded:
        raise MCPClientError("Gmail did not load")

    # Step 3: Open compose using DIRECT Playwright action (bypasses iframe issues)
    print("[3/6] Opening compose window...")
    
    # Use browser_run_code with proper frame handling
    compose_code = """async (page) => {
        const results = { success: false, method: null, error: null };
        
        try {
            // Wait for network to be idle
            await page.waitForLoadState('networkidle');
            await page.waitForTimeout(2000);
            
            // Strategy 1: Try to find and click Compose button
            const composeSelectors = [
                'a[title="Compose"]',
                'div[role="button"]:has-text("Compose")',
                'button:has-text("Compose")',
                '[data-tooltip*="Compose"]'
            ];
            
            for (const selector of composeSelectors) {
                try {
                    const btn = page.locator(selector).first();
                    const count = await btn.count();
                    if (count > 0) {
                        const visible = await btn.isVisible();
                        if (visible) {
                            await btn.click();
                            await page.waitForTimeout(3000);
                            results.success = true;
                            results.method = 'click:' + selector;
                            return results;
                        }
                    }
                } catch (e) {
                    // Try next selector
                }
            }
            
            // Strategy 2: Keyboard shortcut 'c'
            try {
                await page.keyboard.press('Escape');
                await page.waitForTimeout(500);
                await page.keyboard.press('c');
                await page.waitForTimeout(3000);
                
                // Check if compose appeared
                const composeWindow = page.locator('div[aria-label="Message body"][contenteditable="true"]').first();
                if (await composeWindow.count() > 0) {
                    results.success = true;
                    results.method = 'keyboard_c';
                    return results;
                }
            } catch (e) {}
            
            // Strategy 3: Use Gmail's internal JS
            try {
                await page.evaluate(() => {
                    const composeBtn = document.querySelector('div[jsname="C228mb"]');
                    if (composeBtn) {
                        composeBtn.click();
                    }
                });
                await page.waitForTimeout(3000);
                results.success = true;
                results.method = 'js_eval';
                return results;
            } catch (e) {}
            
            results.error = 'All strategies failed';
            return results;
            
        } catch (error) {
            results.error = error.message;
            return results;
        }
    }"""
    
    result = client.run_code(compose_code)
    print(f"    Compose result: {result}")
    time.sleep(3)

    # Check if compose opened
    snapshot = client.snapshot()
    text = str(snapshot.get('content', ''))
    
    compose_opened = ('To' in text and 'Subject' in text) or ('Message body' in text)
    if not compose_opened:
        print("    [WARN] Compose not detected, trying direct approach...")
        
        # Direct approach: Just try to fill fields anyway
        print("    Attempting to fill fields directly...")

    # Step 4: Fill fields
    print("[4/6] Filling email fields...")
    
    fill_code = f"""async (page) => {{
        const results = {{ to: false, subject: false, body: false }};
        
        try {{
            // Wait for elements
            await page.waitForTimeout(2000);
            
            // Fill To - try multiple selectors
            const toSelectors = ['[aria-label="To"]', 'input[name="to"]', 'textarea[name="to"]'];
            for (const sel of toSelectors) {{
                try {{
                    const field = page.locator(sel).first();
                    if (await field.count() > 0) {{
                        await field.fill('{escape_js_string(to)}');
                        results.to = true;
                        break;
                    }}
                }} catch (e) {{}}
            }}
            await page.waitForTimeout(1000);
            
            // Fill Subject
            const subjectSelectors = ['[aria-label="Subject"]', 'input[name="subjectbox"]'];
            for (const sel of subjectSelectors) {{
                try {{
                    const field = page.locator(sel).first();
                    if (await field.count() > 0) {{
                        await field.fill('{escape_js_string(subject)}');
                        results.subject = true;
                        break;
                    }}
                }} catch (e) {{}}
            }}
            
            // Fill Body
            const bodySelectors = ['div[aria-label="Message body"][contenteditable="true"]', '[role="textbox"][aria-label*="body"]'];
            for (const sel of bodySelectors) {{
                try {{
                    const field = page.locator(sel).first();
                    if (await field.count() > 0) {{
                        await field.click();
                        await page.waitForTimeout(500);
                        await field.fill('{escape_js_string(body)}');
                        results.body = true;
                        break;
                    }}
                }} catch (e) {{}}
            }}
            
            return results;
        }} catch (e) {{
            return {{ ...results, error: e.message }};
        }}
    }}"""
    
    result = client.run_code(fill_code)
    print(f"    Fill result: {result}")
    time.sleep(2)

    # Step 5: Send
    print("[5/6] Sending email...")
    
    send_code = """async (page) => {
        try {
            // Focus body first
            const bodyField = page.locator('div[aria-label="Message body"][contenteditable="true"]').first();
            if (await bodyField.count() > 0) {
                await bodyField.click();
                await page.waitForTimeout(500);
            }
            
            // Try Ctrl+Enter
            await page.keyboard.press('Control+Enter');
            await page.waitForTimeout(3000);
            
            // Check if compose closed
            const stillExists = await bodyField.count() > 0;
            return { sent: !stillExists, method: 'ctrl+enter' };
        } catch (e) {
            return { sent: false, error: e.message };
        }
    }"""
    
    result = client.run_code(send_code)
    print(f"    Send result: {result}")
    time.sleep(3)

    # Step 6: Verify
    print("[6/6] Verifying...")
    snapshot = client.snapshot()
    text = str(snapshot.get('content', ''))
    
    if 'Undo' in text:
        print("\n[SUCCESS] Email sent! (Undo toast)")
    elif 'To' not in text and 'Subject' not in text:
        print("\n[SUCCESS] Email sent! (Compose closed)")
    else:
        print("\n[WARN] Status unclear - check Sent folder")
        print(f"    Page preview: {text[:300]}...")
    
    print("\n" + "=" * 60)
    print("DONE")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description='Gmail sender with iframe support')
    parser.add_argument('to', help='Recipient email')
    parser.add_argument('subject', help='Subject')
    parser.add_argument('body', help='Body text')
    parser.add_argument('--mcp-url', '-u', default='http://localhost:8808')
    args = parser.parse_args()

    # Remove space from email if present
    to_email = args.to.replace(' ', '')

    client = PlaywrightMCPClient(args.mcp_url)
    try:
        send_email(client, to_email, args.subject, args.body)
    except MCPClientError as e:
        print(f"\n[ERROR] {e}")
        sys.exit(1)
    finally:
        client.close()


if __name__ == "__main__":
    main()
