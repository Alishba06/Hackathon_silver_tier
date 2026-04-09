#!/usr/bin/env python3
"""Debug MCP session handling."""

import json
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

url = "http://localhost:8808/mcp"

print("=" * 60)
print("MCP Session Debug Script")
print("=" * 60)

# Step 1: Initialize
print("\n[Step 1] Sending initialize request...")
payload = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
        "protocolVersion": "2024-11-05",
        "capabilities": {},
        "clientInfo": {"name": "debug", "version": "1.0.0"}
    }
}

data = json.dumps(payload).encode('utf-8')
headers = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
}

try:
    req = Request(url, data=data, headers=headers, method='POST')
    with urlopen(req, timeout=30) as resp:
        session_id = resp.headers.get('Mcp-Session-Id') or resp.headers.get('mcp-session-id')
        print(f"  Session ID received: {session_id}")
        body = resp.read().decode('utf-8')
        print(f"  Response: {body[:200]}")
except Exception as e:
    print(f"  ERROR: {e}")
    exit(1)

if not session_id:
    print("  ERROR: No session ID returned!")
    exit(1)

# Step 2: Send initialized notification
print("\n[Step 2] Sending initialized notification...")
notify_payload = {
    "jsonrpc": "2.0",
    "method": "notifications/initialized"
}
notify_data = json.dumps(notify_payload).encode('utf-8')
notify_headers = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
    "Mcp-Session-Id": session_id,
}

try:
    req = Request(url, data=notify_data, headers=notify_headers, method='POST')
    with urlopen(req, timeout=10) as resp:
        print(f"  OK (status: {resp.status})")
except Exception as e:
    print(f"  Note: {e}")

# Step 3: Call a tool (browser_snapshot)
print("\n[Step 3] Calling browser_snapshot tool...")
tool_payload = {
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/call",
    "params": {
        "name": "browser_snapshot",
        "arguments": {}
    }
}
tool_data = json.dumps(tool_payload).encode('utf-8')
tool_headers = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
    "Mcp-Session-Id": session_id,
}

try:
    req = Request(url, data=tool_data, headers=tool_headers, method='POST')
    with urlopen(req, timeout=60) as resp:
        new_session = resp.headers.get('Mcp-Session-Id') or resp.headers.get('mcp-session-id')
        print(f"  Session ID in response: {new_session}")
        body = resp.read().decode('utf-8')
        if len(body) > 500:
            print(f"  Response (truncated): {body[:500]}...")
        else:
            print(f"  Response: {body}")
except HTTPError as e:
    body = e.read().decode('utf-8') if e.fp else str(e)
    print(f"  HTTP Error {e.code}: {body}")
except URLError as e:
    print(f"  URL Error: {e.reason}")
except Exception as e:
    print(f"  ERROR: {e}")

print("\n" + "=" * 60)
print("Debug complete!")
print("=" * 60)
