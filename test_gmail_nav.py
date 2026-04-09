#!/usr/bin/env python3
"""Test Gmail navigation and login status"""

import sys
import io
import json
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
                "clientInfo": {"name": "test", "version": "1.0.0"}
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
        headers = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}
        if self._session_id:
            headers["mcp-session-id"] = self._session_id
            headers["Mcp-Session-Id"] = self._session_id
        req = Request(self.base_url, data=data, headers=headers, method='POST')
        with urlopen(req, timeout=60) as resp:
            new_session_id = resp.headers.get('Mcp-Session-Id') or resp.headers.get('mcp-session-id')
            body = resp.read().decode('utf-8')
            if new_session_id:
                self._session_id = new_session_id
            if 'event:' in body or body.startswith('data:'):
                for line in body.split('\n'):
                    line = line.strip()
                    if line.startswith('data:'):
                        return json.loads(line[5:].strip())
            return json.loads(body) if body.strip() else {}

    def call_tool(self, name, args=None):
        self._ensure_initialized()
        payload = {"jsonrpc": "2.0", "id": self._next_id(), "method": "tools/call", "params": {"name": name}}
        if args:
            payload["params"]["arguments"] = args
        print(f"[TOOL] Calling {name}")
        result = self._send_request(payload)
        if "error" in result:
            raise Exception(f"MCP error: {result['error'].get('message')}")
        return result.get("result", {})

    def navigate(self, url):
        return self.call_tool("browser_navigate", {"url": url})

    def snapshot(self):
        return self.call_tool("browser_snapshot", {})

    def close(self):
        try:
            self.call_tool("browser_close", {})
        except:
            pass

print("=" * 60)
print("Gmail Navigation Test")
print("=" * 60)

client = PlaywrightMCPClient()

print("\n[1] Navigating to Gmail...")
result = client.navigate("https://mail.google.com/mail/u/0/")
print(f"    Result: {result}")

print("\n[2] Waiting for page to load...")
time.sleep(5)

print("\n[3] Taking snapshot...")
try:
    snapshot = client.snapshot()
    content = snapshot.get('content', '')
    print(f"    Snapshot length: {len(content)} chars")
    print(f"\n    First 1000 chars:\n    {content[:1000]}")
    
    # Check for key elements
    if 'Sign in' in content or 'sign in' in content.lower():
        print("\n[!] SIGN IN PAGE DETECTED - Not logged in")
    elif 'Compose' in content:
        print("\n[✓] COMPOSE BUTTON FOUND - Logged in!")
    else:
        print("\n[?] Page content unclear")
except Exception as e:
    print(f"    Error: {e}")

client.close()
print("\nDone!")
