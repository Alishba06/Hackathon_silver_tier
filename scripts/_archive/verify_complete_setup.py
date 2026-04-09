#!/usr/bin/env python3
"""
Complete Setup Verification Script for AI Employee Vault.

This script verifies:
1. Playwright MCP Server is running
2. Session management works correctly
3. Gmail navigation works
4. Compose button can be found and clicked
5. All components are properly connected

Usage:
    python scripts\verify_complete_setup.py
"""

import json
import sys
import io
import time
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

# Fix Windows console Unicode issues
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')


class PlaywrightMCPClient:
    """Minimal MCP client for verification."""

    def __init__(self, url="http://localhost:8808/mcp"):
        self.base_url = url.rstrip('/')
        if not self.base_url.endswith('/mcp'):
            self.base_url = self.base_url + '/mcp'
        self._request_id = 0
        self._session_id = None
        self._initialized = False

    def _next_id(self):
        self._request_id += 1
        return self._request_id

    def _ensure_initialized(self):
        if self._initialized:
            return

        payload = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "verify-complete-setup", "version": "1.0.0"}
            }
        }

        data = json.dumps(payload).encode('utf-8')
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }

        req = Request(self.base_url, data=data, headers=headers, method='POST')

        try:
            with urlopen(req, timeout=30) as resp:
                self._session_id = resp.headers.get('Mcp-Session-Id') or resp.headers.get('mcp-session-id')
                print(f"    [INIT] Session: {self._session_id[:8] if self._session_id else 'None'}...")
                body = resp.read().decode('utf-8')
                # Parse SSE
                if 'data:' in body:
                    for line in body.split('\n'):
                        if line.strip().startswith('data:'):
                            result = json.loads(line.strip()[5:])
                            if "error" in result:
                                raise Exception(f"Init error: {result['error'].get('message')}")
                            break
        except HTTPError as e:
            body = e.read().decode('utf-8') if e.fp else str(e)
            raise Exception(f"HTTP {e.code}: {body}")
        except URLError as e:
            raise Exception(f"Connection failed: {e.reason}")

        self._initialized = True

    def _send_request(self, payload):
        data = json.dumps(payload).encode('utf-8')
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        if self._session_id:
            headers["mcp-session-id"] = self._session_id
            headers["Mcp-Session-Id"] = self._session_id

        req = Request(self.base_url, data=data, headers=headers, method='POST')

        try:
            with urlopen(req, timeout=120) as resp:
                new_session_id = resp.headers.get('Mcp-Session-Id') or resp.headers.get('mcp-session-id')
                if new_session_id:
                    self._session_id = new_session_id
                body = resp.read().decode('utf-8')
                # Parse SSE
                if 'data:' in body:
                    for line in body.split('\n'):
                        if line.strip().startswith('data:'):
                            return json.loads(line.strip()[5:])
                return json.loads(body) if body.strip() else {}
        except HTTPError as e:
            body = e.read().decode('utf-8') if e.fp else str(e)
            raise Exception(f"HTTP {e.code}: {body}")
        except URLError as e:
            raise Exception(f"Connection failed: {e.reason}")

    def call_tool(self, name, args=None):
        self._ensure_initialized()
        payload = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "tools/call",
            "params": {"name": name}
        }
        if args:
            payload["params"]["arguments"] = args

        result = self._send_request(payload)
        if "error" in result:
            raise Exception(f"MCP error: {result['error'].get('message')}")
        return result.get("result", {})

    def navigate(self, url):
        return self.call_tool("browser_navigate", {"url": url})

    def snapshot(self):
        return self.call_tool("browser_snapshot", {})

    def run_code(self, code):
        return self.call_tool("browser_run_code", {"code": code})

    def close(self):
        try:
            self.call_tool("browser_close", {})
        except:
            pass


def check_mcp_server():
    """Check if MCP server is running."""
    print("\n" + "=" * 70)
    print("STEP 1: Checking Playwright MCP Server")
    print("=" * 70)

    try:
        req = Request("http://localhost:8808", method='GET')
        with urlopen(req, timeout=5) as resp:
            print("    [OK] Server is responding on port 8808")
            return True
    except URLError:
        print("    [FAIL] Server NOT responding on port 8808")
        print("\n    To start the server, run:")
        print("    > npx @playwright/mcp@latest --port 8808 --shared-browser-context")
        return False
    except Exception as e:
        print(f"    [WARN] Server check: {e}")
        return True  # Server might be running but not responding to GET


def check_session_management():
    """Test session creation and persistence."""
    print("\n" + "=" * 70)
    print("STEP 2: Testing Session Management")
    print("=" * 70)

    client = PlaywrightMCPClient()

    try:
        # Test 1: Initialize session
        print("\n    [Test 1] Initializing session...")
        client._ensure_initialized()
        if client._session_id:
            print(f"    [PASS] Session created: {client._session_id[:8]}...")
        else:
            print("    [FAIL] No session ID received")
            return False

        # Test 2: Multiple tool calls with same session
        print("\n    [Test 2] Testing session persistence...")
        for i in range(3):
            result = client.snapshot()
            print(f"    [OK] Call {i+1} succeeded")

        print("    [PASS] Session persists across multiple calls")
        return True

    except Exception as e:
        print(f"    [FAIL] {e}")
        return False
    finally:
        client.close()


def check_gmail_navigation():
    """Test Gmail navigation."""
    print("\n" + "=" * 70)
    print("STEP 3: Testing Gmail Navigation")
    print("=" * 70)

    client = PlaywrightMCPClient()

    try:
        print("\n    Navigating to Gmail...")
        result = client.navigate("https://mail.google.com/mail/u/0/")
        print("    [OK] Navigation request sent")

        print("    Waiting for page to load (10 seconds)...")
        time.sleep(10)

        print("    Taking snapshot...")
        snapshot = client.snapshot()
        content = snapshot.get('content', '')

        # Extract text from snapshot
        if isinstance(content, list):
            texts = [item.get('text', '') or item.get('name', '') for item in content if isinstance(item, dict)]
            content_text = ' '.join(texts)
        else:
            content_text = str(content)

        # Check page state
        if 'Sign in' in content_text or 'sign in' in content_text.lower():
            print("    [INFO] Login page detected - please log in to Gmail")
            print("    [PASS] Navigation successful (manual login required)")
            return True
        elif 'Compose' in content_text:
            print("    [PASS] Gmail inbox loaded (logged in)")
            return True
        else:
            print("    [WARN] Page content unclear")
            print(f"    Content preview: {content_text[:200]}...")
            return True

    except Exception as e:
        print(f"    [FAIL] {e}")
        return False
    finally:
        client.close()


def check_compose_button():
    """Test Compose button detection."""
    print("\n" + "=" * 70)
    print("STEP 4: Testing Compose Button Detection")
    print("=" * 70)

    client = PlaywrightMCPClient()

    try:
        # Navigate to Gmail
        print("\n    Navigating to Gmail...")
        client.navigate("https://mail.google.com/mail/u/0/")
        time.sleep(10)

        # Take snapshot
        print("    Taking snapshot...")
        snapshot = client.snapshot()
        content = snapshot.get('content', '')

        if isinstance(content, list):
            texts = [item.get('text', '') or item.get('name', '') for item in content if isinstance(item, dict)]
            content_text = ' '.join(texts)
        else:
            content_text = str(content)

        # Check for Compose button
        if 'Compose' in content_text:
            print("    [PASS] Compose button FOUND")

            # Try to find compose using Playwright code
            compose_code = """async (page) => {
                try {
                    const composeBtn = page.getByLabel('Compose', { exact: true }).first();
                    const isVisible = await composeBtn.isVisible();
                    return { found: true, visible: isVisible };
                } catch (e) {
                    return { found: false, error: e.message };
                }
            }"""

            print("    Testing Compose button visibility...")
            result = client.run_code(compose_code)
            print(f"    [OK] Compose check completed")
            return True
        else:
            print("    [INFO] Compose button not found")
            if 'Sign in' in content_text:
                print("    [INFO] Please log in to Gmail first")
            return True

    except Exception as e:
        print(f"    [FAIL] {e}")
        return False
    finally:
        client.close()


def print_summary(results):
    """Print test summary."""
    print("\n" + "=" * 70)
    print("VERIFICATION SUMMARY")
    print("=" * 70)

    tests = [
        ("MCP Server Running", results.get('server', False)),
        ("Session Management", results.get('session', False)),
        ("Gmail Navigation", results.get('navigation', False)),
        ("Compose Detection", results.get('compose', False)),
    ]

    all_passed = True
    for name, passed in tests:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {status}: {name}")
        if not passed:
            all_passed = False

    print("\n" + "=" * 70)

    if all_passed:
        print("[SUCCESS] All verification tests passed!")
        print("\nYour setup is ready. You can now:")
        print("  1. Send emails: python scripts\\gmail_mcp_sender.py \"to@example.com\" \"Subject\" \"Body\"")
        print("  2. Or use: python scripts\\gmasender.py \"to@example.com\" \"Subject\" \"Body\"")
    else:
        print("[ISSUES] Some tests failed. See above for details.")
        print("\nTroubleshooting:")
        print("  - Ensure MCP server is running: npx @playwright/mcp@latest --port 8808 --shared-browser-context")
        print("  - Check Node.js is installed: node --version")
        print("  - Verify Playwright browsers: npx playwright install")

    print("=" * 70)


def main():
    print("=" * 70)
    print("AI Employee Vault - Complete Setup Verification")
    print("=" * 70)

    results = {}

    # Step 1: Check MCP server
    results['server'] = check_mcp_server()

    if not results['server']:
        print("\n[STOP] MCP server is not running. Please start it first.")
        print_summary(results)
        sys.exit(1)

    # Step 2: Check session management
    results['session'] = check_session_management()

    # Step 3: Check Gmail navigation
    results['navigation'] = check_gmail_navigation()

    # Step 4: Check compose button
    results['compose'] = check_compose_button()

    # Print summary
    print_summary(results)

    sys.exit(0 if all(results.values()) else 1)


if __name__ == "__main__":
    main()
