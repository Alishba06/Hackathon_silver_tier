#!/usr/bin/env python3
"""
Test with simpler URLs to isolate the issue.
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

def test_url(url, description):
    global session_id
    print(f"\n{'='*60}")
    print(f"Test: {description}")
    print(f"URL: {url}")
    print(f"{'='*60}")
    
    # Fresh initialize
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
    try:
        with urlopen(req, timeout=30) as resp:
            session_id = resp.headers.get('mcp-session-id')
            body = resp.read().decode('utf-8')
            print(f"  Session: {session_id}")
    except Exception as e:
        print(f"  ERROR: {e}")
        return
    
    # Navigate
    print("\n[2] Navigate...")
    nav_payload = {
        "jsonrpc": "2.0",
        "id": next_id(),
        "method": "tools/call",
        "params": {"name": "browser_navigate", "arguments": {"url": url}}
    }
    data = json.dumps(nav_payload).encode('utf-8')
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "mcp-session-id": session_id,
        "Mcp-Session-Id": session_id,
    }
    req = Request(base_url, data=data, headers=headers, method='POST')
    try:
        with urlopen(req, timeout=120) as resp:
            new_session = resp.headers.get('mcp-session-id')
            if new_session:
                session_id = new_session
            body = resp.read().decode('utf-8')
            result = parse_response(body)
            if 'error' in result:
                print(f"  Navigate ERROR: {result['error']}")
                return
            print(f"  Navigate OK")
    except HTTPError as e:
        body = e.read().decode('utf-8') if e.fp else str(e)
        print(f"  Navigate HTTP {e.code}: {body[:200]}")
        return
    
    # Wait
    time.sleep(2)
    
    # Snapshot
    print("\n[3] Snapshot...")
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
    req = Request(base_url, data=data, headers=headers, method='POST')
    try:
        with urlopen(req, timeout=60) as resp:
            body = resp.read().decode('utf-8')
            result = parse_response(body)
            if 'error' in result:
                print(f"  Snapshot ERROR: {result['error']}")
            else:
                content = result.get('result', {}).get('content', [{}])[0].get('text', '')
                print(f"  SUCCESS! Snapshot length: {len(content)}")
    except HTTPError as e:
        body = e.read().decode('utf-8') if e.fp else str(e)
        print(f"  Snapshot HTTP {e.code}: {body[:200]}")

# Test with different URLs
test_url("https://example.com", "Simple static page")
test_url("https://httpbin.org/html", "Simple HTML page")
test_url("https://mail.google.com/mail/u/0/", "Gmail (requires login)")

print("\n" + "=" * 70)
print("All tests complete")
print("=" * 70)
