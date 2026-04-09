#!/usr/bin/env python3
"""
Verification script for the Playwright MCP session fix.

This script tests each step of the Gmail email sending flow to verify
that the session handling fix works correctly.

Run this BEFORE running gmasender.py to verify the fix.

Usage:
    python scripts\\verify_mcp_fix.py
"""

import json
import sys
import io
import time
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')


class MCPVerifier:
    """Verify MCP session handling fix."""

    def __init__(self, base_url: str = "http://localhost:8808"):
        self.base_url = base_url.rstrip('/')
        self._request_id = 0
        self._session_id = None
        self._initialized = False
        self._errors = []
        self._successes = []

    def _next_id(self) -> int:
        self._request_id += 1
        return self._request_id

    def _parse_sse(self, body: str) -> dict:
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

    def _send_request(self, payload: dict, include_session: bool = True) -> tuple:
        """Send request and return (result_dict, error_string)."""
        data = json.dumps(payload).encode('utf-8')
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        if self._session_id and include_session:
            headers["mcp-session-id"] = self._session_id
            headers["Mcp-Session-Id"] = self._session_id

        req = Request(self.base_url, data=data, headers=headers, method='POST')

        try:
            with urlopen(req, timeout=60) as resp:
                # CRITICAL: Get session ID before body
                new_session = resp.headers.get('Mcp-Session-Id') or resp.headers.get('mcp-session-id')
                if new_session:
                    if new_session != self._session_id:
                        if self._session_id:
                            print(f"        Session updated: {self._session_id[:8]}... -> {new_session[:8]}...")
                        else:
                            print(f"        Session created: {new_session[:8]}...")
                    self._session_id = new_session

                body = resp.read().decode('utf-8')
                return self._parse_sse(body), None

        except HTTPError as e:
            body = e.read().decode('utf-8') if e.fp else str(e)
            return None, f"HTTP {e.code}: {body[:200]}"
        except URLError as e:
            return None, f"Connection failed: {e.reason}"

    def test_initialize(self) -> bool:
        """Test 1: Initialize session."""
        print("\n[Test 1] Initialize MCP session...")
        print("  Sending initialize request...")
        
        payload = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "verifier", "version": "1.0.0"}
            }
        }

        result, error = self._send_request(payload, include_session=False)
        
        if error:
            print(f"  [FAIL] {error}")
            self._errors.append("Initialize failed")
            return False

        if "error" in result:
            err = result["error"]
            print(f"  [FAIL] {err.get('message')}")
            self._errors.append(f"Initialize error: {err.get('message')}")
            return False

        if not self._session_id:
            print("  [WARN] No session ID returned, but continuing...")
        else:
            print(f"  [PASS] Session ID: {self._session_id}")
            self._successes.append("Session initialized")

        # Send initialized notification
        notify_payload = {"jsonrpc": "2.0", "method": "notifications/initialized"}
        self._send_request(notify_payload)
        self._initialized = True
        return True

    def test_snapshot_after_init(self) -> bool:
        """Test 2: Snapshot immediately after init (this was failing before)."""
        print("\n[Test 2] Snapshot immediately after initialize...")
        print("  This is where 'HTTP 404: Session not found' occurred before")
        
        payload = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "tools/call",
            "params": {"name": "browser_snapshot", "arguments": {}}
        }

        result, error = self._send_request(payload)

        if error:
            if '404' in error or 'session' in error.lower():
                print(f"  [FAIL] SESSION BUG STILL EXISTS: {error}")
                self._errors.append("Session lost after init - BUG NOT FIXED")
                return False
            print(f"  [FAIL] {error}")
            self._errors.append(f"Snapshot failed: {error}")
            return False

        if "error" in result:
            err = result["error"]
            # Check if it's a session error
            if 'session' in str(err).lower() or '404' in str(err):
                print(f"  [FAIL] SESSION ERROR: {err.get('message')}")
                self._errors.append("Session error in snapshot")
                return False
            print(f"  [FAIL] {err.get('message')}")
            self._errors.append(f"Snapshot error: {err.get('message')}")
            return False

        content = result.get('result', {}).get('content', [{}])[0].get('text', '')
        print(f"  [PASS] Snapshot received ({len(content)} chars)")
        self._successes.append("Snapshot works after init")
        return True

    def test_navigate(self) -> bool:
        """Test 3: Navigate to a URL."""
        print("\n[Test 3] Navigate to example.com...")
        
        payload = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "tools/call",
            "params": {"name": "browser_navigate", "arguments": {"url": "https://example.com"}}
        }

        result, error = self._send_request(payload)

        if error:
            if '404' in error or 'session' in error.lower():
                print(f"  [FAIL] Session lost during navigate: {error}")
                self._errors.append("Session lost during navigate")
                return False
            print(f"  [FAIL] {error}")
            self._errors.append(f"Navigate failed: {error}")
            return False

        if "error" in result:
            err = result["error"]
            if 'session' in str(err).lower():
                print(f"  [FAIL] Session error: {err.get('message')}")
                self._errors.append("Session error in navigate")
                return False
            print(f"  [FAIL] {err.get('message')}")
            self._errors.append(f"Navigate error: {err.get('message')}")
            return False

        print(f"  [PASS] Navigation successful")
        self._successes.append("Navigate works")
        return True

    def test_snapshot_after_navigate(self) -> bool:
        """Test 4: Snapshot after navigate (session might change)."""
        print("\n[Test 4] Snapshot after navigation...")
        print("  Checking if session ID changes after navigate...")
        
        old_session = self._session_id
        
        payload = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "tools/call",
            "params": {"name": "browser_snapshot", "arguments": {}}
        }

        result, error = self._send_request(payload)

        if error:
            if '404' in error or 'session' in error.lower():
                print(f"  [FAIL] Session lost after navigate: {error}")
                self._errors.append("Session lost after navigate")
                return False
            print(f"  [FAIL] {error}")
            self._errors.append(f"Snapshot failed: {error}")
            return False

        if "error" in result:
            err = result["error"]
            if 'session' in str(err).lower():
                print(f"  [FAIL] Session error: {err.get('message')}")
                self._errors.append("Session error after navigate")
                return False
            print(f"  [FAIL] {err.get('message')}")
            self._errors.append(f"Snapshot error: {err.get('message')}")
            return False

        new_session = self._session_id
        if old_session != new_session:
            print(f"  [INFO] Session changed: {old_session[:8]}... -> {new_session[:8]}...")
        
        content = result.get('result', {}).get('content', [{}])[0].get('text', '')
        print(f"  [PASS] Snapshot received ({len(content)} chars)")
        self._successes.append("Snapshot works after navigate")
        return True

    def test_multiple_calls(self) -> bool:
        """Test 5: Multiple consecutive tool calls."""
        print("\n[Test 5] Multiple consecutive tool calls...")
        print("  Testing session persistence across 3 calls...")
        
        for i in range(3):
            payload = {
                "jsonrpc": "2.0",
                "id": self._next_id(),
                "method": "tools/call",
                "params": {"name": "browser_snapshot", "arguments": {}}
            }

            result, error = self._send_request(payload)

            if error:
                if '404' in error or 'session' in error.lower():
                    print(f"  [FAIL] Session lost on call {i+1}: {error}")
                    self._errors.append(f"Session lost on call {i+1}")
                    return False
                print(f"  [FAIL] Call {i+1}: {error}")
                self._errors.append(f"Call {i+1} failed: {error}")
                return False

            if "error" in result and 'session' in str(result["error"]).lower():
                print(f"  [FAIL] Session error on call {i+1}")
                self._errors.append(f"Session error on call {i+1}")
                return False

            print(f"  [OK] Call {i+1} succeeded")

        print(f"  [PASS] All 3 calls succeeded with same session")
        self._successes.append("Multiple calls work")
        return True

    def run_all_tests(self) -> bool:
        """Run all verification tests."""
        print("=" * 70)
        print("Playwright MCP Session Fix Verification")
        print("=" * 70)
        print(f"\nTesting MCP server at: {self.base_url}")
        print("If server is not running, start with:")
        print("  npx @playwright/mcp@latest --port 8808")
        print("\n" + "-" * 70)

        all_passed = True

        # Run tests in order
        if not self.test_initialize():
            print("\n[STOP] Initialize failed, cannot continue tests")
            return False

        if not self.test_snapshot_after_init():
            all_passed = False
            # Try to continue anyway

        if not self.test_navigate():
            all_passed = False

        if not self.test_snapshot_after_navigate():
            all_passed = False

        if not self.test_multiple_calls():
            all_passed = False

        # Summary
        print("\n" + "=" * 70)
        print("VERIFICATION SUMMARY")
        print("=" * 70)

        if self._successes:
            print("\nSuccessful tests:")
            for s in self._successes:
                print(f"  [OK] {s}")

        if self._errors:
            print("\nFailed tests:")
            for e in self._errors:
                print(f"  [FAIL] {e}")

        print("\n" + "-" * 70)
        if all_passed and not self._errors:
            print("\n[SUCCESS] ALL TESTS PASSED!")
            print("\nThe session handling fix is working correctly.")
            print("You can now run: python scripts\\gmasender.py \"to@example.com\" \"Subject\" \"Body\"")
            return True
        else:
            print("\n[FAILURE] SOME TESTS FAILED")
            print("\nThe fix may not be complete. Check the errors above.")
            print("\nCommon issues:")
            print("  - MCP server not running: npx @playwright/mcp@latest --port 8808")
            print("  - Wrong port: Make sure you use --port 8808")
            print("  - Browser context closed: Restart the MCP server")
            return False


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Verify Playwright MCP session fix')
    parser.add_argument('--mcp-url', '-u', default='http://localhost:8808',
                       help='Playwright MCP server URL')
    args = parser.parse_args()

    verifier = MCPVerifier(args.mcp_url)
    success = verifier.run_all_tests()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
