#!/usr/bin/env python3
"""
Minimal reproduction of the exact issue from verify_mcp_fix.py.

This uses the EXACT same code structure as verify_mcp_fix.py to isolate the bug.
"""

import json
import sys
import io
import time
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

def send_request(method, params=None, include_session=True, description=""):
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
    
    if description:
        print(f"  [{description}] Session: {session_id[:8] if session_id else 'None'}...")
    
    req = Request(base_url, data=data, headers=headers, method='POST')
    
    try:
        with urlopen(req, timeout=60) as resp:
            # Get session BEFORE body
            new_session = resp.headers.get('Mcp-Session-Id') or resp.headers.get('mcp-session-id')
            if new_session:
                if new_session != session_id:
                    print(f"    Session UPDATED: {session_id[:8] if session_id else 'None'}... -> {new_session[:8]}...")
                session_id = new_session
            
            body = resp.read().decode('utf-8')
            return parse_sse(body), None
            
    except HTTPError as e:
        error_body = e.read().decode('utf-8') if e.fp else str(e)
        return None, f"HTTP {e.code}: {error_body[:200]}"
    except URLError as e:
        return None, f"Connection failed: {e.reason}"

print("=" * 70)
print("Minimal Reproduction - Exact verify_mcp_fix.py flow")
print("=" * 70)

# Initialize
print("\n[1] Initialize...")
result, error = send_request("initialize", {
    "protocolVersion": "2024-11-05",
    "capabilities": {},
    "clientInfo": {"name": "repro", "version": "1.0.0"}
}, include_session=False, description="Init")

if error:
    print(f"  FAIL: {error}")
    sys.exit(1)

print(f"  Session: {session_id}")

# Notification
send_request("notifications/initialized", include_session=True)

# Snapshot before
print("\n[2] Snapshot BEFORE navigate...")
result, error = send_request("tools/call", {
    "name": "browser_snapshot",
    "arguments": {}
}, description="Pre-nav")

if error:
    print(f"  FAIL: {error}")
else:
    print(f"  OK")

# Navigate
print("\n[3] Navigate...")
result, error = send_request("tools/call", {
    "name": "browser_navigate",
    "arguments": {"url": "https://example.com"}
}, description="Navigate")

if error:
    print(f"  FAIL: {error}")
    sys.exit(1)
else:
    print(f"  Navigate OK")
    if result and "error" in result:
        print(f"  Error in result: {result['error']}")

# Check session after navigate
print(f"  Session after navigate: {session_id}")

# Wait a bit - maybe timing issue?
print("\n  Waiting 2 seconds...")
time.sleep(2)

# Snapshot after - THE CRITICAL TEST
print("\n[4] Snapshot AFTER navigate (CRITICAL)...")
print(f"  Current session_id variable: {session_id}")

# First attempt - immediate
print("\n[4a] Immediate snapshot...")
result, error = send_request("tools/call", {
    "name": "browser_snapshot",
    "arguments": {}
}, description="Post-nav")

if error:
    print(f"  FAIL: {error}")
    print("\n  >>> This is the BUG! Let's investigate...")
    
    # Try with fresh session extraction
    print("\n[4b] Re-reading session from fresh request...")
    # Send a dummy request to see what session the server expects
    test_payload = {
        "jsonrpc": "2.0",
        "id": next_id(),
        "method": "tools/call",
        "params": {"name": "browser_snapshot", "arguments": {}}
    }
    test_data = json.dumps(test_payload).encode('utf-8')
    
    # Try with current session
    test_headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "mcp-session-id": session_id,
        "Mcp-Session-Id": session_id,
    }
    
    test_req = Request(base_url, data=test_data, headers=test_headers, method='POST')
    try:
        with urlopen(test_req, timeout=60) as resp:
            new_sess = resp.headers.get('Mcp-Session-Id') or resp.headers.get('mcp-session-id')
            print(f"    Response session header: {new_sess}")
            test_body = resp.read().decode('utf-8')
            test_result = parse_sse(test_body)
            if "error" in test_result:
                print(f"    Error: {test_result['error']}")
            else:
                print(f"    SUCCESS! Session was valid.")
    except HTTPError as e:
        error_body = e.read().decode('utf-8') if e.fp else str(e)
        print(f"    HTTP {e.code}: {error_body[:200]}")
        
        # Check if it's a parsing issue - maybe response has session but we're not getting it
        print(f"    Response headers: {dict(e.headers) if hasattr(e, 'headers') and e.headers else 'N/A'}")
else:
    print(f"  OK - No error!")
    if result and "error" in result:
        print(f"  Error in result: {result['error']}")
    else:
        print(f"  SUCCESS!")

print("\n" + "=" * 70)
