#!/usr/bin/env python3
"""Test gmail_mcp_sender client directly with verbose tracing."""

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

def send_request(payload, include_session=True):
    global session_id
    data = json.dumps(payload).encode('utf-8')
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    }
    if session_id and include_session:
        headers["Mcp-Session-Id"] = session_id
        print(f"  >>> Using session: {session_id[:8]}...")
    
    req = Request(base_url, data=data, headers=headers, method='POST')
    
    try:
        with urlopen(req, timeout=60) as resp:
            new_session = resp.headers.get('Mcp-Session-Id') or resp.headers.get('mcp-session-id')
            if new_session:
                if new_session != session_id:
                    print(f"  >>> Session: {session_id[:8] if session_id else 'None'}... -> {new_session[:8]}...")
                session_id = new_session
            body = resp.read().decode('utf-8')
            return parse_response(body)
    except HTTPError as e:
        body = e.read().decode('utf-8') if e.fp else str(e)
        print(f"  >>> HTTP {e.code}: {body[:200]}")
        raise Exception(f"HTTP {e.code}: {body}")
    except URLError as e:
        raise Exception(f"Connection failed: {e.reason}")

print("=" * 60)
print("Gmail MCP Sender - Direct Test")
print("=" * 60)

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
result = send_request(payload)
print(f"  Result: {result.get('result', {}).get('serverInfo', {})}")
print(f"  Session ID: {session_id}")

# Step 2: Send initialized notification
print("\n[2] Initialized notification...")
notify_payload = {"jsonrpc": "2.0", "method": "notifications/initialized"}
try:
    send_request(notify_payload)
    print("  OK")
except Exception as e:
    print(f"  Note: {e}")

# Step 3: Navigate to Gmail
print("\n[3] Navigate to Gmail...")
nav_payload = {
    "jsonrpc": "2.0",
    "id": next_id(),
    "method": "tools/call",
    "params": {"name": "browser_navigate", "arguments": {"url": "https://mail.google.com/mail/u/0/"}}
}
result = send_request(nav_payload)
print(f"  Result: {result.get('result', {}).get('content', [{}])[0].get('text', 'OK')[:50]}...")

# Step 4: Snapshot (this is where it fails in gmail_mcp_sender.py)
print("\n[4] Snapshot...")
snap_payload = {
    "jsonrpc": "2.0",
    "id": next_id(),
    "method": "tools/call",
    "params": {"name": "browser_snapshot", "arguments": {}}
}
try:
    result = send_request(snap_payload)
    content = result.get('result', {}).get('content', [{}])[0].get('text', '')
    print(f"  Result: {content[:100]}...")
except Exception as e:
    print(f"  ERROR: {e}")

print("\n" + "=" * 60)
print("Test complete!")
print("=" * 60)
