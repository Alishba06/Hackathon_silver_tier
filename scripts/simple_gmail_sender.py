#!/usr/bin/env python3
"""
Simple Gmail Email Sender - Uses direct Playwright code execution.

This version uses a simpler approach that directly checks if actions succeeded
by examining the page state, not parsing complex result formats.
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
        # Use base URL without /mcp for proper streamable HTTP
        self.base_url = url.rstrip('/')
        self._request_id = 0
        self._session_id = None
        self._initialized = False

    def _next_id(self):
        self._request_id += 1
        return self._request_id

    def _get_url(self):
        # For streamable HTTP, use /mcp endpoint
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
                "clientInfo": {"name": "simple-gmail-sender", "version": "1.0.0"}
            }
        }
        data = json.dumps(payload).encode('utf-8')
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            # Don't send session header on first request
        }
        req = Request(self._get_url(), data=data, headers=headers, method='POST')
        try:
            with urlopen(req, timeout=30) as resp:
                # CRITICAL: Extract session BEFORE reading body
                self._session_id = resp.headers.get('Mcp-Session-Id') or resp.headers.get('mcp-session-id')
                print(f"    [INIT] Session: {self._session_id[:8] if self._session_id else 'None'}...")
                # Read body but don't rely on it
                _ = resp.read()
        except HTTPError as e:
            # Even on error, check for session ID in headers
            if hasattr(e, 'headers') and e.headers:
                self._session_id = e.headers.get('Mcp-Session-Id') or e.headers.get('mcp-session-id')
            raise MCPClientError(f"HTTP {e.code}: {e.read().decode('utf-8') if e.fp else str(e)}")
        except URLError as e:
            raise MCPClientError(f"Connection failed: {e.reason}")
        self._initialized = True
        # Send initialized notification
        self._send_notification("notifications/initialized")

    def _send_notification(self, method):
        """Send notification without waiting for response."""
        payload = {"jsonrpc": "2.0", "method": method}
        data = json.dumps(payload).encode('utf-8')
        headers = {"Content-Type": "application/json"}
        if self._session_id:
            headers["mcp-session-id"] = self._session_id
            headers["Mcp-Session-Id"] = self._session_id
        try:
            req = Request(self._get_url(), data=data, headers=headers, method='POST')
            with urlopen(req, timeout=10) as resp:
                # Update session if changed
                new_session = resp.headers.get('Mcp-Session-Id') or resp.headers.get('mcp-session-id')
                if new_session:
                    self._session_id = new_session
        except:
            pass  # Notifications don't need response

    def _send_request(self, payload):
        data = json.dumps(payload).encode('utf-8')
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        if self._session_id:
            # Send BOTH header formats
            headers["mcp-session-id"] = self._session_id
            headers["Mcp-Session-Id"] = self._session_id
        
        req = Request(self._get_url(), data=data, headers=headers, method='POST')
        
        try:
            with urlopen(req, timeout=120) as resp:
                # CRITICAL: Extract session BEFORE reading body
                new_session_id = resp.headers.get('Mcp-Session-Id') or resp.headers.get('mcp-session-id')
                if new_session_id:
                    self._session_id = new_session_id
                
                body = resp.read().decode('utf-8')
                
                # Parse SSE format
                if 'data:' in body:
                    for line in body.split('\n'):
                        if line.strip().startswith('data:'):
                            json_str = line.strip()[5:]
                            if json_str and json_str != '[DONE]':
                                return json.loads(json_str)
                return json.loads(body) if body.strip() else {}
                
        except HTTPError as e:
            # Extract session from error response headers too
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


def get_snapshot_text(snapshot):
    content = snapshot.get('content', '')
    if isinstance(content, list):
        texts = [item.get('text', '') or item.get('name', '') for item in content if isinstance(item, dict)]
        return ' '.join(texts)
    return str(content)


def send_email(client, to, subject, body):
    """Send email using direct Playwright code."""
    
    print("=" * 60)
    print("Simple Gmail Sender")
    print("=" * 60)
    print(f"To: {to}")
    print(f"Subject: {subject}")
    print(f"Body: {body[:80]}{'...' if len(body) > 80 else ''}")
    print("=" * 60)

    # Step 1: Navigate
    print("\n[1/5] Navigating to Gmail...")
    client.navigate("https://mail.google.com/mail/u/0/")
    time.sleep(10)

    # Step 2: Wait for load
    print("[2/5] Waiting for Gmail to load...")
    for i in range(12):  # Wait up to 60 seconds
        snapshot = client.snapshot()
        text = get_snapshot_text(snapshot)
        if 'Compose' in text:
            print("    [OK] Gmail loaded (Compose button found)")
            break
        if 'Sign in' in text:
            print("    [WAIT] Login page - waiting for login...")
            time.sleep(10)
        else:
            print("    [WAIT] Loading...")
            time.sleep(5)
    else:
        raise MCPClientError("Gmail did not load properly")

    # Step 3: Open compose using keyboard shortcut (most reliable)
    print("[3/5] Opening compose window...")
    compose_open_code = """async (page) => {
        try {
            // Press Escape to ensure focus
            await page.keyboard.press('Escape');
            await page.waitForTimeout(500);
            
            // Press 'c' for compose (Gmail keyboard shortcut)
            await page.keyboard.press('c');
            await page.waitForTimeout(3000);
            
            // Check if compose window appeared
            const composeWindow = page.locator('div[aria-label="Message body"][contenteditable="true"]').first();
            const exists = await composeWindow.count() > 0;
            
            return { opened: exists, method: 'keyboard_c' };
        } catch (e) {
            return { opened: false, error: e.message };
        }
    }"""
    
    result = client.run_code(compose_open_code)
    print(f"    Compose result: {result}")
    
    # Wait and check if compose opened
    time.sleep(3)
    snapshot = client.snapshot()
    text = get_snapshot_text(snapshot)
    
    compose_opened = 'To' in text and 'Subject' in text
    if not compose_opened:
        print("    [WARN] Compose not detected after keyboard shortcut")
        print("    Trying alternative: Ctrl+Shift+C...")
        
        # Try alternative keyboard shortcut
        alt_code = """async (page) => {
            try {
                await page.keyboard.press('Control+Shift+c');
                await page.waitForTimeout(3000);
                const composeWindow = page.locator('div[aria-label="Message body"][contenteditable="true"]').first();
                return await composeWindow.count() > 0;
            } catch (e) {
                return false;
            }
        }"""
        client.run_code(alt_code)
        time.sleep(3)
        snapshot = client.snapshot()
        text = get_snapshot_text(snapshot)
        compose_opened = 'To' in text and 'Subject' in text
    
    if not compose_opened:
        print("[ERROR] Could not open Compose window")
        print("Page content:", text[:500])
        raise MCPClientError("Compose window not found")
    
    print("    [OK] Compose window opened")

    # Step 4: Fill fields
    print("[4/5] Filling email fields...")
    fill_code = f"""async (page) => {{
        try {{
            // Fill To field
            const toField = page.locator('[aria-label="To"], input[name="to"]').first();
            await toField.fill('{escape_js_string(to)}');
            await page.waitForTimeout(1000);
            
            // Fill Subject
            const subjectField = page.locator('[aria-label="Subject"], input[name="subjectbox"]').first();
            await subjectField.fill('{escape_js_string(subject)}');
            
            // Fill Body
            const bodyField = page.locator('div[aria-label="Message body"][contenteditable="true"]').first();
            await bodyField.click();
            await page.waitForTimeout(500);
            await bodyField.fill('{escape_js_string(body)}');
            
            return {{ success: true }};
        }} catch (e) {{
            return {{ success: false, error: e.message }};
        }}
    }}"""
    
    result = client.run_code(fill_code)
    print(f"    Fill result: {result}")
    time.sleep(2)

    # Step 5: Send using Ctrl+Enter
    print("[5/5] Sending email...")
    send_code = """async (page) => {
        try {
            // Focus body field first
            const bodyField = page.locator('div[aria-label="Message body"][contenteditable="true"]').first();
            await bodyField.click();
            await page.waitForTimeout(500);
            
            // Press Ctrl+Enter to send
            await page.keyboard.press('Control+Enter');
            await page.waitForTimeout(3000);
            
            // Check if compose window closed (indicates send)
            const composeExists = await bodyField.count() > 0;
            
            return { sent: !composeExists, method: 'ctrl+enter' };
        } catch (e) {
            return { sent: false, error: e.message };
        }
    }"""
    
    result = client.run_code(send_code)
    print(f"    Send result: {result}")
    
    # Verify
    time.sleep(3)
    snapshot = client.snapshot()
    text = get_snapshot_text(snapshot)
    
    if 'Undo' in text:
        print("\n[SUCCESS] Email sent! (Undo toast detected)")
    elif 'To' not in text and 'Subject' not in text:
        print("\n[SUCCESS] Email sent! (Compose window closed)")
    else:
        print("\n[WARN] Send status unclear - check Gmail Sent folder")
    
    print("\n" + "=" * 60)
    print("DONE")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description='Simple Gmail sender')
    parser.add_argument('to', help='Recipient email')
    parser.add_argument('subject', help='Subject')
    parser.add_argument('body', help='Body text')
    parser.add_argument('--mcp-url', '-u', default='http://localhost:8808')
    args = parser.parse_args()

    client = PlaywrightMCPClient(args.mcp_url)
    try:
        send_email(client, args.to, args.subject, args.body)
    except MCPClientError as e:
        print(f"\n[ERROR] {e}")
        sys.exit(1)
    finally:
        client.close()


if __name__ == "__main__":
    main()
