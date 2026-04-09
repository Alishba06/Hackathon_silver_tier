#!/usr/bin/env python3
"""
Exact copy of verify_mcp_fix.py but with more debug output to find the root cause.
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

    def _send_request(self, payload: dict, include_session: bool = True, debug: bool = False) -> tuple:
        """Send request and return (result_dict, error_string)."""
        data = json.dumps(payload).encode('utf-8')
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        if self._session_id and include_session:
            headers["mcp-session-id"] = self._session_id
            headers["Mcp-Session-Id"] = self._session_id

        if debug:
            print(f"        [DEBUG] Sending with session: {self._session_id[:8] if self._session_id else 'None'}...")

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
                if debug:
                    print(f"        [DEBUG] Response body length: {len(body)}")
                return self._parse_sse(body), None

        except HTTPError as e:
            # Get session from error response headers too!
            error_headers = dict(e.headers) if hasattr(e, 'headers') and e.headers else {}
            error_session = error_headers.get('Mcp-Session-Id') or error_headers.get('mcp-session-id')
            if error_session:
                print(f"        [DEBUG] Session in ERROR response: {error_session[:8]}...")
                if error_session != self._session_id:
                    self._session_id = error_session
                    print(f"        [DEBUG] Session updated from error response!")
            
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

        result, error = self._send_request(payload, include_session=False, debug=True)

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
        self._send_request(notify_payload, debug=True)
        self._initialized = True
        return True

    def test_snapshot_after_init(self) -> bool:
        """Test 2: Snapshot immediately after init."""
        print("\n[Test 2] Snapshot immediately after initialize...")

        payload = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "tools/call",
            "params": {"name": "browser_snapshot", "arguments": {}}
        }

        result, error = self._send_request(payload, debug=True)

        if error:
            if '404' in error or 'session' in error.lower():
                print(f"  [FAIL] SESSION BUG: {error}")
                self._errors.append("Session lost after init")
                return False
            print(f"  [FAIL] {error}")
            self._errors.append(f"Snapshot failed: {error}")
            return False

        if "error" in result:
            err = result["error"]
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

        result, error = self._send_request(payload, debug=True)

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
        print(f"  Session after navigate: {self._session_id[:8] if self._session_id else 'None'}...")
        self._successes.append("Navigate works")
        return True

    def test_snapshot_after_navigate(self) -> bool:
        """Test 4: Snapshot after navigate."""
        print("\n[Test 4] Snapshot after navigation...")
        print(f"  Current session: {self._session_id[:8] if self._session_id else 'None'}...")

        payload = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "tools/call",
            "params": {"name": "browser_snapshot", "arguments": {}}
        }

        result, error = self._send_request(payload, debug=True)

        if error:
            print(f"  Raw error: {error}")
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

        content = result.get('result', {}).get('content', [{}])[0].get('text', '')
        print(f"  [PASS] Snapshot received ({len(content)} chars)")
        self._successes.append("Snapshot works after navigate")
        return True


def main():
    print("=" * 70)
    print("Debug Verification - With Extra Logging")
    print("=" * 70)

    verifier = MCPVerifier("http://localhost:8808")

    # Run tests
    if not verifier.test_initialize():
        print("\n[STOP] Initialize failed")
        return False

    if not verifier.test_snapshot_after_init():
        print("\n[STOP] Snapshot after init failed")
        return False

    if not verifier.test_navigate():
        print("\n[STOP] Navigate failed")
        return False

    if not verifier.test_snapshot_after_navigate():
        print("\n[FAIL] Snapshot after navigate failed")
        return False

    print("\n" + "=" * 70)
    print("[SUCCESS] ALL TESTS PASSED!")
    print("=" * 70)
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
