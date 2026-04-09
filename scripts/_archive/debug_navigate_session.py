#!/usr/bin/env python3
"""
Debug script to trace exactly what happens during browser_navigate.

This captures:
1. Full HTTP request/response for navigate
2. Session ID before and after navigate
3. Any error details from the 404 response
"""

import json
import sys
import io
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

base_url = "http://localhost:8808"
session_id = None
request_id = 0

def next_id():
    global request_id
    request_id += 1
    return request_id

def parse_sse(body):
    body = body.strip()
    if not body:
        return {}
    if 'event:' in body or body.startswith('data:'):
        for line in body.split('\n'):
            line = line.strip()
            if line.startswith('data:'):
                json_str = line[5:].strip()
                if json_str and json_str != '[DONE]':
                    try:
                        return json.loads(json_str)
                    except:
                        continue
        return {}
    try:
        return json.loads(body)
    except:
        return {}

def send_request(method, params=None, include_session=True):
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
    if session_id and include_session:
        headers["mcp-session-id"] = session_id
        headers["Mcp-Session-Id"] = session_id
        print(f"    Using session: {session_id[:8] if session_id else 'None'}...")
    
    req = Request(base_url, data=data, headers=headers, method='POST')
    
    try:
        with urlopen(req, timeout=60) as resp:
            # Get session BEFORE body
            new_session = resp.headers.get('Mcp-Session-Id') or resp.headers.get('mcp-session-id')
            if new_session:
                if new_session != session_id:
                    print(f"    Session CHANGED: {session_id[:8] if session_id else 'None'}... -> {new_session[:8]}...")
                session_id = new_session
            
            body = resp.read().decode('utf-8')
            return parse_sse(body), None
            
    except HTTPError as e:
        error_body = e.read().decode('utf-8') if e.fp else str(e)
        print(f"    HTTP {e.code} Response Headers: {dict(e.headers) if hasattr(e, 'headers') and e.headers else 'N/A'}")
        print(f"    HTTP {e.code} Response Body: {error_body[:500]}")
        return None, f"HTTP {e.code}: {error_body}"
    except URLError as e:
        return None, f"Connection failed: {e.reason}"

print("=" * 70)
print("Debug: browser_navigate Session Behavior")
print("=" * 70)

# Step 1: Initialize
print("\n[1] Initialize...")
result, error = send_request("initialize", {
    "protocolVersion": "2024-11-05",
    "capabilities": {},
    "clientInfo": {"name": "debug", "version": "1.0.0"}
}, include_session=False)

if error:
    print(f"  FAIL: {error}")
    sys.exit(1)

print(f"  Session after init: {session_id[:8] if session_id else 'None'}...")

# Send initialized notification
send_request("notifications/initialized", include_session=True)

# Step 2: Snapshot before navigate
print("\n[2] Snapshot BEFORE navigate...")
result, error = send_request("tools/call", {
    "name": "browser_snapshot",
    "arguments": {}
})

if error:
    print(f"  FAIL: {error}")
else:
    print(f"  OK - Session still: {session_id[:8] if session_id else 'None'}...")

# Step 3: Navigate
print("\n[3] Navigate to example.com...")
print("    Watching for session changes...")
result, error = send_request("tools/call", {
    "name": "browser_navigate",
    "arguments": {"url": "https://example.com"}
})

if error:
    print(f"  FAIL during navigate: {error}")
else:
    print(f"  Navigate OK - Session now: {session_id[:8] if session_id else 'None'}...")
    if "error" in result:
        print(f"  Error in result: {result['error']}")

# Step 4: Snapshot after navigate (this is where it fails)
print("\n[4] Snapshot AFTER navigate...")
print(f"    Using session: {session_id[:8] if session_id else 'None'}...")

# Try with lowercase header only
print("\n[4a] Trying with lowercase header (mcp-session-id)...")
payload = {
    "jsonrpc": "2.0",
    "id": next_id(),
    "method": "tools/call",
    "params": {"name": "browser_snapshot", "arguments": {}}
}
data = json.dumps(payload).encode('utf-8')
headers = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
    "mcp-session-id": session_id,
}
req = Request(base_url, data=data, headers=headers, method='POST')
try:
    with urlopen(req, timeout=60) as resp:
        new_session = resp.headers.get('Mcp-Session-Id') or resp.headers.get('mcp-session-id')
        if new_session:
            print(f"    Response session: {new_session[:8]}...")
        body = resp.read().decode('utf-8')
        result = parse_sse(body)
        if "error" in result:
            print(f"    Error: {result['error']}")
        else:
            print(f"    SUCCESS with lowercase header!")
except HTTPError as e:
    error_body = e.read().decode('utf-8') if e.fp else str(e)
    print(f"    HTTP {e.code}: {error_body[:200]}")

# Try with capitalized header only
print("\n[4b] Trying with capitalized header (Mcp-Session-Id)...")
headers = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
    "Mcp-Session-Id": session_id,
}
req = Request(base_url, data=data, headers=headers, method='POST')
try:
    with urlopen(req, timeout=60) as resp:
        new_session = resp.headers.get('Mcp-Session-Id') or resp.headers.get('mcp-session-id')
        if new_session:
            print(f"    Response session: {new_session[:8]}...")
        body = resp.read().decode('utf-8')
        result = parse_sse(body)
        if "error" in result:
            print(f"    Error: {result['error']}")
        else:
            print(f"    SUCCESS with capitalized header!")
except HTTPError as e:
    error_body = e.read().decode('utf-8') if e.fp else str(e)
    print(f"    HTTP {e.code}: {error_body[:200]}")

# Try with BOTH headers
print("\n[4c] Trying with BOTH headers...")
headers = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
    "mcp-session-id": session_id,
    "Mcp-Session-Id": session_id,
}
req = Request(base_url, data=data, headers=headers, method='POST')
try:
    with urlopen(req, timeout=60) as resp:
        new_session = resp.headers.get('Mcp-Session-Id') or resp.headers.get('mcp-session-id')
        if new_session:
            print(f"    Response session: {new_session[:8]}...")
        body = resp.read().decode('utf-8')
        result = parse_sse(body)
        if "error" in result:
            print(f"    Error: {result['error']}")
        else:
            print(f"    SUCCESS with both headers!")
except HTTPError as e:
    error_body = e.read().decode('utf-8') if e.fp else str(e)
    print(f"    HTTP {e.code}: {error_body[:200]}")

# Try WITHOUT session header (maybe navigate creates new session?)
print("\n[4d] Trying WITHOUT session header...")
headers = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
}
req = Request(base_url, data=data, headers=headers, method='POST')
try:
    with urlopen(req, timeout=60) as resp:
        new_session = resp.headers.get('Mcp-Session-Id') or resp.headers.get('mcp-session-id')
        print(f"    Response session: {new_session}")
        body = resp.read().decode('utf-8')
        result = parse_sse(body)
        if "error" in result:
            print(f"    Error: {result['error']}")
        else:
            print(f"    SUCCESS without session header! Got new session: {new_session[:8] if new_session else 'None'}...")
            session_id = new_session
except HTTPError as e:
    error_body = e.read().decode('utf-8') if e.fp else str(e)
    print(f"    HTTP {e.code}: {error_body[:200]}")

# Try re-initializing
print("\n[5] Try re-initializing session...")
result, error = send_request("initialize", {
    "protocolVersion": "2024-11-05",
    "capabilities": {},
    "clientInfo": {"name": "debug", "version": "1.0.0"}
}, include_session=False)

if error:
    print(f"  FAIL: {error}")
else:
    print(f"  New session: {session_id[:8] if session_id else 'None'}...")
    
    # Try snapshot with new session
    print("\n[6] Snapshot with new session...")
    result, error = send_request("tools/call", {
        "name": "browser_snapshot",
        "arguments": {}
    })
    
    if error:
        print(f"  FAIL: {error}")
    else:
        print(f"  SUCCESS with new session!")

print("\n" + "=" * 70)
print("Debug complete")
print("=" * 70)
