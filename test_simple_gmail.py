#!/usr/bin/env python3
"""
Simple MCP Test - Navigate to Gmail and check what's on the page.
"""

import json
import sys
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
import time

MCP_URL = "http://localhost:8808/mcp"

class SimpleMCPClient:
    def __init__(self):
        self._session_id = None
        self._request_id = 0
        
    def initialize(self):
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "simple-test", "version": "1.0.0"}
            }
        }
        
        data = json.dumps(payload).encode('utf-8')
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream"
        }
        req = Request(MCP_URL, data=data, headers=headers, method='POST')
        
        with urlopen(req, timeout=30) as resp:
            self._session_id = resp.headers.get('Mcp-Session-Id') or resp.headers.get('mcp-session-id')
            body = resp.read().decode('utf-8')
            print(f"[INIT] Session: {self._session_id}")
            
            # Send initialized notification
            notify = {"jsonrpc": "2.0", "method": "notifications/initialized"}
            notify_data = json.dumps(notify).encode('utf-8')
            notify_headers = {
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
                "Mcp-Session-Id": self._session_id,
                "mcp-session-id": self._session_id
            }
            notify_req = Request(MCP_URL, data=notify_data, headers=notify_headers, method='POST')
            try:
                with urlopen(notify_req, timeout=10) as notify_resp:
                    print(f"[INIT] Notification sent: {notify_resp.status}")
            except:
                pass
            return True
            
    def call_tool(self, name, args=None):
        payload = {
            "jsonrpc": "2.0",
            "id": self._request_id,
            "method": "tools/call",
            "params": {"name": name}
        }
        if args:
            payload["params"]["arguments"] = args
            
        self._request_id += 1
        
        data = json.dumps(payload).encode('utf-8')
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Mcp-Session-Id": self._session_id,
            "mcp-session-id": self._session_id
        }
        req = Request(MCP_URL, data=data, headers=headers, method='POST')
        
        with urlopen(req, timeout=60) as resp:
            # Update session ID from response
            new_session = resp.headers.get('Mcp-Session-Id') or resp.headers.get('mcp-session-id')
            if new_session:
                self._session_id = new_session
                
            body = resp.read().decode('utf-8')
            
            # Parse SSE
            for line in body.split('\n'):
                line = line.strip()
                if line.startswith('data:'):
                    return json.loads(line[5:].strip())
        return {}

def main():
    print("=" * 60)
    print("SIMPLE GMAIL MCP TEST")
    print("=" * 60)
    
    client = SimpleMCPClient()
    client.initialize()
    
    # Step 1: Navigate to Gmail
    print("\n[1/4] Navigating to Gmail...")
    result = client.call_tool("browser_navigate", {"url": "https://mail.google.com/mail/u/0/"})
    print(f"    Navigate result: {result}")
    
    # Wait for page to load
    print("    Waiting 5 seconds for page load...")
    time.sleep(5)
    
    # Step 2: Take snapshot
    print("\n[2/4] Taking snapshot...")
    snapshot = client.call_tool("browser_snapshot", {})
    
    # Extract and show content
    content = snapshot.get('result', {}).get('content', [])
    if isinstance(content, list) and len(content) > 0:
        text = content[0].get('text', '') if isinstance(content[0], dict) else str(content[0])
        print(f"\n    Page content (first 500 chars):")
        print(f"    {'-' * 50}")
        print(f"    {text[:500]}")
        print(f"    {'-' * 50}")
        
        # Check for key indicators
        if 'Sign in' in text or 'sign in' in text.lower():
            print("\n    [!] LOGIN PAGE DETECTED - You need to sign in to Gmail")
        elif 'Compose' in text:
            print("\n    [OK] COMPOSE BUTTON FOUND - Logged in!")
        elif 'Inbox' in text or 'inbox' in text:
            print("\n    [OK] INBOX FOUND - Logged in!")
        else:
            print("\n    [?] Unknown page state")
    
    # Step 3: Try to find Compose button
    print("\n[3/4] Looking for Compose button...")
    compose_test = """async (page) => {
        await page.waitForLoadState('networkidle');
        await page.waitForTimeout(2000);
        
        const results = {};
        
        // Try different selectors
        try {
            const btn1 = page.get_by_role("button", { name: "Compose" });
            results.getByRole = await btn1.isVisible();
        } catch(e) { results.getByRole = 'error: ' + e.message }
        
        try {
            const btn2 = page.locator('button[gh="cm"]').first();
            results.ghCmButton = await btn2.isVisible();
        } catch(e) { results.ghCmButton = 'error: ' + e.message }
        
        try {
            const btn3 = page.locator('div[role="button"][gh="cm"]').first();
            results.ghCmDiv = await btn3.isVisible();
        } catch(e) { results.ghCmDiv = 'error: ' + e.message }
        
        return results;
    }"""
    
    compose_result = client.call_tool("browser_run_code", {"code": compose_test})
    print(f"    Compose button check: {compose_result}")
    
    # Step 4: Close
    print("\n[4/4] Closing browser...")
    client.call_tool("browser_close", {})
    print("    Done!")
    
    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    main()
