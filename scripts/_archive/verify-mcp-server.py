#!/usr/bin/env python3
"""
Verify Playwright MCP Server is running (Windows-compatible).
"""

import json
import sys
import io
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

# Fix Windows console Unicode issues
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')


def check_mcp_server(url: str = "http://localhost:8808") -> bool:
    """Check if MCP server is responding."""
    # Try both /mcp and /sse endpoints
    test_url = url.rstrip('/')
    
    # First, try to hit the base URL to see what we get
    try:
        req = Request(test_url, method='GET')
        with urlopen(req, timeout=5) as resp:
            print(f"[OK] Server responding at {test_url}")
    except:
        pass

    # Use /mcp endpoint for streamable HTTP transport
    test_url = test_url + '/mcp'

    # Send initialize request to test connection
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "verify", "version": "1.0.0"}
        }
    }

    try:
        data = json.dumps(payload).encode('utf-8')
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        req = Request(test_url, data=data, headers=headers, method='POST')
        
        with urlopen(req, timeout=10) as resp:
            body = resp.read().decode('utf-8').strip()
            
            if not body:
                # Empty response but connection succeeded - server is running
                print("[OK] MCP server running (empty response)")
                return True
            
            # Handle SSE format (event: ... \n data: {...})
            if 'event:' in body or body.startswith('data:'):
                for line in body.split('\n'):
                    line = line.strip()
                    if line.startswith('data:'):
                        json_data = line[5:].strip()
                        if json_data:
                            result = json.loads(json_data)
                            if "result" in result:
                                print("[OK] MCP server running and initialized")
                                return True
                            elif "error" in result:
                                print(f"[WARN] MCP server responding but not initialized: {result['error'].get('message')}")
                                return True
                print("[WARN] MCP server responded with SSE but no data found")
                return True
            
            # Handle plain JSON response
            result = json.loads(body)
            
            if "error" in result:
                # Server responded but not initialized - that's OK for our purposes
                print(f"[WARN] MCP server responding but not initialized: {result['error'].get('message')}")
                return True
            elif "result" in result:
                print("[OK] MCP server running and initialized")
                return True
            else:
                print("[WARN] MCP server responded with unexpected format")
                return True
                
    except HTTPError as e:
        if e.code == 400:
            # Bad Request usually means server is running but not initialized
            print("[OK] MCP server running (needs initialization)")
            return True
        print(f"[ERROR] HTTP Error: {e.code}")
        return False
    except URLError as e:
        print(f"[ERROR] Connection failed: {e.reason}")
        return False
    except json.JSONDecodeError as e:
        print(f"[ERROR] Invalid JSON response: {e}")
        return False
    except Exception as e:
        print(f"[ERROR] Unexpected error: {e}")
        return False


def main():
    print("Checking Playwright MCP Server...")
    print("-" * 40)
    
    if check_mcp_server():
        print("-" * 40)
        print("[OK] Playwright MCP server is running!")
        print("\nYou can now run:")
        print("  python scripts\\gmail_mcp_sender.py \"to@example.com\" \"Subject\" \"Body\"")
        sys.exit(0)
    else:
        print("-" * 40)
        print("[ERROR] Playwright MCP server is NOT running")
        print("\nTo start the server, run:")
        print("  npx @playwright/mcp@latest --port 8808 --shared-browser-context")
        sys.exit(1)


if __name__ == "__main__":
    main()
