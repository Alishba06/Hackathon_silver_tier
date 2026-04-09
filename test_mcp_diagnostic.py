#!/usr/bin/env python3
"""
MCP Diagnostic Test - Verifies Playwright MCP server connection and Gmail automation.
Run this to diagnose issues with gmail_mcp_sender.py
"""

import sys
import json
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

MCP_URL = "http://localhost:8808/mcp"

def test_mcp_connection():
    """Test if MCP server is reachable."""
    print("\n" + "=" * 60)
    print("MCP CONNECTION TEST")
    print("=" * 60)
    
    try:
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "diagnostic", "version": "1.0.0"}
            }
        }
        
        data = json.dumps(payload).encode('utf-8')
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        
        req = Request(MCP_URL, data=data, headers=headers, method='POST')
        
        print(f"Connecting to {MCP_URL}...")
        with urlopen(req, timeout=10) as resp:
            session_id = resp.headers.get('Mcp-Session-Id') or resp.headers.get('mcp-session-id')
            body = resp.read().decode('utf-8')
            
            if session_id:
                print(f"[OK] MCP server reachable")
                print(f"[OK] Session ID: {session_id[:8]}...")
                return session_id
            else:
                print(f"[WARN] No session ID in response")
                return None
                
    except HTTPError as e:
        print(f"[FAIL] HTTP Error {e.code}: {e.read().decode('utf-8')}")
        return None
    except URLError as e:
        print(f"[FAIL] Connection failed: {e.reason}")
        print(f"\n[HINT] Is the MCP server running?")
        print(f"       Start it with: npx @playwright/mcp@latest --port 8808 --shared-browser-context")
        return None
    except Exception as e:
        print(f"[FAIL] Unexpected error: {e}")
        return None


def test_snapshot(session_id):
    """Test browser_snapshot tool."""
    print("\n" + "=" * 60)
    print("BROWSER SNAPSHOT TEST")
    print("=" * 60)
    
    if not session_id:
        print("[SKIP] No session ID available")
        return False
    
    try:
        payload = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "browser_snapshot",
                "arguments": {}
            }
        }
        
        data = json.dumps(payload).encode('utf-8')
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "Mcp-Session-Id": session_id,
            "mcp-session-id": session_id
        }
        
        req = Request(MCP_URL, data=data, headers=headers, method='POST')
        
        print("Calling browser_snapshot...")
        with urlopen(req, timeout=30) as resp:
            body = resp.read().decode('utf-8')
            
            # Parse SSE response
            for line in body.split('\n'):
                line = line.strip()
                if line.startswith('data:'):
                    json_data = json.loads(line[5:].strip())
                    if 'error' in json_data:
                        print(f"[FAIL] MCP Error: {json_data['error'].get('message')}")
                        return False
                    else:
                        print(f"[OK] Snapshot returned successfully")
                        # Check if we can see Gmail content
                        result = json_data.get('result', {})
                        content = result.get('content', [])
                        if content:
                            text_content = ''
                            if isinstance(content, list) and len(content) > 0:
                                text_content = str(content[0].get('text', ''))[:200]
                            elif isinstance(content, str):
                                text_content = content[:200]
                            
                            if 'gmail' in text_content.lower() or 'mail' in text_content.lower():
                                print(f"[OK] Gmail page detected in snapshot")
                            else:
                                print(f"[INFO] Current page content (first 200 chars): {text_content}")
                        return True
                        
    except Exception as e:
        print(f"[FAIL] Snapshot test failed: {e}")
        return False


def test_python_dependencies():
    """Test Python dependencies."""
    print("\n" + "=" * 60)
    print("PYTHON DEPENDENCIES TEST")
    print("=" * 60)
    
    deps = {
        'playwright': 'Playwright browser automation',
        'requests': 'HTTP requests',
        'google.auth': 'Google OAuth (for Gmail API)',
        'googleapiclient': 'Google API Client'
    }
    
    all_ok = True
    for module, desc in deps.items():
        try:
            __import__(module.replace('.', '_'))
            print(f"[OK] {module}: {desc}")
        except ImportError as e:
            print(f"[FAIL] {module}: {desc} - {e}")
            all_ok = False
    
    return all_ok


def test_playwright_browsers():
    """Test Playwright browsers."""
    print("\n" + "=" * 60)
    print("PLAYWRIGHT BROWSERS TEST")
    print("=" * 60)
    
    try:
        from playwright.sync_api import sync_playwright
        p = sync_playwright().start()
        
        # Check Chromium
        try:
            path = p.chromium.executable_path
            print(f"[OK] Chromium path: {path}")
        except Exception as e:
            print(f"[FAIL] Chromium not found: {e}")
            return False
        
        p.stop()
        return True
        
    except Exception as e:
        print(f"[FAIL] Playwright import failed: {e}")
        return False


def main():
    print("\n" + "=" * 60)
    print("GMAIL MCP DIAGNOSTIC REPORT")
    print("=" * 60)
    
    # Test 1: Python dependencies
    deps_ok = test_python_dependencies()
    
    # Test 2: Playwright browsers
    browsers_ok = test_playwright_browsers()
    
    # Test 3: MCP Connection
    session_id = test_mcp_connection()
    
    # Test 4: Browser snapshot (if MCP connected)
    snapshot_ok = test_snapshot(session_id) if session_id else False
    
    # Summary
    print("\n" + "=" * 60)
    print("DIAGNOSTIC SUMMARY")
    print("=" * 60)
    print(f"Python Dependencies: {'[OK]' if deps_ok else '[FAIL]'}")
    print(f"Playwright Browsers: {'[OK]' if browsers_ok else '[FAIL]'}")
    print(f"MCP Connection:      {'[OK]' if session_id else '[FAIL]'}")
    print(f"Browser Snapshot:    {'[OK]' if snapshot_ok else '[SKIP/FAIL]'}")
    print("=" * 60)
    
    if not session_id:
        print("\n[CRITICAL] MCP server is NOT running!")
        print("\nTo fix, run this command in a separate terminal:")
        print("  npx @playwright/mcp@latest --port 8808 --shared-browser-context")
        print("\nThen keep that terminal open while running gmail_mcp_sender.py")
        return 1
    
    if not snapshot_ok:
        print("\n[WARNING] Snapshot test failed. Browser may not be on Gmail page yet.")
        return 1
    
    print("\n[OK] All diagnostic tests passed!")
    print("\nYou can now run:")
    print("  python scripts\\gmail_mcp_sender.py \"to@example.com\" \"Subject\" \"Body\"")
    return 0


if __name__ == "__main__":
    sys.exit(main())
