#!/usr/bin/env python3
"""
Debug browser_navigate response to see if session changes.
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

def print_all_headers(prefix, headers):
    print(f"  {prefix} Headers:")
    for name, value in headers.items():
        print(f"    {name}: {value}")

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
print("Debug browser_navigate response")
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
    print_all_headers("Response", resp.headers)
    session_id = resp.headers.get('mcp-session-id')
    body = resp.read().decode('utf-8')
    print(f"  Session after init: {session_id}")

# Step 2: Initialized notification
print("\n[2] Send initialized notification...")
notify_payload = {"jsonrpc": "2.0", "method": "notifications/initialized"}
data = json.dumps(notify_payload).encode('utf-8')
headers = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
    "mcp-session-id": session_id,
    "Mcp-Session-Id": session_id,
}
req = Request(base_url, data=data, headers=headers, method='POST')
try:
    with urlopen(req, timeout=10) as resp:
        print_all_headers("Notification Response", resp.headers)
        body = resp.read().decode('utf-8')
        print(f"  Body: '{body}'")
except Exception as e:
    print(f"  Note: {e}")

# Step 3: Navigate to Gmail - CAPTURE EVERYTHING
print("\n[3] Navigate to Gmail (capturing full response)...")
nav_payload = {
    "jsonrpc": "2.0",
    "id": next_id(),
    "method": "tools/call",
    "params": {"name": "browser_navigate", "arguments": {"url": "https://mail.google.com/mail/u/0/"}}
}
data = json.dumps(nav_payload).encode('utf-8')
headers = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
    "mcp-session-id": session_id,
    "Mcp-Session-Id": session_id,
}
print(f"  Request headers: {headers}")

req = Request(base_url, data=data, headers=headers, method='POST')
try:
    with urlopen(req, timeout=120) as resp:  # Longer timeout for navigation
        print_all_headers("Navigate Response", resp.headers)
        
        # Check for session ID in response
        new_session = resp.headers.get('mcp-session-id') or resp.headers.get('Mcp-Session-Id')
        print(f"  Session in response header: {new_session}")
        
        # Read body in chunks to see what's happening
        raw_body = resp.read().decode('utf-8')
        print(f"  Raw body length: {len(raw_body)}")
        print(f"  Raw body preview:\n{raw_body[:500]}")
        
        # Parse the response
        result = parse_response(raw_body)
        print(f"  Parsed result: {json.dumps(result, indent=2)[:500]}")
        
        # Update session ID
        if new_session:
            session_id = new_session
            print(f"  Session updated to: {session_id}")
            
except HTTPError as e:
    body = e.read().decode('utf-8') if e.fp else str(e)
    print(f"  HTTP {e.code}: {body}")
except Exception as e:
    print(f"  ERROR: {e}")

print(f"\n  Final session ID: {session_id}")

# Step 4: Try snapshot with the session
print("\n[4] Try snapshot with session...")
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
print(f"  Request headers: {headers}")

req = Request(base_url, data=data, headers=headers, method='POST')
try:
    with urlopen(req, timeout=60) as resp:
        print_all_headers("Snapshot Response", resp.headers)
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
