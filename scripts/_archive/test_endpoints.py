#!/usr/bin/env python3
"""Test MCP server with /sse endpoint vs /mcp endpoint."""

import json
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

def test_endpoint(url, label):
    print(f"\n[{label}] Using {url}...")
    print(f"  URL: {url}")
    
    # Step 1: Initialize
    print("  [1] Initialize...")
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
    
    session_id = None
    try:
        req = Request(url, data=json.dumps(payload).encode('utf-8'), headers=headers, method='POST')
        with urlopen(req, timeout=30) as resp:
            session_id = resp.headers.get('Mcp-Session-Id') or resp.headers.get('mcp-session-id')
            print(f"      Session ID: {session_id}")
            body = resp.read().decode('utf-8')
            print(f"      Initialize: OK")
    except Exception as e:
        print(f"      ERROR: {e}")
        return
    
    if not session_id:
        print("      No session ID returned!")
        return
    
    # Step 2: Send initialized notification
    print("  [2] Initialized notification...")
    notify_payload = {"jsonrpc": "2.0", "method": "notifications/initialized"}
    notify_headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "Mcp-Session-Id": session_id,
    }
    try:
        req = Request(url, data=json.dumps(notify_payload).encode('utf-8'), headers=notify_headers, method='POST')
        with urlopen(req, timeout=10) as resp:
            print(f"      Status: {resp.status}")
    except Exception as e:
        print(f"      Note: {e}")
    
    # Step 3: Tool call
    print("  [3] Tool call (browser_snapshot)...")
    tool_payload = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {"name": "browser_snapshot", "arguments": {}}
    }
    tool_headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "Mcp-Session-Id": session_id,
    }
    try:
        req = Request(url, data=json.dumps(tool_payload).encode('utf-8'), headers=tool_headers, method='POST')
        with urlopen(req, timeout=30) as resp:
            print(f"      Status: {resp.status}")
            new_session = resp.headers.get('Mcp-Session-Id') or resp.headers.get('mcp-session-id')
            print(f"      Session in response: {new_session}")
            body = resp.read().decode('utf-8')
            if 'error' in body.lower():
                print(f"      Error: {body[:200]}")
            else:
                print(f"      Success! Response: {body[:100]}...")
    except HTTPError as e:
        body = e.read().decode('utf-8') if e.fp else str(e)
        print(f"      HTTP {e.code}: {body[:200]}")
    except Exception as e:
        print(f"      ERROR: {e}")

print("=" * 70)
print("MCP Server Endpoint Test: /sse vs /mcp")
print("=" * 70)

# Test with /mcp endpoint (streamable HTTP)
test_endpoint("http://localhost:8808/mcp", "Test 1")

# Test with /sse endpoint (legacy SSE)
test_endpoint("http://localhost:8808/sse", "Test 2")

print("\n" + "=" * 70)
