#!/usr/bin/env python3
"""
Gmail Sender - Debug Version

This version shows detailed debug information about Gmail's DOM structure
to help identify the correct selectors for the Send button.

Usage:
    python scripts\\gmasender_debug.py "recipient@example.com" "Subject" "Email body"
"""

import argparse
import json
import sys
import io
import time
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')


class MCPClientError(Exception):
    pass


class PlaywrightMCPClient:
    def __init__(self, base_url: str = "http://localhost:8808"):
        self.base_url = base_url.rstrip('/')
        self._request_id = 0
        self._session_id = None
        self._initialized = False
        self._reinitializing = False

    def _next_id(self) -> int:
        self._request_id += 1
        return self._request_id

    def _extract_session_id(self, headers) -> str:
        session_id = headers.get('Mcp-Session-Id') or headers.get('mcp-session-id')
        if session_id and session_id != self._session_id:
            self._session_id = session_id
        return session_id

    def _parse_sse_response(self, body: str) -> dict:
        body = body.strip()
        if not body:
            return {}
        for line in body.split('\n'):
            line = line.strip()
            if line.startswith('data:'):
                json_str = line[5:].strip()
                if json_str and json_str != '[DONE]':
                    try:
                        return json.loads(json_str)
                    except json.JSONDecodeError:
                        continue
        try:
            return json.loads(body)
        except json.JSONDecodeError:
            return {}

    def _ensure_initialized(self, force: bool = False):
        if self._initialized and not force:
            return
        payload = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "gmasender", "version": "1.0.0"}
            }
        }
        data = json.dumps(payload).encode('utf-8')
        headers = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}
        req = Request(self.base_url, data=data, headers=headers, method='POST')
        try:
            with urlopen(req, timeout=30) as resp:
                self._session_id = self._extract_session_id(resp.headers)
                body = resp.read().decode('utf-8')
                result = self._parse_sse_response(body)
                if "error" in result:
                    raise MCPClientError(f"Initialize failed: {result['error'].get('message')}")
        except HTTPError as e:
            body = e.read().decode('utf-8') if e.fp else str(e)
            raise MCPClientError(f"HTTP {e.code}: {body}")
        except URLError as e:
            raise MCPClientError(f"Connection failed: {e.reason}")
        self._initialized = True

    def _send_request(self, payload: dict, retry: bool = True) -> dict:
        self._ensure_initialized()
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
                new_session_id = self._extract_session_id(resp.headers)
                if new_session_id:
                    self._session_id = new_session_id
                body = resp.read().decode('utf-8')
                return self._parse_sse_response(body)
        except HTTPError as e:
            body = e.read().decode('utf-8') if e.fp else str(e)
            if e.code == 404 and 'session' in body.lower() and retry:
                self._initialized = False
                return self._send_request(payload, retry=False)
            raise MCPClientError(f"HTTP {e.code}: {body}")
        except URLError as e:
            raise MCPClientError(f"Connection failed: {e.reason}")

    def call_tool(self, name: str, arguments: dict = None) -> dict:
        payload = {"jsonrpc": "2.0", "id": self._next_id(), "method": "tools/call", "params": {"name": name}}
        if arguments:
            payload["params"]["arguments"] = arguments
        result = self._send_request(payload)
        if "error" in result:
            raise MCPClientError(f"MCP error: {result['error'].get('message')}")
        return result.get("result", {})

    def navigate(self, url: str) -> dict:
        return self.call_tool("browser_navigate", {"url": url})

    def run_code(self, code: str) -> dict:
        return self.call_tool("browser_run_code", {"code": code})

    def snapshot(self) -> dict:
        return self.call_tool("browser_snapshot", {})


def escape_js_string(s: str) -> str:
    return (s.replace('\\', '\\\\').replace("'", "\\'").replace('"', '\\"')
            .replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t'))


def debug_gmail_structure(client: PlaywrightMCPClient):
    """Debug: Print Gmail's DOM structure to find correct selectors."""
    
    print("\n" + "=" * 60)
    print("DEBUG: Analyzing Gmail Page Structure")
    print("=" * 60)
    
    # Navigate to Gmail
    print("\nNavigating to Gmail...")
    client.navigate("https://mail.google.com/mail/u/0/")
    time.sleep(5)
    
    # Get snapshot
    print("Getting page snapshot...")
    snapshot = client.snapshot()
    print("\n--- SNAPSHOT ---")
    print(str(snapshot)[:3000])
    
    # Run debug code to find compose and send buttons
    debug_code = """async (page) => {
        const results = {};
        
        // Find Compose button
        try {
            const composeSelectors = [
                'div[aria-label="Compose"]',
                'div[role="button"]:has-text("Compose")',
                'a[href="#compose"]',
                '[data-tooltip="Compose"]'
            ];
            results.compose = [];
            for (const selector of composeSelectors) {
                const elements = page.locator(selector);
                const count = await elements.count();
                if (count > 0) {
                    results.compose.push({ selector, count });
                }
            }
        } catch (e) {
            results.composeError = e.message;
        }
        
        // Wait for compose window (if we can click compose)
        results.composeWindow = {};
        try {
            // Try to open compose
            const composeBtn = page.getByLabel('Compose', { exact: true }).first();
            if (await composeBtn.count() > 0) {
                await composeBtn.click();
                await page.waitForTimeout(2000);
                
                // Find To, Subject, Body fields
                const fieldSelectors = {
                    'to': 'textarea[name="to"], div[aria-label="To"], input[name="to"]',
                    'subject': 'input[name="subjectbox"], div[aria-label="Subject"], input[placeholder*="Subject"]',
                    'body': 'div[aria-label="Message body"], div[contenteditable="true"][aria-label*="body"]',
                    'send': 'div[aria-label="Send"], button:has-text("Send"), div[role="button"][aria-label*="Send"]'
                };
                
                for (const [field, selector] of Object.entries(fieldSelectors)) {
                    try {
                        const elements = page.locator(selector);
                        const count = await elements.count();
                        const isVisible = count > 0 ? await elements.first().isVisible() : false;
                        results.composeWindow[field] = { selector, count, visible: isVisible };
                    } catch (e) {
                        results.composeWindow[field] = { error: e.message };
                    }
                }
                
                // Get the HTML of send button area
                try {
                    const sendBtn = page.locator('div[aria-label="Send"]').first();
                    if (await sendBtn.count() > 0) {
                        results.sendButtonHTML = await sendBtn.first().evaluate(el => el.outerHTML);
                        results.sendButtonAttributes = await sendBtn.first().evaluate(el => {
                            const attrs = {};
                            for (const attr of el.attributes) {
                                attrs[attr.name] = attr.value;
                            }
                            return attrs;
                        });
                    }
                } catch (e) {
                    results.sendButtonHTML = 'Not found: ' + e.message;
                }
            }
        } catch (e) {
            results.composeWindowError = e.message;
        }
        
        return results;
    }"""
    
    print("\nRunning debug analysis...")
    result = client.run_code(debug_code)
    
    # Parse and display results
    if result:
        content_list = result.get('content', [])
        for item in content_list:
            text = item.get('text', '')
            if '### Result' in text:
                json_start = text.find('{', text.find('### Result'))
                if json_start != -1:
                    brace_count = 0
                    json_end = json_start
                    for i, char in enumerate(text[json_start:], json_start):
                        if char == '{':
                            brace_count += 1
                        elif char == '}':
                            brace_count -= 1
                            if brace_count == 0:
                                json_end = i + 1
                                break
                    if json_end > json_start:
                        try:
                            debug_data = json.loads(text[json_start:json_end])
                            print("\n--- DEBUG RESULTS ---")
                            print(json.dumps(debug_data, indent=2))
                        except json.JSONDecodeError:
                            print("Could not parse debug results")
    
    print("\n" + "=" * 60)
    print("DEBUG complete. Check the output above for correct selectors.")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description='Debug Gmail structure for automation')
    parser.add_argument('--mcp-url', '-u', default='http://localhost:8808',
                       help='Playwright MCP server URL')
    args = parser.parse_args()

    print(f"Connecting to MCP server at {args.mcp_url}...")
    client = PlaywrightMCPClient(args.mcp_url)

    try:
        debug_gmail_structure(client)
    except MCPClientError as e:
        print(f"\n[ERROR] {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
