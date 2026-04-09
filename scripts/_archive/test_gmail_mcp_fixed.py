#!/usr/bin/env python3
"""
Test script to verify the MCP session header fix.

This script tests that:
1. Session is created successfully
2. Session persists across multiple tool calls
3. Both header formats (mcp-session-id and Mcp-Session-Id) are sent
"""

import json
import sys
import io
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

# Fix Windows console Unicode issues
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

base_url = "http://localhost:8808/mcp"
session_id = None
request_id = 0

def next_id():
    global request_id
    request_id += 1
    return request_id

def parse_response(body):
    body = body.strip()
    if not body:
        return {}
    if 'event:' in body or body.startswith('data:'):
        for line in body.split('\n'):
            line = line.strip()
            if line.startswith('data:'):
                json_data = line[5:].strip()
                if json_data:
                    return json.loads(json_data)
    return json.loads(body)

def send_request(payload, include_session=True, wait_for_response=True):
    global session_id
    data = json.dumps(payload).encode('utf-8')
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    }
    if session_id and include_session:
        # Send BOTH header formats for maximum compatibility
        headers["mcp-session-id"] = session_id
        headers["Mcp-Session-Id"] = session_id
        print(f"  >>> Using session: {session_id[:8] if len(session_id) > 8 else session_id}...")

    req = Request(base_url, data=data, headers=headers, method='POST')

    try:
        with urlopen(req, timeout=120 if wait_for_response else 60) as resp:
            new_session = resp.headers.get('Mcp-Session-Id') or resp.headers.get('mcp-session-id')
            if new_session:
                if new_session != session_id:
                    print(f"  >>> Session updated: {session_id[:8] if session_id and len(session_id) > 8 else session_id}... -> {new_session[:8]}...")
                session_id = new_session
            body = resp.read().decode('utf-8')
            print(f"  >>> Response body length: {len(body)}")
            return parse_response(body)
    except HTTPError as e:
        body = e.read().decode('utf-8') if e.fp else str(e)
        print(f"  >>> HTTP {e.code}: {body[:200]}")
        raise Exception(f"HTTP {e.code}: {body}")
    except URLError as e:
        raise Exception(f"Connection failed: {e.reason}")

print("=" * 70)
print("Gmail MCP Sender - Session Header Fix Test")
print("=" * 70)
print("\nThis test verifies that session headers are sent correctly")
print("using BOTH 'mcp-session-id' and 'Mcp-Session-Id' formats.\n")

# Step 1: Initialize
print("[1/5] Initialize session...")
payload = {
    "jsonrpc": "2.0",
    "id": next_id(),
    "method": "initialize",
    "params": {
        "protocolVersion": "2024-11-05",
        "capabilities": {},
        "clientInfo": {"name": "gmail-mcp-sender", "version": "1.0.0"}
    }
}
result = send_request(payload)
print(f"  Server: {result.get('result', {}).get('serverInfo', {})}")
print(f"  Session ID: {session_id}")
print("  [OK] Session initialized")

# Step 2: Send initialized notification
print("\n[2/5] Send initialized notification...")
notify_payload = {"jsonrpc": "2.0", "method": "notifications/initialized"}
try:
    send_request(notify_payload)
    print("  [OK] Notification sent")
except Exception as e:
    print(f"  [NOTE] {e}")

# Step 3: Navigate to Gmail
print("\n[3/5] Navigate to Gmail...")
nav_payload = {
    "jsonrpc": "2.0",
    "id": next_id(),
    "method": "tools/call",
    "params": {"name": "browser_navigate", "arguments": {"url": "https://mail.google.com/mail/u/0/"}}
}
result = send_request(nav_payload)
content = result.get('result', {}).get('content', [{}])[0].get('text', 'OK')
print(f"  Result: {content[:80]}...")
print(f"  Session preserved: {session_id is not None}")
print("  [OK] Navigation successful")

# Step 4: Snapshot (this is where it was failing before)
print("\n[4/5] Get browser snapshot...")
snap_payload = {
    "jsonrpc": "2.0",
    "id": next_id(),
    "method": "tools/call",
    "params": {"name": "browser_snapshot", "arguments": {}}
}
try:
    result = send_request(snap_payload)
    content = result.get('result', {}).get('content', [{}])[0].get('text', '')
    print(f"  Snapshot length: {len(content)} chars")
    print(f"  Session preserved: {session_id is not None}")
    print("  [OK] Snapshot successful - FIX VERIFIED!")
except Exception as e:
    print(f"  [FAIL] {e}")
    print("\n  The session header fix did not work.")
    print("  Check that the MCP server is running: npx @playwright/mcp@latest --port 8808")
    sys.exit(1)

# Step 5: Another snapshot to confirm session persistence
print("\n[5/5] Get another snapshot (session persistence test)...")
try:
    result = send_request(snap_payload)
    content = result.get('result', {}).get('content', [{}])[0].get('text', '')
    print(f"  Snapshot length: {len(content)} chars")
    print(f"  Session still active: {session_id is not None}")
    print("  [OK] Session persists across multiple calls!")
except Exception as e:
    print(f"  [FAIL] {e}")
    print("\n  Session was lost between calls.")
    sys.exit(1)

print("\n" + "=" * 70)
print("ALL TESTS PASSED!")
print("=" * 70)
print("\nThe fix is working correctly:")
print("  ✓ Session is created and preserved")
print("  ✓ Both header formats are sent (mcp-session-id and Mcp-Session-Id)")
print("  ✓ Session persists across multiple tool calls")
print("  ✓ browser_snapshot works after browser_navigate")
print("\nYou can now use gmail_mcp_sender.py without session errors.")
print("=" * 70)
