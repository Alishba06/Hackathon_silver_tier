#!/usr/bin/env python3
"""
Check if browser_navigate returns a NEW session ID that we need to use.
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

def print_headers(title, headers):
    print(f"  {title}:")
    for name, value in headers.items():
        print(f"    {name}: {value}")

print("=" * 70)
print("Check session ID changes during browser_navigate")
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
print("  Request headers:")
for k, v in headers.items():
    print(f"    {k}: {v}")

req = Request(base_url, data=data, headers=headers, method='POST')
with urlopen(req, timeout=30) as resp:
    print_headers("Response headers", resp.headers)
    session_id = resp.headers.get('mcp-session-id')
    body = resp.read().decode('utf-8')
    print(f"  Session after init: {session_id}")

# Step 2: Navigate WITHOUT session header
print("\n[2] Navigate WITHOUT session header...")
nav_payload = {
    "jsonrpc": "2.0",
    "id": next_id(),
    "method": "tools/call",
    "params": {"name": "browser_navigate", "arguments": {"url": "https://example.com"}}
}
data = json.dumps(nav_payload).encode('utf-8')
headers_no_session = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
}
print("  Request headers (no session):")
for k, v in headers_no_session.items():
    print(f"    {k}: {v}")

req = Request(base_url, data=data, headers=headers_no_session, method='POST')
try:
    with urlopen(req, timeout=60) as resp:
        print_headers("Response headers", resp.headers)
        new_session = resp.headers.get('mcp-session-id')
        body = resp.read().decode('utf-8')
        print(f"  New session from response: {new_session}")
        print(f"  Body: {body[:200]}...")
except HTTPError as e:
    body = e.read().decode('utf-8') if e.fp else str(e)
    print(f"  HTTP {e.code}: {body}")

# Step 3: Try snapshot with ORIGINAL session
print(f"\n[3] Snapshot with ORIGINAL session ({session_id})...")
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
    "Mcp-Session-Id": session_id,
}
print(f"  Request headers (original session):")
for k, v in headers.items():
    print(f"    {k}: {v}")

req = Request(base_url, data=data, headers=headers, method='POST')
try:
    with urlopen(req, timeout=60) as resp:
        body = resp.read().decode('utf-8')
        result = parse_response(body)
        if 'error' in result:
            print(f"  ERROR: {result['error']}")
        else:
            print(f"  SUCCESS!")
except HTTPError as e:
    body = e.read().decode('utf-8') if e.fp else str(e)
    print(f"  HTTP {e.code}: {body[:200]}")

# Step 4: Try snapshot with NEW session (if any)
if new_session and new_session != session_id:
    print(f"\n[4] Snapshot with NEW session ({new_session})...")
    data = json.dumps(snap_payload).encode('utf-8')
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "mcp-session-id": new_session,
        "Mcp-Session-Id": new_session,
    }
    print(f"  Request headers (new session):")
    for k, v in headers.items():
        print(f"    {k}: {v}")
    
    req = Request(base_url, data=data, headers=headers, method='POST')
    try:
        with urlopen(req, timeout=60) as resp:
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
