#!/usr/bin/env python3
"""Test MCP server connection with proper headers."""

import json
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

url = "http://localhost:8808/mcp"

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

data = json.dumps(payload).encode('utf-8')
headers = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
}

print(f"Testing MCP server at {url}")
print("-" * 50)

try:
    req = Request(url, data=data, headers=headers, method='POST')
    with urlopen(req, timeout=10) as resp:
        print(f"Status: {resp.status}")
        print(f"Headers: {dict(resp.headers)}")
        body = resp.read().decode('utf-8')
        print(f"Body ({len(body)} chars):")
        print(body[:1000] if len(body) > 1000 else body)
except HTTPError as e:
    print(f"HTTP Error {e.code}: {e.reason}")
    print(f"Headers: {dict(e.headers) if e.headers else 'N/A'}")
    if e.fp:
        body = e.read().decode('utf-8')
        print(f"Body: {body[:500]}")
except URLError as e:
    print(f"URL Error: {e.reason}")
except Exception as e:
    print(f"Error: {e}")
