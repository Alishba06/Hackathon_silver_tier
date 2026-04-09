#!/usr/bin/env python3
"""
Debug Compose Button Detection

This script helps debug why the Compose button is not being detected.
It shows the actual snapshot content and tries multiple detection methods.
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
                "clientInfo": {"name": "debug-compose", "version": "1.0.0"}
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
        result = self._send_request(payload)
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
    """Extract text from snapshot."""
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
print("DEBUG: Compose Button Detection")
print("=" * 70)

client = PlaywrightMCPClient()

try:
    # Step 1: Navigate to Gmail
    print("\n[1] Navigating to Gmail...")
    client.navigate("https://mail.google.com/mail/u/0/")
    print("    Waiting 15 seconds for Gmail to load...")
    time.sleep(15)

    # Step 2: Take snapshot
    print("\n[2] Taking snapshot...")
    snapshot = client.snapshot()
    
    # Step 3: Analyze snapshot format
    print("\n[3] Analyzing snapshot format...")
    content = snapshot.get('content', 'NO CONTENT')
    print(f"    Content type: {type(content)}")
    if isinstance(content, list):
        print(f"    Content length: {len(content)} items")
    else:
        print(f"    Content length: {len(str(content))} chars")

    # Step 4: Search for Compose
    print("\n[4] Searching for 'Compose' in snapshot...")
    snapshot_text = get_snapshot_text(snapshot)
    
    if 'Compose' in snapshot_text:
        print("    [FOUND] 'Compose' text detected in snapshot!")
        # Find lines with Compose
        lines = snapshot_text.split('\n')
        for i, line in enumerate(lines):
            if 'Compose' in line:
                print(f"         Line {i}: {line[:100]}")
    else:
        print("    [NOT FOUND] 'Compose' text not in snapshot")
        
    # Also check lowercase
    if 'compose' in snapshot_text.lower():
        print("    [FOUND] 'compose' (lowercase) detected!")
    else:
        print("    [NOT FOUND] 'compose' (lowercase) not in snapshot")

    # Step 5: Check for Sign In
    print("\n[5] Checking login status...")
    if 'Sign in' in snapshot_text or 'sign in' in snapshot_text.lower():
        print("    [INFO] Login page detected - user needs to log in")
    else:
        print("    [INFO] Not on login page")

    # Step 6: Try direct compose detection code
    print("\n[6] Running direct compose detection code...")
    detect_code = """async (page) => {
        const results = {
            composeFound: false,
            composeVisible: false,
            error: null,
            pageUrl: page.url(),
            selectors: {}
        };
        
        try {
            // Check URL
            results.pageUrl = page.url();
            
            // Try multiple selectors
            const selectors = [
                { name: 'getByLabel', selector: page.getByLabel('Compose', { exact: true }).first() },
                { name: 'role+text', selector: page.locator('div[role="button"]:has-text("Compose")').first() },
                { name: 'title', selector: page.locator('a[title="Compose"]').first() },
                { name: 'jsname', selector: page.locator('div[jsname="C228mb"]').first() }
            ];
            
            for (const { name, selector } of selectors) {
                try {
                    const exists = await selector.count() > 0;
                    const visible = exists ? await selector.isVisible() : false;
                    results.selectors[name] = { exists, visible };
                    if (visible) {
                        results.composeFound = true;
                        results.composeVisible = true;
                        results.foundWith = name;
                    }
                } catch (e) {
                    results.selectors[name] = { error: e.message };
                }
            }
            
        } catch (error) {
            results.error = error.message;
        }
        
        return results;
    }"""
    
    result = client.run_code(detect_code)
    print(f"    Detection result: {json.dumps(result, indent=2)}")

    # Step 7: Show snapshot preview
    print("\n[7] Snapshot preview (first 2000 chars):")
    print("-" * 70)
    preview = snapshot_text[:2000]
    print(preview)
    print("-" * 70)

    print("\n" + "=" * 70)
    print("DEBUG COMPLETE")
    print("=" * 70)
    
except Exception as e:
    print(f"\n[ERROR] {e}")
    import traceback
    traceback.print_exc()
finally:
    client.close()
