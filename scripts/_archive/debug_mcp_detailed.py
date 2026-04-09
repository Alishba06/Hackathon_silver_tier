#!/usr/bin/env python3
"""Detailed debug of MCP session handling with full HTTP trace."""

import json
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

url = "http://localhost:8808/mcp"

print("=" * 70)
print("MCP Session Debug - Full HTTP Trace")
print("=" * 70)

session_id = None

# Step 1: Initialize
print("\n[Step 1] INITIALIZE REQUEST")
print("-" * 70)
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

print(f"POST {url}")
print(f"Headers: {headers}")
print(f"Body: {json.dumps(payload)}")

try:
    req = Request(url, data=data, headers=headers, method='POST')
    with urlopen(req, timeout=30) as resp:
        print(f"\nResponse Status: {resp.status}")
        print(f"Response Headers: {dict(resp.headers)}")
        session_id = resp.headers.get('Mcp-Session-Id') or resp.headers.get('mcp-session-id')
        print(f"\n>>> Session ID extracted: {session_id}")
        body = resp.read().decode('utf-8')
        print(f"Response Body: {body}")
except Exception as e:
    print(f"ERROR: {e}")
    exit(1)

if not session_id:
    print("ERROR: No session ID returned!")
    exit(1)

# Step 2: Send initialized notification
print("\n\n[Step 2] INITIALIZED NOTIFICATION")
print("-" * 70)
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

print(f"POST {url}")
print(f"Headers: {notify_headers}")
print(f"Body: {json.dumps(notify_payload)}")

try:
    req = Request(url, data=notify_data, headers=notify_headers, method='POST')
    with urlopen(req, timeout=10) as resp:
        print(f"\nResponse Status: {resp.status}")
        print(f"Response Headers: {dict(resp.headers)}")
        body = resp.read().decode('utf-8')
        print(f"Response Body: {body[:200] if body else '(empty)'}")
except Exception as e:
    print(f"Note: {e}")

# Step 3: First tool call (browser_snapshot)
print("\n\n[Step 3] FIRST TOOL CALL - browser_snapshot")
print("-" * 70)
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

print(f"POST {url}")
print(f"Headers: {tool_headers}")
print(f"Body: {json.dumps(tool_payload)}")

try:
    req = Request(url, data=tool_data, headers=tool_headers, method='POST')
    with urlopen(req, timeout=60) as resp:
        print(f"\nResponse Status: {resp.status}")
        print(f"Response Headers: {dict(resp.headers)}")
        new_session = resp.headers.get('Mcp-Session-Id') or resp.headers.get('mcp-session-id')
        print(f"\n>>> Session ID in response: {new_session}")
        print(f">>> Session ID matches: {new_session == session_id}")
        body = resp.read().decode('utf-8')
        if len(body) > 500:
            print(f"Response Body (truncated): {body[:500]}...")
        else:
            print(f"Response Body: {body}")
except HTTPError as e:
    body = e.read().decode('utf-8') if e.fp else str(e)
    print(f"\nHTTP Error {e.code}:")
    print(f"Response Headers: {dict(e.headers) if e.headers else 'N/A'}")
    print(f"Body: {body}")
except URLError as e:
    print(f"URL Error: {e.reason}")
except Exception as e:
    print(f"ERROR: {e}")

# Step 4: Second tool call (simulate next step in script)
print("\n\n[Step 4] SECOND TOOL CALL - browser_snapshot (again)")
print("-" * 70)
tool_payload2 = {
    "jsonrpc": "2.0",
    "id": 3,
    "method": "tools/call",
    "params": {
        "name": "browser_snapshot",
        "arguments": {}
    }
}
tool_data2 = json.dumps(tool_payload2).encode('utf-8')
tool_headers2 = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
    "Mcp-Session-Id": session_id,
}

print(f"POST {url}")
print(f"Headers: {tool_headers2}")
print(f"Body: {json.dumps(tool_payload2)}")

try:
    req = Request(url, data=tool_data2, headers=tool_headers2, method='POST')
    with urlopen(req, timeout=60) as resp:
        print(f"\nResponse Status: {resp.status}")
        print(f"Response Headers: {dict(resp.headers)}")
        new_session = resp.headers.get('Mcp-Session-Id') or resp.headers.get('mcp-session-id')
        print(f"\n>>> Session ID in response: {new_session}")
        print(f">>> Session ID matches: {new_session == session_id}")
        body = resp.read().decode('utf-8')
        if len(body) > 500:
            print(f"Response Body (truncated): {body[:500]}...")
        else:
            print(f"Response Body: {body}")
except HTTPError as e:
    body = e.read().decode('utf-8') if e.fp else str(e)
    print(f"\nHTTP Error {e.code}:")
    print(f"Response Headers: {dict(e.headers) if e.headers else 'N/A'}")
    print(f"Body: {body[:500]}")
except URLError as e:
    print(f"URL Error: {e.reason}")
except Exception as e:
    print(f"ERROR: {e}")

print("\n" + "=" * 70)
print("Debug complete!")
print("=" * 70)
