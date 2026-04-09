#!/usr/bin/env python3
"""
Test to replicate exact gmail_mcp_sender.py flow.
"""

import json
import sys
import io
import time
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

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

def send_request(method, params=None, description=""):
    global session_id
    payload = {
        "jsonrpc": "2.0",
        "id": next_id(),
        "method": method,
    }
    if params:
        payload["params"] = params
    
    data = json.dumps(payload).encode('utf-8')
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    }
    if session_id:
        headers["mcp-session-id"] = session_id
        headers["Mcp-Session-Id"] = session_id
        print(f"    Session: {session_id[:8]}...")
    
    req = Request(base_url, data=data, headers=headers, method='POST')
    
    try:
        with urlopen(req, timeout=60) as resp:
            new_session = resp.headers.get('mcp-session-id')
            if new_session and new_session != session_id:
                session_id = new_session
            body = resp.read().decode('utf-8')
            result = parse_response(body)
            if 'error' in result:
                print(f"    ERROR: {result['error']}")
                return None
            print(f"    {description} OK")
            return result
    except HTTPError as e:
        body = e.read().decode('utf-8') if e.fp else str(e)
        print(f"    HTTP {e.code}: {body[:200]}")
        return None
    except URLError as e:
        print(f"    URLError: {e}")
        return None

print("=" * 70)
print("Replicating gmail_mcp_sender.py flow")
print("=" * 70)

# Step 1: Initialize
print("\n[1] Initialize...")
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
data = json.dumps(payload).encode('utf-8')
headers = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
}
req = Request(base_url, data=data, headers=headers, method='POST')
with urlopen(req, timeout=30) as resp:
    session_id = resp.headers.get('mcp-session-id')
    body = resp.read().decode('utf-8')
    result = parse_response(body)
    print(f"  Session: {session_id}")
    print(f"  Server: {result.get('result', {}).get('serverInfo', {})}")

# Step 2: Initialized notification
print("\n[2] Send initialized notification...")
notify_payload = {"jsonrpc": "2.0", "method": "notifications/initialized"}
data = json.dumps(notify_payload).encode('utf-8')
headers = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
    "mcp-session-id": session_id,
    "Mcp-Session-Id": session_id,
}
req = Request(base_url, data=data, headers=headers, method='POST')
try:
    with urlopen(req, timeout=10) as resp:
        print(f"  Notification sent")
except Exception as e:
    print(f"  Note: {e}")

# Step 3: Navigate to Gmail
print("\n[3] Navigate to Gmail...")
result = send_request("tools/call", {
    "name": "browser_navigate",
    "arguments": {"url": "https://mail.google.com/mail/u/0/"}
}, "Navigation")
if result:
    content = result.get('result', {}).get('content', [{}])[0].get('text', '')
    print(f"  Result: {content[:100]}...")

# Wait for page load
print("  Waiting 3 seconds...")
time.sleep(3)

# Step 4: Snapshot (this is where it fails)
print("\n[4] Get snapshot...")
result = send_request("tools/call", {
    "name": "browser_snapshot",
    "arguments": {}
}, "Snapshot")
if result:
    content = result.get('result', {}).get('content', [{}])[0].get('text', '')
    print(f"  Snapshot length: {len(content)} chars")
else:
    print("  FAILED - This is the bug!")

print("\n" + "=" * 70)
