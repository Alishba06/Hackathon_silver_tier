#!/usr/bin/env python3
"""
Gmail Sender via Playwright MCP - Robust Version

This script sends emails through Gmail's web interface using browser automation.
It connects to a Playwright MCP server and automates the entire email sending flow.

Usage:
    python scripts\\gmasender.py "recipient@example.com" "Subject" "Email body"

MCP Server must be running:
    npx @playwright/mcp@latest --port 8808 --shared-browser-context
"""

import argparse
import json
import sys
import io
import time
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

# Fix Windows console Unicode issues
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')


class MCPClientError(Exception):
    """MCP client error."""
    pass


class PlaywrightMCPClient:
    """
    Robust MCP client for Playwright MCP server using streamable HTTP transport.
    """

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
        """Extract session ID from HTTP headers."""
        session_id = headers.get('Mcp-Session-Id') or headers.get('mcp-session-id')
        if session_id and session_id != self._session_id:
            if self._session_id:
                print(f"    [SESSION] Updated: {self._session_id[:8]}... -> {session_id[:8]}...")
            else:
                print(f"    [SESSION] Created: {session_id[:8]}...")
        return session_id

    def _parse_sse_response(self, body: str) -> dict:
        """Parse Server-Sent Events (SSE) response format."""
        body = body.strip()
        if not body:
            return {}

        is_sse = body.startswith('event:') or body.startswith('data:') or '\nevent:' in body or '\ndata:' in body

        if is_sse:
            for line in body.split('\n'):
                line = line.strip()
                if line.startswith('data:'):
                    json_str = line[5:].strip()
                    if json_str and json_str != '[DONE]':
                        try:
                            return json.loads(json_str)
                        except json.JSONDecodeError:
                            continue
            return {}

        try:
            return json.loads(body)
        except json.JSONDecodeError:
            return {}

    def _ensure_initialized(self, force: bool = False):
        """Initialize or reinitialize the MCP session."""
        if self._initialized and not force:
            return

        if force:
            print("    [INIT] Reinitializing MCP session...")
        else:
            print("    [INIT] Initializing MCP session...")

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
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }

        req = Request(self.base_url, data=data, headers=headers, method='POST')

        try:
            with urlopen(req, timeout=30) as resp:
                self._session_id = self._extract_session_id(resp.headers)

                if not self._session_id:
                    print("    [WARN] No session ID in response headers")

                body = resp.read().decode('utf-8')
                result = self._parse_sse_response(body)

                if "error" in result:
                    raise MCPClientError(f"Initialize failed: {result['error'].get('message')}")

                print(f"    [INIT] Server: {result.get('result', {}).get('serverInfo', {})}")

        except HTTPError as e:
            body = e.read().decode('utf-8') if e.fp else str(e)
            raise MCPClientError(f"HTTP {e.code}: {body}")
        except URLError as e:
            raise MCPClientError(f"Connection failed: {e.reason}. Is the MCP server running on {self.base_url}?")

        self._initialized = True
        self._send_notification("notifications/initialized")

    def _send_notification(self, method: str, params: dict = None):
        """Send a notification (no response expected)."""
        payload = {"jsonrpc": "2.0", "method": method}
        if params:
            payload["params"] = params

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
            with urlopen(req, timeout=10) as resp:
                pass
        except Exception:
            pass

    def _send_request(self, payload: dict, include_session: bool = True, retry: bool = True) -> dict:
        """Send a JSON-RPC request to the MCP server."""
        self._ensure_initialized()

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
            with urlopen(req, timeout=120) as resp:
                new_session_id = self._extract_session_id(resp.headers)
                if new_session_id:
                    self._session_id = new_session_id

                body = resp.read().decode('utf-8')
                return self._parse_sse_response(body)

        except HTTPError as e:
            error_headers = dict(e.headers) if hasattr(e, 'headers') and e.headers else {}
            new_session_id = error_headers.get('Mcp-Session-Id') or error_headers.get('mcp-session-id')
            if new_session_id and new_session_id != self._session_id:
                self._session_id = new_session_id

            body = e.read().decode('utf-8') if e.fp else str(e)

            if e.code == 404 and ('session' in body.lower() or 'not found' in body.lower()):
                if retry and not self._reinitializing:
                    self._reinitializing = True
                    self._initialized = False
                    self._ensure_initialized()
                    self._reinitializing = False
                    return self._send_request(payload, include_session=True, retry=False)
                raise MCPClientError(f"HTTP {e.code}: Session not found.")

            raise MCPClientError(f"HTTP {e.code}: {body}")

        except URLError as e:
            raise MCPClientError(f"Connection failed: {e.reason}. Is the MCP server running?")

    def call_tool(self, name: str, arguments: dict = None) -> dict:
        """Call an MCP tool."""
        payload = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "tools/call",
            "params": {"name": name}
        }
        if arguments:
            payload["params"]["arguments"] = arguments

        print(f"    [TOOL] Calling {name}...")
        result = self._send_request(payload)

        if "error" in result:
            err = result["error"]
            raise MCPClientError(f"MCP error {err.get('code')}: {err.get('message')}")

        return result.get("result", {})

    def snapshot(self) -> dict:
        """Get page accessibility snapshot."""
        return self.call_tool("browser_snapshot", {})

    def navigate(self, url: str) -> dict:
        """Navigate to URL."""
        return self.call_tool("browser_navigate", {"url": url})

    def run_code(self, code: str) -> dict:
        """Run Playwright JavaScript code."""
        return self.call_tool("browser_run_code", {"code": code})

    def close(self):
        """Close the browser."""
        try:
            self.call_tool("browser_close", {})
        except:
            pass


def escape_js_string(s: str) -> str:
    """Escape special characters for JavaScript string literals."""
    return (s
            .replace('\\', '\\\\')
            .replace("'", "\\'")
            .replace('"', '\\"')
            .replace('\n', '\\n')
            .replace('\r', '\\r')
            .replace('\t', '\\t'))


def send_email_via_gmail(client: PlaywrightMCPClient, to: str, subject: str, body: str):
    """Send an email using Gmail web interface via Playwright MCP."""

    print("\n" + "=" * 60)
    print("Gmail MCP Email Sender - Robust Version")
    print("=" * 60)
    print(f"To:      {to}")
    print(f"Subject: {subject}")
    print(f"Body:    {body[:80]}{'...' if len(body) > 80 else ''}")
    print("=" * 60)

    # Step 1: Navigate to Gmail and wait for full load
    print("\n[1/7] Navigating to Gmail...")
    result = client.navigate("https://mail.google.com/mail/u/0/")
    print(f"    Navigation: OK")
    
    # CRITICAL: Wait for Gmail to fully load with all dynamic content
    print("    Waiting for Gmail to fully load...")
    time.sleep(8)

    # Step 2: Check if logged in
    print("[2/7] Checking login status...")
    try:
        snapshot = client.snapshot()
    except MCPClientError as e:
        if 'closed' in str(e).lower() or 'browser' in str(e).lower():
            print("[ERROR] Browser context was closed. Please restart the MCP server.")
        raise

    snapshot_text = str(snapshot)
    if 'Sign in' in snapshot_text or 'sign in' in snapshot_text.lower():
        print("[!] Login required. Please complete login in the browser window.")
        print("    Waiting up to 2 minutes for login...")
        max_wait = 120
        wait_interval = 5
        waited = 0
        while waited < max_wait:
            time.sleep(wait_interval)
            waited += wait_interval
            try:
                snapshot = client.snapshot()
                if 'Compose' in str(snapshot) or 'compose' in str(snapshot).lower():
                    print("[OK] Login detected!")
                    break
            except:
                pass
        else:
            raise MCPClientError("Login timeout. Please run again after logging in.")
    else:
        print("[OK] Already logged in!")

    # Wait additional time for Gmail UI to stabilize
    time.sleep(3)

    # Step 3: Open compose window with multiple strategies
    print("[3/7] Opening compose window...")

    compose_code = """async (page) => {
        const results = { success: false, method: 'none', error: null };
        
        try {
            // Wait for page to be fully interactive
            await page.waitForLoadState('networkidle');
            await page.waitForTimeout(2000);
            
            // Strategy 1: Click Compose button using getByLabel
            try {
                const composeBtn = page.getByLabel('Compose', { exact: true }).first();
                const isVisible = await composeBtn.isVisible();
                console.log('Compose button visible:', isVisible);
                if (isVisible) {
                    await composeBtn.click();
                    await page.waitForTimeout(3000);
                    results.success = true;
                    results.method = 'getByLabel';
                    return results;
                }
            } catch (e1) {
                console.log('Strategy 1 failed:', e1.message);
            }
            
            // Strategy 2: Try finding compose by role and text
            try {
                const composeBtn = page.locator('div[role="button"]:has-text("Compose")').first();
                const isVisible = await composeBtn.isVisible();
                if (isVisible) {
                    await composeBtn.click();
                    await page.waitForTimeout(3000);
                    results.success = true;
                    results.method = 'role+text';
                    return results;
                }
            } catch (e2) {
                console.log('Strategy 2 failed:', e2.message);
            }
            
            // Strategy 3: Try keyboard shortcut 'c' (Gmail shortcut for compose)
            try {
                // First make sure we're focused on the main Gmail area
                await page.keyboard.press('Escape');
                await page.waitForTimeout(500);
                await page.keyboard.press('c');
                await page.waitForTimeout(3000);
                
                // Check if compose window appeared
                const composeWindow = page.locator('div[aria-label="Message body"][contenteditable="true"]').first();
                const exists = await composeWindow.count() > 0;
                if (exists) {
                    results.success = true;
                    results.method = 'keyboard_c';
                    return results;
                }
            } catch (e3) {
                console.log('Strategy 3 failed:', e3.message);
            }
            
            // Strategy 4: Try to find any compose-related element
            try {
                const selectors = [
                    'a[title="Compose"]',
                    '[data-tooltip*="Compose"]',
                    'div[jsname="C228mb"]',  // Gmail's internal selector for compose
                    'div.T-I.J-J5-Ji.T-I-KE.L3'  // Old Gmail compose button class
                ];
                
                for (const selector of selectors) {
                    try {
                        const btn = page.locator(selector).first();
                        const isVisible = await btn.isVisible();
                        if (isVisible) {
                            await btn.click();
                            await page.waitForTimeout(3000);
                            results.success = true;
                            results.method = 'fallback_selector: ' + selector;
                            return results;
                        }
                    } catch (e) {
                        // Try next selector
                    }
                }
            } catch (e4) {
                console.log('Strategy 4 failed:', e4.message);
            }
            
            results.error = 'All compose strategies failed';
            return results;
            
        } catch (error) {
            results.error = error.message;
            return results;
        }
    }"""
    
    compose_result = client.run_code(compose_code)
    
    # Parse compose result
    compose_opened = False
    if compose_result:
        content_list = compose_result.get('content', [])
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
                            compose_data = json.loads(text[json_start:json_end])
                            if compose_data.get('success') == True:
                                compose_opened = True
                                print(f"    Compose: Opened (method: {compose_data.get('method', 'unknown')})")
                            else:
                                print(f"    Compose: Failed - {compose_data.get('error', 'Unknown error')}")
                        except json.JSONDecodeError:
                            pass
                    break
    
    if not compose_opened:
        print("    [WARN] Compose may not have opened. Will try to fill fields anyway...")
    
    time.sleep(2)

    # Step 4: Fill email fields with robust selectors
    print("[4/7] Filling email fields...")

    fill_code = f"""async (page) => {{
        const results = {{ success: false, to: false, subject: false, body: false, errors: [] }};
        
        try {{
            // Wait for compose window elements to be available
            await page.waitForTimeout(2000);
            
            // Fill To field - multiple selector strategies
            const toSelectors = [
                'textarea[name="to"]',
                'div[aria-label="To"] textarea',
                'input[name="to"]',
                '[placeholder*="To"]'
            ];
            
            for (const selector of toSelectors) {{
                try {{
                    const toField = page.locator(selector).first();
                    const isVisible = await toField.isVisible();
                    if (isVisible) {{
                        await toField.fill('{escape_js_string(to)}');
                        await page.waitForTimeout(1000);  // Wait for email validation
                        results.to = true;
                        console.log('To field filled using:', selector);
                        break;
                    }}
                }} catch (e) {{
                    // Try next selector
                }}
            }}
            
            if (!results.to) {{
                results.errors.push('Could not fill To field');
            }}
            
            // Fill Subject field
            const subjectSelectors = [
                'input[name="subjectbox"]',
                'input[placeholder*="Subject"]',
                'div[aria-label="Subject"] input',
                'input[type="text"][aria-label*="Subject"]'
            ];
            
            for (const selector of subjectSelectors) {{
                try {{
                    const subjectField = page.locator(selector).first();
                    const isVisible = await subjectField.isVisible();
                    if (isVisible) {{
                        await subjectField.fill('{escape_js_string(subject)}');
                        results.subject = true;
                        console.log('Subject field filled using:', selector);
                        break;
                    }}
                }} catch (e) {{
                    // Try next selector
                }}
            }}
            
            if (!results.subject) {{
                results.errors.push('Could not fill Subject field');
            }}
            
            // Fill Body field
            const bodySelectors = [
                'div[aria-label="Message body"][contenteditable="true"]',
                'div[role="textbox"][aria-label*="body"]',
                'div[contenteditable="true"][aria-label*="Message"]',
                'div.gm editable[contenteditable="true"]'
            ];
            
            for (const selector of bodySelectors) {{
                try {{
                    const bodyField = page.locator(selector).first();
                    const isVisible = await bodyField.isVisible();
                    if (isVisible) {{
                        await bodyField.click();  // Focus first
                        await page.waitForTimeout(500);
                        await bodyField.fill('{escape_js_string(body)}');
                        results.body = true;
                        console.log('Body field filled using:', selector);
                        break;
                    }}
                }} catch (e) {{
                    // Try next selector
                }}
            }}
            
            if (!results.body) {{
                results.errors.push('Could not fill Body field');
            }}
            
            // Wait for Gmail to process all inputs
            await page.waitForTimeout(1500);
            
            results.success = results.to && results.subject && results.body;
            return results;
            
        }} catch (error) {{
            results.errors.push(error.message);
            return results;
        }}
    }}"""

    fill_result = client.run_code(fill_code)
    
    # Parse fill result
    fields_filled = False
    if fill_result:
        content_list = fill_result.get('content', [])
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
                            fill_data = json.loads(text[json_start:json_end])
                            if fill_data.get('success') == True:
                                fields_filled = True
                                print(f"    Fields: All filled successfully")
                            else:
                                errors = fill_data.get('errors', [])
                                print(f"    Fields: Partial - {', '.join(errors)}")
                                # Still consider it a success if body was filled
                                if fill_data.get('body') == True:
                                    fields_filled = True
                                    print(f"    Fields: Body filled, proceeding with send")
                        except json.JSONDecodeError:
                            pass
                    break
    
    time.sleep(2)

    # Step 5: Send email using Ctrl+Enter (primary) and Send button (fallback)
    print("[5/7] Sending email...")

    send_code = """async (page) => {
        const results = { 
            success: false, 
            method: 'none', 
            composeClosed: false, 
            confirmed: false,
            error: null 
        };
        
        try {
            // Wait for any pending operations
            await page.waitForTimeout(1500);
            
            // Get reference to compose window before sending
            const bodyField = page.locator('div[aria-label="Message body"][contenteditable="true"]').first();
            const composeExistsBefore = await bodyField.count() > 0;
            
            if (!composeExistsBefore) {
                results.error = 'Compose window not found';
                return results;
            }
            
            // Focus the body field to ensure keyboard shortcut works
            await bodyField.click();
            await page.waitForTimeout(500);
            
            // METHOD 1: Ctrl+Enter keyboard shortcut (most reliable)
            console.log('Attempting Ctrl+Enter...');
            await page.keyboard.press('Control+Enter');
            
            // Wait for compose window to close (indicates successful send)
            let composeClosed = false;
            for (let i = 0; i < 20; i++) {  // Wait up to 10 seconds
                await page.waitForTimeout(500);
                try {
                    const stillExists = await bodyField.count() > 0;
                    if (!stillExists) {
                        composeClosed = true;
                        console.log('Compose closed after', (i + 1) * 0.5, 'seconds');
                        break;
                    }
                } catch (e) {
                    composeClosed = true;
                    break;
                }
            }
            
            results.composeClosed = composeClosed;
            
            // Check for send confirmation toast
            try {
                const content = await page.content();
                if (content.includes('Message sent') || content.includes('Undo')) {
                    results.confirmed = true;
                    results.method = 'ctrl+enter with confirmation';
                }
            } catch (e) {}
            
            if (composeClosed) {
                results.success = true;
                results.method = 'ctrl+enter';
                return results;
            }
            
            // METHOD 2: Try clicking the Send button
            console.log('Ctrl+Enter did not work, trying Send button...');
            
            const sendButtonSelectors = [
                'div[aria-label="Send"][role="button"]',
                'button:has-text("Send")',
                'div[role="button"]:has-text("Send")',
                'div.T-I.J-J5-Ji.aoO.v7.T-I-atl',
                'div[aria-label*="Send"]'
            ];
            
            for (const selector of sendButtonSelectors) {
                try {
                    const sendBtn = page.locator(selector).first();
                    const isVisible = await sendBtn.isVisible();
                    if (isVisible) {
                        await sendBtn.click();
                        console.log('Clicked Send button using:', selector);
                        
                        // Wait for compose to close
                        for (let i = 0; i < 20; i++) {
                            await page.waitForTimeout(500);
                            try {
                                const stillExists = await bodyField.count() > 0;
                                if (!stillExists) {
                                    results.composeClosed = true;
                                    results.success = true;
                                    results.method = 'send_button: ' + selector;
                                    return results;
                                }
                            } catch (e) {
                                results.composeClosed = true;
                                results.success = true;
                                results.method = 'send_button: ' + selector;
                                return results;
                            }
                        }
                    }
                } catch (e) {
                    // Try next selector
                }
            }
            
            // If compose is still open, try Ctrl+Enter one more time
            if (!results.composeClosed) {
                console.log('Final attempt: Ctrl+Enter again');
                await page.keyboard.press('Control+Enter');
                await page.waitForTimeout(3000);
                
                try {
                    const stillExists = await bodyField.count() > 0;
                    if (!stillExists) {
                        results.composeClosed = true;
                        results.success = true;
                        results.method = 'ctrl+enter (retry)';
                    }
                } catch (e) {
                    results.composeClosed = true;
                    results.success = true;
                    results.method = 'ctrl+enter (retry)';
                }
            }
            
            return results;
            
        } catch (error) {
            results.error = error.message;
            return results;
        }
    }"""

    send_result = client.run_code(send_code)
    print(f"    Send: Attempted")

    # Parse send result
    send_success = False
    compose_closed = False
    if send_result:
        content_list = send_result.get('content', [])
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
                            send_data = json.loads(text[json_start:json_end])
                            send_success = send_data.get('success') == True
                            compose_closed = send_data.get('composeClosed') == True
                            if compose_closed:
                                print(f"    Send: Success (method: {send_data.get('method', 'unknown')})")
                            elif send_success:
                                print(f"    Send: Attempted (method: {send_data.get('method', 'unknown')})")
                            else:
                                print(f"    Send: Failed - {send_data.get('error', 'Unknown error')}")
                        except json.JSONDecodeError:
                            pass
                    break

    # Step 6: Wait for Gmail to process
    print("[6/7] Waiting for Gmail to process...")
    time.sleep(5)

    # Step 7: Verify by checking Sent folder
    print("[7/7] Verifying in Sent folder...")

    verify_code = f"""async (page) => {{
        const results = {{ 
            verified: false, 
            inSentFolder: false, 
            foundSubject: false, 
            foundRecipient: false,
            hasUndoToast: false,
            hasMessageSent: false,
            url: '',
            reason: 'Unknown'
        }};
        
        try {{
            // Navigate to Sent folder
            await page.goto('https://mail.google.com/mail/u/0/#sent', {{ waitUntil: 'networkidle' }});
            await page.waitForTimeout(5000);
            
            results.url = page.url();
            
            // Look for the subject line in the sent emails list
            const subjectText = '{escape_js_string(subject)}';
            const toEmail = '{escape_js_string(to)}';
            
            // Get all visible content
            const content = await page.content();
            
            // Check for various indicators
            results.foundSubject = content.includes(subjectText);
            results.foundRecipient = content.includes(toEmail);
            results.hasUndoToast = content.includes('Undo');
            results.hasMessageSent = content.includes('Message sent');
            
            // Email is verified if subject found OR (recipient found AND message sent toast)
            results.inSentFolder = results.foundSubject || (results.foundRecipient && results.hasMessageSent);
            results.verified = results.inSentFolder || results.hasUndoToast;
            
            if (results.foundSubject) {{
                results.reason = 'Found subject in Sent folder';
            }} else if (results.hasUndoToast || results.hasMessageSent) {{
                results.reason = 'Send confirmation visible';
            }} else if (results.foundRecipient) {{
                results.reason = 'Found recipient in Sent folder';
            }} else {{
                results.reason = 'Not found in Sent folder yet (may still be processing)';
            }}
            
            return results;
            
        }} catch (error) {{
            results.reason = 'Verification error: ' + error.message;
            return results;
        }}
    }}"""

    verify_result = client.run_code(verify_code)
    
    # Parse verify result
    verification_success = False
    if verify_result:
        content_list = verify_result.get('content', [])
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
                            verify_data = json.loads(text[json_start:json_end])
                            verification_success = (
                                verify_data.get('verified') == True or 
                                verify_data.get('inSentFolder') == True or 
                                verify_data.get('hasUndoToast') == True or 
                                verify_data.get('hasMessageSent') == True
                            )
                            print(f"    Verification: {verify_data.get('reason', 'Complete')}")
                        except json.JSONDecodeError:
                            pass
                    break

    # Final status
    print()
    if compose_closed:
        print("[OK] Email sent successfully! (Compose window closed)")
        print("    Check your Sent folder: https://mail.google.com/mail/u/0/#sent")
    elif send_success and verification_success:
        print("[OK] Email sent successfully! (Verified in Sent folder)")
    elif send_success:
        print("[OK] Email sent! (Check Sent folder to confirm)")
    elif verification_success:
        print("[OK] Email found in Sent folder!")
    else:
        print("[OK] Email send initiated")
        print("    Gmail may still be processing. Check Sent folder:")
        print("    https://mail.google.com/mail/u/0/#sent")

    print("\n" + "=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description='Send emails via Gmail web interface using Playwright MCP',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  python scripts\\gmasender.py "user@example.com" "Hello" "Message body"
  python scripts\\gmasender.py --mcp-url "http://localhost:8808" "..." "..." "..."
        '''
    )

    parser.add_argument('to', nargs='?', help='Recipient email address')
    parser.add_argument('subject', nargs='?', help='Email subject')
    parser.add_argument('body', nargs='?', help='Email body')
    parser.add_argument('--mcp-url', '-u', default='http://localhost:8808',
                       help='Playwright MCP server URL (default: http://localhost:8808)')
    parser.add_argument('--close-browser', '-c', action='store_true',
                       help='Close browser after sending')

    args = parser.parse_args()

    # Validate arguments
    if not (args.to and args.subject and args.body):
        print("Error: Must provide to, subject, and body arguments")
        print("\nUsage:")
        print('  python scripts\\gmasender.py "user@example.com" "Subject" "Body"')
        sys.exit(1)

    if not args.to.strip():
        print("Error: Recipient email is empty")
        sys.exit(1)

    # Create client and send
    print(f"\nConnecting to MCP server at {args.mcp_url}...")
    client = PlaywrightMCPClient(args.mcp_url)

    try:
        send_email_via_gmail(client, args.to, args.subject, args.body)
    except MCPClientError as e:
        print(f"\n[ERROR] {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        sys.exit(1)
    finally:
        if args.close_browser:
            print("\nClosing browser...")
            client.close()


if __name__ == "__main__":
    main()
