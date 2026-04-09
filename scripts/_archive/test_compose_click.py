#!/usr/bin/env python3
"""
Test Compose Click Directly

This script tests the compose button click with detailed output.
"""

import json
import sys
import io
import time
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')


class PlaywrightMCPClient:
    def __init__(self, url="http://localhost:8808/mcp"):
        self.base_url = url.rstrip('/')
        if not self.base_url.endswith('/mcp'):
            self.base_url = self.base_url + '/mcp'
        self._request_id = 0
        self._session_id = None
        self._initialized = False

    def _next_id(self):
        self._request_id += 1
        return self._request_id

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
                "clientInfo": {"name": "test-compose", "version": "1.0.0"}
            }
        }
        data = json.dumps(payload).encode('utf-8')
        headers = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}
        req = Request(self.base_url, data=data, headers=headers, method='POST')
        with urlopen(req, timeout=30) as resp:
            self._session_id = resp.headers.get('Mcp-Session-Id') or resp.headers.get('mcp-session-id')
            print(f"[INIT] Session: {self._session_id}")
            body = resp.read().decode('utf-8')
        self._initialized = True

    def _send_request(self, payload):
        data = json.dumps(payload).encode('utf-8')
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        if self._session_id:
            headers["mcp-session-id"] = self._session_id
            headers["Mcp-Session-Id"] = self._session_id
        req = Request(self.base_url, data=data, headers=headers, method='POST')
        try:
            with urlopen(req, timeout=120) as resp:
                new_session_id = resp.headers.get('Mcp-Session-Id') or resp.headers.get('mcp-session-id')
                if new_session_id:
                    self._session_id = new_session_id
                body = resp.read().decode('utf-8')
                print(f"    [RAW RESPONSE] Length: {len(body)}")
                print(f"    [RAW RESPONSE] First 500 chars: {body[:500]}")
                if 'data:' in body:
                    for line in body.split('\n'):
                        if line.strip().startswith('data:'):
                            return json.loads(line.strip()[5:])
                return json.loads(body) if body.strip() else {}
        except HTTPError as e:
            body = e.read().decode('utf-8') if e.fp else str(e)
            raise Exception(f"HTTP {e.code}: {body}")
        except URLError as e:
            raise Exception(f"Connection failed: {e.reason}")

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
        print(f"\n[TOOL] Calling {name}...")
        result = self._send_request(payload)
        print(f"    [RESULT] Keys: {list(result.keys()) if result else 'None'}")
        if "error" in result:
            raise Exception(f"MCP error: {result['error'].get('message')}")
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


def get_snapshot_text(snapshot):
    content = snapshot.get('content', '')
    if isinstance(content, list):
        texts = []
        for item in content:
            if isinstance(item, dict):
                texts.append(item.get('text', '') or item.get('name', '') or item.get('role', ''))
            elif isinstance(item, str):
                texts.append(item)
        return '\n'.join(texts)
    elif isinstance(content, str):
        return content
    return str(content)


print("=" * 70)
print("TEST: Compose Button Click")
print("=" * 70)

client = PlaywrightMCPClient()

try:
    # Navigate to Gmail
    print("\n[1] Navigating to Gmail...")
    client.navigate("https://mail.google.com/mail/u/0/")
    print("    Waiting 15 seconds...")
    time.sleep(15)

    # Check snapshot
    print("\n[2] Checking page state...")
    snapshot = client.snapshot()
    text = get_snapshot_text(snapshot)
    
    if 'Sign in' in text or 'sign in' in text.lower():
        print("    [INFO] Please log in to Gmail in the browser window")
        print("    Waiting 30 seconds for login...")
        time.sleep(30)
        snapshot = client.snapshot()
        text = get_snapshot_text(snapshot)
    
    if 'Compose' in text:
        print("    [OK] Compose button text found in snapshot")
    else:
        print("    [WARN] Compose button text NOT found")
        print(f"    Page content preview: {text[:500]}...")

    # Try to click compose
    print("\n[3] Attempting to click Compose...")
    
    compose_code = """async (page) => {
        const results = { success: false, method: 'none', error: null };
        try {
            await page.waitForLoadState('networkidle');
            await page.waitForTimeout(2000);
            
            // Strategy 1: getByLabel
            try {
                const composeBtn = page.getByLabel('Compose', { exact: true }).first();
                const isVisible = await composeBtn.isVisible();
                console.log('Compose visible:', isVisible);
                if (isVisible) {
                    await composeBtn.click();
                    await page.waitForTimeout(3000);
                    results.success = true;
                    results.method = 'getByLabel';
                    return results;
                }
            } catch (e1) {
                console.log('Strategy 1 error:', e1.message);
            }
            
            // Strategy 2: keyboard shortcut
            try {
                await page.keyboard.press('Escape');
                await page.waitForTimeout(500);
                await page.keyboard.press('c');
                await page.waitForTimeout(3000);
                const composeWindow = page.locator('div[aria-label="Message body"][contenteditable="true"]').first();
                const exists = await composeWindow.count() > 0;
                if (exists) {
                    results.success = true;
                    results.method = 'keyboard_c';
                    return results;
                }
            } catch (e3) {
                console.log('Strategy 2 error:', e3.message);
            }
            
            results.error = 'All strategies failed';
            return results;
        } catch (error) {
            results.error = error.message;
            return results;
        }
    }"""
    
    result = client.run_code(compose_code)
    print(f"\n[4] Raw result from run_code:")
    print(f"    Full result: {json.dumps(result, indent=2, default=str)}")
    
    # Check if compose opened
    print("\n[5] Checking if compose window opened...")
    time.sleep(3)
    snapshot = client.snapshot()
    text = get_snapshot_text(snapshot)
    
    if 'To' in text and 'Subject' in text:
        print("    [SUCCESS] Compose window is OPEN! (To and Subject fields detected)")
    else:
        print("    [WARN] Compose window not detected")
        print(f"    Content preview: {text[:500]}...")

    print("\n" + "=" * 70)
    print("TEST COMPLETE")
    print("=" * 70)
    
except Exception as e:
    print(f"\n[ERROR] {e}")
    import traceback
    traceback.print_exc()
finally:
    client.close()
