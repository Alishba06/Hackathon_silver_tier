#!/usr/bin/env python3
"""Test different session header formats."""

import json
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

base_url = "http://localhost:8808/mcp"

print("=" * 70)
print("Testing Session Header Formats")
print("=" * 70)

# Test 1: Initialize and get session
print("\n[Test 1] Initialize with standard headers...")
payload = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
        "protocolVersion": "2024-11-05",
        "capabilities": {},
        "clientInfo": {"name": "test", "version": "1.0.0"}
    }
}

headers = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
}

try:
    req = Request(base_url, data=json.dumps(payload).encode('utf-8'), headers=headers, method='POST')
    with urlopen(req, timeout=30) as resp:
        session_id = resp.headers.get('Mcp-Session-Id') or resp.headers.get('mcp-session-id')
        print(f"  Session ID: {session_id}")
        body = resp.read().decode('utf-8')
        print(f"  Response: OK")
except Exception as e:
    print(f"  ERROR: {e}")
    exit(1)

# Test 2: Try tool call with different header formats
test_cases = [
    ("Mcp-Session-Id", "Capitalized"),
    ("mcp-session-id", "Lowercase"),
    ("mcp-session-id", "Lowercase (alt)"),
]

for header_name, description in test_cases:
    print(f"\n[Test] Tool call with {description} header: {header_name}")
    
    tool_payload = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {"name": "browser_snapshot", "arguments": {}}
    }
    
    tool_headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        header_name: session_id,
    }
    
    try:
        req = Request(base_url, data=json.dumps(tool_payload).encode('utf-8'), headers=tool_headers, method='POST')
        with urlopen(req, timeout=30) as resp:
            print(f"  Status: {resp.status}")
            new_session = resp.headers.get('Mcp-Session-Id') or resp.headers.get('mcp-session-id')
            print(f"  Session in response: {new_session}")
            body = resp.read().decode('utf-8')
            if 'error' in body.lower():
                print(f"  Error in body: {body[:200]}")
            else:
                print(f"  Success!")
    except HTTPError as e:
        body = e.read().decode('utf-8') if e.fp else str(e)
        print(f"  HTTP {e.code}: {body[:200]}")
    except Exception as e:
        print(f"  ERROR: {e}")

# Test 3: Try without Accept header
print(f"\n[Test] Tool call without Accept header...")
tool_payload = {
    "jsonrpc": "2.0",
    "id": 3,
    "method": "tools/call",
    "params": {"name": "browser_snapshot", "arguments": {}}
}

tool_headers = {
    "Content-Type": "application/json",
    "Mcp-Session-Id": session_id,
}

try:
    req = Request(base_url, data=json.dumps(tool_payload).encode('utf-8'), headers=tool_headers, method='POST')
    with urlopen(req, timeout=30) as resp:
        print(f"  Status: {resp.status}")
        body = resp.read().decode('utf-8')
        print(f"  Response: {body[:200]}...")
except HTTPError as e:
    body = e.read().decode('utf-8') if e.fp else str(e)
    print(f"  HTTP {e.code}: {body[:200]}")
except Exception as e:
    print(f"  ERROR: {e}")

print("\n" + "=" * 70)
