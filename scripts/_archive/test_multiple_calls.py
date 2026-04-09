#!/usr/bin/env python3
"""Test if sessions work with multiple tool calls of the same type."""

import json
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

base_url = "http://localhost:8808/mcp"
session_id = None

def parse_response(body):
    body = body.strip()
    if not body:
        return {}
    if 'event:' in body or body.startswith('data:'):
        for line in body.split('\n'):
            line = line.strip()
            if line.startswith('data:'):
                return json.loads(line[5:].strip())
    return json.loads(body)

def send_request(method, params=None):
    global session_id
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
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
        headers["Mcp-Session-Id"] = session_id
    
    req = Request(base_url, data=data, headers=headers, method='POST')
    
    try:
        with urlopen(req, timeout=60) as resp:
            new_session = resp.headers.get('Mcp-Session-Id') or resp.headers.get('mcp-session-id')
            if new_session:
                session_id = new_session
            body = resp.read().decode('utf-8')
            return parse_response(body)
    except HTTPError as e:
        body = e.read().decode('utf-8') if e.fp else str(e)
        raise Exception(f"HTTP {e.code}: {body}")

print("=" * 60)
print("Test: Multiple tool calls")
print("=" * 60)

# Initialize
print("\n[1] Initialize...")
result = send_request("initialize", {
    "protocolVersion": "2024-11-05",
    "capabilities": {},
    "clientInfo": {"name": "test", "version": "1.0.0"}
})
print(f"    Session: {session_id[:8]}...")

# Send initialized notification
print("\n[2] Initialized notification...")
send_request("notifications/initialized")

# Test 1: Multiple snapshots
print("\n[3] Test: Multiple browser_snapshot calls...")
for i in range(3):
    print(f"    [{i+1}] browser_snapshot...")
    try:
        result = send_request("tools/call", {"name": "browser_snapshot", "arguments": {}})
        print(f"        OK")
    except Exception as e:
        print(f"        ERROR: {e}")
        break

# Test 2: Navigate then snapshot
print("\n[4] Test: browser_navigate then browser_snapshot...")
print("    [1] browser_navigate...")
try:
    result = send_request("tools/call", {"name": "browser_navigate", "arguments": {"url": "https://example.com"}})
    print(f"        OK")
except Exception as e:
    print(f"        ERROR: {e}")

print("    [2] browser_snapshot...")
try:
    result = send_request("tools/call", {"name": "browser_snapshot", "arguments": {}})
    print(f"        OK")
except Exception as e:
    print(f"        ERROR: {e}")

print("\n" + "=" * 60)
