#!/usr/bin/env python3
"""
Test to see if the initialized notification causes session reset.
"""

import json
import sys
import io
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

print("=" * 70)
print("Test: Does initialized notification cause session issues?")
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
        "clientInfo": {"name": "debug-client", "version": "1.0.0"}
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
    print(f"  Session: {session_id}")
    print(f"  Init response: OK")

# Step 2: Send initialized notification WITH session header
print("\n[2] Send initialized notification WITH session header...")
notify_payload = {"jsonrpc": "2.0", "method": "notifications/initialized"}
data = json.dumps(notify_payload).encode('utf-8')
headers = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
    "mcp-session-id": session_id,
}
req = Request(base_url, data=data, headers=headers, method='POST')
try:
    with urlopen(req, timeout=30) as resp:
        new_session = resp.headers.get('mcp-session-id')
        print(f"  Response session: {new_session}")
        body = resp.read().decode('utf-8')
        print(f"  Response body: {body[:200]}")
except HTTPError as e:
    body = e.read().decode('utf-8') if e.fp else str(e)
    print(f"  HTTP {e.code}: {body[:200]}")

# Step 3: Try tool call AFTER notification
print("\n[3] Tool call AFTER notification...")
snap_payload = {
    "jsonrpc": "2.0",
    "id": next_id(),
    "method": "tools/call",
    "params": {"name": "browser_snapshot", "arguments": {}}
}
data = json.dumps(snap_payload).encode('utf-8')
headers = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
    "mcp-session-id": session_id,
}
req = Request(base_url, data=data, headers=headers, method='POST')
try:
    with urlopen(req, timeout=60) as resp:
        print(f"  Status: {resp.status}")
        body = resp.read().decode('utf-8')
        result = parse_response(body)
        if 'error' in result:
            print(f"  ERROR: {result['error']}")
        else:
            print(f"  SUCCESS!")
except HTTPError as e:
    body = e.read().decode('utf-8') if e.fp else str(e)
    print(f"  HTTP {e.code}: {body[:200]}")

# Step 4: Try WITHOUT sending initialized notification
print("\n\n[4] Testing WITHOUT initialized notification...")
print("    (Fresh session, no notification sent)")

# Fresh initialize
payload = {
    "jsonrpc": "2.0",
    "id": next_id(),
    "method": "initialize",
    "params": {
        "protocolVersion": "2024-11-05",
        "capabilities": {},
        "clientInfo": {"name": "debug-client", "version": "1.0.0"}
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
    print(f"  Session: {session_id}")

# Skip notification, go straight to tool call
print("\n[5] Tool call WITHOUT notification...")
data = json.dumps(snap_payload).encode('utf-8')
headers = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
    "mcp-session-id": session_id,
}
req = Request(base_url, data=data, headers=headers, method='POST')
try:
    with urlopen(req, timeout=60) as resp:
        print(f"  Status: {resp.status}")
        body = resp.read().decode('utf-8')
        result = parse_response(body)
        if 'error' in result:
            print(f"  ERROR: {result['error']}")
        else:
            print(f"  SUCCESS!")
except HTTPError as e:
    body = e.read().decode('utf-8') if e.fp else str(e)
    print(f"  HTTP {e.code}: {body[:200]}")

print("\n" + "=" * 70)
