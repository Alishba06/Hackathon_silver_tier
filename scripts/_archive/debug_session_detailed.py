#!/usr/bin/env python3
"""
Debug script to trace exact HTTP requests and responses with Playwright MCP.
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
print("Playwright MCP - Raw HTTP Debug")
print("=" * 70)

# Request 1: Initialize
print("\n[REQ 1] Initialize:")
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
print(f"  URL: {base_url}")
print(f"  Headers: {headers}")
print(f"  Body: {json.dumps(payload)[:100]}...")

req = Request(base_url, data=data, headers=headers, method='POST')
try:
    with urlopen(req, timeout=30) as resp:
        print(f"\n[RESP 1] Status: {resp.status}")
        print(f"  All headers:")
        for name, value in resp.headers.items():
            print(f"    {name}: {value}")
        body = resp.read().decode('utf-8')
        session_id = resp.headers.get('Mcp-Session-Id') or resp.headers.get('mcp-session-id')
        print(f"  Session ID extracted: {session_id}")
        print(f"  Body preview: {body[:200]}...")
except Exception as e:
    print(f"  ERROR: {e}")

# Request 2: Tool call IMMEDIATELY with session
print(f"\n[REQ 2] Tool call (browser_navigate) with session {session_id}:")
nav_payload = {
    "jsonrpc": "2.0",
    "id": next_id(),
    "method": "tools/call",
    "params": {"name": "browser_navigate", "arguments": {"url": "https://example.com"}}
}

# Test with lowercase header only
data = json.dumps(nav_payload).encode('utf-8')
headers_lower = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
    "mcp-session-id": session_id,
}
print(f"  Headers (lowercase only): {headers_lower}")

req = Request(base_url, data=data, headers=headers_lower, method='POST')
try:
    with urlopen(req, timeout=60) as resp:
        print(f"\n[RESP 2] Status: {resp.status}")
        print(f"  All headers:")
        for name, value in resp.headers.items():
            print(f"    {name}: {value}")
        new_session = resp.headers.get('Mcp-Session-Id') or resp.headers.get('mcp-session-id')
        print(f"  New session: {new_session}")
        body = resp.read().decode('utf-8')
        result = parse_response(body)
        if 'error' in result:
            print(f"  ERROR in response: {result['error']}")
        else:
            print(f"  Success! Content: {str(result.get('result', {}))[:100]}...")
except HTTPError as e:
    body = e.read().decode('utf-8') if e.fp else str(e)
    print(f"\n[RESP 2] HTTP {e.code}: {body[:200]}")
except Exception as e:
    print(f"  ERROR: {e}")

# Request 3: Try with capitalized header
print(f"\n[REQ 3] Tool call (browser_snapshot) with capitalized header:")
snap_payload = {
    "jsonrpc": "2.0",
    "id": next_id(),
    "method": "tools/call",
    "params": {"name": "browser_snapshot", "arguments": {}}
}

data = json.dumps(snap_payload).encode('utf-8')
headers_cap = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
    "Mcp-Session-Id": session_id,
}
print(f"  Headers (capitalized only): {headers_cap}")

req = Request(base_url, data=data, headers=headers_cap, method='POST')
try:
    with urlopen(req, timeout=60) as resp:
        print(f"\n[RESP 3] Status: {resp.status}")
        body = resp.read().decode('utf-8')
        result = parse_response(body)
        if 'error' in result:
            print(f"  ERROR: {result['error']}")
        else:
            print(f"  Success!")
except HTTPError as e:
    body = e.read().decode('utf-8') if e.fp else str(e)
    print(f"\n[RESP 3] HTTP {e.code}: {body[:200]}")
except Exception as e:
    print(f"  ERROR: {e}")

# Request 4: Try with BOTH headers
print(f"\n[REQ 4] Tool call with BOTH headers:")
data = json.dumps(snap_payload).encode('utf-8')
headers_both = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
    "mcp-session-id": session_id,
    "Mcp-Session-Id": session_id,
}
print(f"  Headers (both): {headers_both}")

req = Request(base_url, data=data, headers=headers_both, method='POST')
try:
    with urlopen(req, timeout=60) as resp:
        print(f"\n[RESP 4] Status: {resp.status}")
        body = resp.read().decode('utf-8')
        result = parse_response(body)
        if 'error' in result:
            print(f"  ERROR: {result['error']}")
        else:
            print(f"  Success!")
except HTTPError as e:
    body = e.read().decode('utf-8') if e.fp else str(e)
    print(f"\n[RESP 4] HTTP {e.code}: {body[:200]}")
except Exception as e:
    print(f"  ERROR: {e}")

# Request 5: Try WITHOUT Accept header
print(f"\n[REQ 5] Tool call WITHOUT Accept header:")
data = json.dumps(snap_payload).encode('utf-8')
headers_no_accept = {
    "Content-Type": "application/json",
    "mcp-session-id": session_id,
    "Mcp-Session-Id": session_id,
}
print(f"  Headers (no Accept): {headers_no_accept}")

req = Request(base_url, data=data, headers=headers_no_accept, method='POST')
try:
    with urlopen(req, timeout=60) as resp:
        print(f"\n[RESP 5] Status: {resp.status}")
        body = resp.read().decode('utf-8')
        result = parse_response(body)
        if 'error' in result:
            print(f"  ERROR: {result['error']}")
        else:
            print(f"  Success!")
except HTTPError as e:
    body = e.read().decode('utf-8') if e.fp else str(e)
    print(f"\n[RESP 5] HTTP {e.code}: {body[:200]}")
except Exception as e:
    print(f"  ERROR: {e}")

print("\n" + "=" * 70)
print("Debug complete. Check which header format worked.")
print("=" * 70)
